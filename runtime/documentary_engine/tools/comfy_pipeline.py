"""BorrowedTime ComfyUI two-pass adapter with resumable image jobs and verified NVENC assembly.

This adapter preserves the supplied CLI and uses the established engine modules for
speech, motion, HUDs, supplied-score crossfades, ducking, captions and final encoding.
The supplied package is retained separately by the producer; no engine module is changed.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager

ENGINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_ROOT))
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")
REVISION = "bt-comfy-adapter-v1"
MOTION_ALIASES = {"static": "none", "slow_drift_forward": "slow_zoom_in",
                  "slow_push_in": "slow_zoom_in", "slow_tilt_up": "slow_pan_up"}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def identity(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Refusing a symlink receipt")
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def local_file(root, reference):
    if not isinstance(reference, str) or not reference or "\\" in reference or PureWindowsPath(reference).drive:
        raise ValueError("Expected a nonempty project-relative POSIX file path")
    path = Path(reference)
    if path.is_absolute() or any(part in ("..", ".") for part in path.parts):
        raise ValueError("Source path is outside the project")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError(f"Missing or out-of-project source: {reference}")
    return resolved


def cache_valid(path, receipt, key):
    if not path.is_file() or not receipt.is_file():
        return False
    record = load(receipt)
    return record.get("cache_key") == key and record.get("sha256") == digest(path)


@contextmanager
def project_lock(cache):
    """Advisory OS lock is automatically released if a process dies."""
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / "runner.lock"
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0"); stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def inject_workflow(template, prompt, seed, checkpoint, token):
    graph = copy.deepcopy(template)
    prompt_nodes, seed_nodes, saves = [], [], []
    for node_id, node in graph.items():
        title = node.get("_meta", {}).get("title", "").upper()
        inputs = node.get("inputs", {})
        if "SCENE PROMPT" in title:
            inputs["value" if "value" in inputs else "text"] = prompt
            prompt_nodes.append(node_id)
        if "SEED" in title and node["class_type"] in {"PrimitiveInt", "PrimitiveInteger"}:
            inputs["value"] = seed
            seed_nodes.append(node_id)
        if node["class_type"] == "CheckpointLoaderSimple" and checkpoint:
            inputs["ckpt_name"] = checkpoint
        if node["class_type"] == "SaveImage":
            inputs["filename_prefix"] = "BorrowedTime/" + token
            saves.append(node_id)
    if not prompt_nodes:
        candidates = [key for key, node in graph.items() if node["class_type"] == "CLIPTextEncode"
                      and "positive" in node.get("_meta", {}).get("title", "").lower()]
        if len(candidates) != 1:
            raise ValueError("Workflow needs an explicit SCENE PROMPT or one Positive CLIPTextEncode node")
        graph[candidates[0]]["inputs"]["text"] = prompt
    if not seed_nodes:
        samplers = [node for node in graph.values() if node["class_type"] == "KSampler"]
        if not samplers:
            raise ValueError("Workflow has no sampler seed injection")
        for node in samplers:
            node["inputs"]["seed"] = seed
    if len(saves) != 1:
        raise ValueError("Select a workflow with exactly one final SaveImage output")
    return graph, saves[0]


class ComfyClient:
    def __init__(self, base_url, timeout=20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, route, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(self.base_url + route, data=data,
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"ComfyUI HTTP {error.code}: {detail[:3000]}") from error

    def preflight(self, template, checkpoint):
        stats = self.request("/system_stats")
        objects = self.request("/object_info")
        missing = sorted({node["class_type"] for node in template.values()} - set(objects))
        if missing:
            raise ValueError("ComfyUI nodes unavailable: " + ", ".join(missing))
        names = objects["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        chosen = checkpoint or next(node["inputs"]["ckpt_name"] for node in template.values()
                                    if node["class_type"] == "CheckpointLoaderSimple")
        if chosen not in names:
            raise ValueError(f"Checkpoint {chosen!r} unavailable; configured choices: {names}")
        return {"system_stats": stats, "checkpoint": chosen, "node_types": sorted({n["class_type"] for n in template.values()})}

    @staticmethod
    def matches_token(item, token):
        # Queue/history prompt tuples contain the submitted graph at index 2.
        if not isinstance(item, (list, tuple)) or len(item) < 3 or not isinstance(item[2], dict):
            return False
        return any(node.get("class_type") == "SaveImage" and
                   node.get("inputs", {}).get("filename_prefix") == "BorrowedTime/" + token
                   for node in item[2].values())

    def reconcile(self, token):
        queue = self.request("/queue")
        matches = {item[1] for key in ("queue_running", "queue_pending")
                   for item in queue.get(key, []) if self.matches_token(item, token)}
        history = self.request("/history?max_items=200")
        matches.update(prompt_id for prompt_id, record in history.items()
                       if self.matches_token(record.get("prompt"), token))
        if len(matches) > 1:
            raise RuntimeError("Multiple ComfyUI jobs match this owned token; manual reconciliation required")
        return next(iter(matches), None)

    @staticmethod
    def final_image(record, output_node):
        status = record.get("status", {})
        if status.get("status_str") == "error" or any(message[0] == "execution_error"
                for message in status.get("messages", []) if isinstance(message, list) and message):
            raise RuntimeError("ComfyUI generation failed: " + json.dumps(status, ensure_ascii=False)[-3000:])
        if not status.get("completed") or status.get("status_str") != "success":
            return None
        images = record.get("outputs", {}).get(output_node, {}).get("images", [])
        if len(images) != 1 or images[0].get("type", "output") != "output":
            raise RuntimeError("Successful ComfyUI job did not yield exactly one final saved output image")
        return images[0]

    def image(self, template, prompt, output, cache_key, seed, checkpoint, *, timeout=1800, retry_failed=False):
        journal = output.with_suffix(".job.json")
        state = load(journal) if journal.exists() else None
        if state and state.get("cache_key") != cache_key:
            raise ValueError("ComfyUI journal identity does not match the requested image")
        if state and state.get("state") == "failed":
            if not retry_failed or state.get("attempt", 1) >= 3:
                raise RuntimeError("Owned ComfyUI job failed; inspect journal before an explicit bounded retry")
            previous = state
            state = {"cache_key": cache_key, "attempt": previous["attempt"] + 1,
                     "previous_prompt_id": previous.get("prompt_id"), "previous_error": previous.get("error")}
        if not state:
            state = {"cache_key": cache_key, "attempt": 1}
        token = "bt_" + cache_key[:24] + "_a" + str(state["attempt"])
        graph, output_node = inject_workflow(template, prompt, seed, checkpoint, token)
        if not state.get("prompt_id"):
            if state.get("state") in {"submitting", "unknown"}:
                recovered = self.reconcile(token)
                if not recovered:
                    raise RuntimeError("Prior POST outcome is unknown; no unique job found. Refusing duplicate submission.")
                state["prompt_id"] = recovered
            else:
                state.update({"token": token, "workflow_sha256": identity(graph), "state": "submitting",
                              "submitted_epoch": time.time(), "output_node": output_node})
                atomic_json(journal, state)  # Durable intent before the network write.
                try:
                    response = self.request("/prompt", {"prompt": graph, "client_id": token,
                                                        "extra_data": {"borrowedtime_token": token}})
                    prompt_id = response.get("prompt_id")
                    if not prompt_id:
                        raise RuntimeError("ComfyUI did not return prompt_id: " + json.dumps(response))
                    state["prompt_id"] = prompt_id
                except Exception as error:
                    state.update({"state": "unknown", "error": str(error)})
                    atomic_json(journal, state)
                    recovered = self.reconcile(token)
                    if not recovered:
                        raise RuntimeError("ComfyUI submission outcome unknown; retained journal for reconciliation") from error
                    state["prompt_id"] = recovered
            state["state"] = "queued"
            atomic_json(journal, state)
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            history = self.request("/history/" + urllib.parse.quote(state["prompt_id"], safe=""))
            record = history.get(state["prompt_id"])
            if record:
                try:
                    image = self.final_image(record, output_node)
                except RuntimeError as error:
                    state.update({"state": "failed", "error": str(error), "history_status": record.get("status")})
                    atomic_json(journal, state)
                    raise
                if image:
                    parameters = urllib.parse.urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""), "type": "output"})
                    temporary = output.with_suffix(".partial.png")
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with urllib.request.urlopen(self.base_url + "/view?" + parameters, timeout=self.timeout) as response, temporary.open("wb") as stream:
                        shutil.copyfileobj(response, stream)
                    from PIL import Image
                    with Image.open(temporary) as sample:
                        if sample.size != (1920, 1080):
                            raise ValueError(f"ComfyUI final image must be 1920x1080, got {sample.size}")
                        sample.verify()
                    temporary.replace(output)
                    state.update({"state": "complete", "sha256": digest(output), "image": image,
                                  "completed_epoch": time.time(), "elapsed_this_poll_seconds": time.monotonic() - start})
                    atomic_json(journal, state)
                    atomic_json(output.with_suffix(".json"), {"cache_key": cache_key, "sha256": digest(output), "prompt_id": state["prompt_id"]})
                    return state
            time.sleep(1)
        state.update({"state": "queued", "poll_timeout_epoch": time.time()})
        atomic_json(journal, state)
        raise TimeoutError("ComfyUI job still pending; resume the same journal: " + state["prompt_id"])


def validate_manifest(path):
    from engine.motion_worker import MOTIONS
    original_bytes = Path(path).read_bytes()
    manifest = json.loads(original_bytes.decode("utf-8-sig"))
    manifest["_source_sha256"] = hashlib.sha256(original_bytes).hexdigest()
    meta = manifest["project_metadata"]
    if not SAFE_ID.fullmatch(meta["project_id"]):
        raise ValueError("Invalid project_id")
    if meta.get("target_resolution", "1920x1080") != "1920x1080" or meta.get("fps", 30) != 30:
        raise ValueError("This adapter requires 1920x1080 at 30 fps")
    seen = set()
    for chapter in manifest["chapters"]:
        if not chapter["scenes"]:
            raise ValueError("Empty chapter")
        for scene in chapter["scenes"]:
            sid = scene["scene_id"]
            if not SAFE_ID.fullmatch(sid) or sid in seen:
                raise ValueError("Invalid or duplicate scene_id")
            seen.add(sid)
            visual = scene["visual"]
            if visual.get("type") not in {"ai_cinematic", "archival_photo", "static_asset", "title_card", "black_screen_card", "archival_anchor", "illustration_anchor"}:
                raise ValueError("Unsupported visual type: " + str(visual.get("type")))
            motion = MOTION_ALIASES.get(visual.get("motion", "none"), visual.get("motion", "none"))
            if motion not in MOTIONS:
                raise ValueError("Unsupported motion: " + motion)
            for field, default, low, high in (("pause_after_seconds", .3, 0, 120), ("voice_speed", 1, .5, 2), ("duration", .1, .01, 120)):
                value = float(scene.get(field, default))
                if not math.isfinite(value) or not low <= value <= high:
                    raise ValueError("Invalid " + field + " for " + sid)
            hud = scene.get("timestamp_overlay")
            if hud and (len(hud) > 85 or any(ord(c) < 32 for c in hud)):
                raise ValueError("Invalid HUD text")
    return manifest


def assert_frozen_inputs(manifest_path, args):
    if digest(manifest_path) != args._manifest_sha:
        raise ValueError("Manifest changed after this run loaded it; refusing a mismatched delivery receipt")
    source_path = manifest_path.parent / "assets/source-map.json"
    current_source_sha = digest(source_path) if source_path.exists() else None
    if current_source_sha != args._source_map_sha:
        raise ValueError("Source map changed after this run loaded it; reconcile selected inputs before resuming")


def resolve_pin(project, scene, sources):
    pin = sources.get(scene["scene_id"])
    if not pin:
        raise ValueError("Missing source-map provenance for " + scene["scene_id"])
    for field in ("path", "sha256", "provider", "creator", "title", "license", "source_url", "display_label"):
        if not isinstance(pin.get(field), str) or not pin[field].strip():
            raise ValueError("Source pin needs " + field)
    source = local_file(project, pin["path"])
    if digest(source) != pin["sha256"]:
        raise ValueError("Source pin checksum mismatch: " + scene["scene_id"])
    if pin["license"].startswith("CC BY-SA") and not pin.get("license_url"):
        raise ValueError("CC BY-SA source must retain a license URL")
    if len(pin["display_label"]) > 110:
        raise ValueError("Source display label is too long")
    return source, pin


def fit_reference(source, destination):
    from PIL import Image, ImageOps
    with Image.open(source) as original:
        fitted = ImageOps.contain(ImageOps.exif_transpose(original).convert("RGB"), (1700, 880), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1920, 1080), (15, 17, 20))
    canvas.paste(fitted, ((1920 - fitted.width) // 2, (1080 - fitted.height) // 2))
    canvas.save(destination)


def narrator_fingerprint(voice):
    """Bind speech caches to installed model, voice, frontend and actual source bytes."""
    from engine import tts_worker
    from huggingface_hub import hf_hub_download
    if not re.fullmatch(r"[abefhijpz][fm]_[a-z0-9_]+", voice):
        raise ValueError("Use a supported named Kokoro voice; a blend requires a separate approved adapter")
    pipe = tts_worker._pipeline(voice[0], os.getenv("KOKORO_DEVICE") or None)
    pipe.load_voice(voice)
    files = {}
    for name in ("config.json", "kokoro-v1_0.pth", f"voices/{voice}.pt"):
        path = Path(hf_hub_download(repo_id="hexgrad/Kokoro-82M", filename=name, local_files_only=True))
        files[name] = digest(path)
    return {"files_sha256": files, "kokoro": importlib.metadata.version("kokoro"),
            "misaki": importlib.metadata.version("misaki"), "frontend": voice[0]}


def prepare(manifest, manifest_path, template, args, sources):
    import numpy as np
    import soundfile as sf
    from engine import tts_worker
    from engine.hud_overlay import install_font
    project = manifest_path.parent
    cache = project / "cache"
    for part in ("audio", "visuals", "clips", "captions", "work"):
        (cache / part).mkdir(parents=True, exist_ok=True)
    install_font(cache / "clips")
    client = ComfyClient(args.comfy_url)
    comfy = client.preflight(template, args.checkpoint)
    selected = [scene for chapter in manifest["chapters"] for scene in chapter["scenes"]
                if not args.scene or scene["scene_id"] == args.scene]
    if not selected:
        raise ValueError("Requested scene_id was not found")
    records = []
    tts_version = importlib.metadata.version("kokoro")
    fingerprints = {}
    for index, scene in enumerate(selected, 1):
        sid = scene["scene_id"]
        print(f"PREPARE {index}/{len(selected)} {sid}", flush=True)
        text = scene.get("narration", "").strip()
        voice = scene.get("voice", manifest["project_metadata"].get("default_voice", "bm_george"))
        speed = float(scene.get("voice_speed", 1))
        if text and voice not in fingerprints:
            fingerprints[voice] = narrator_fingerprint(voice)
        fingerprint = fingerprints.get(voice)
        key = identity(REVISION, "narration", text, voice, voice[:1], speed,
                       scene.get("pause_after_seconds", .3), tts_version, fingerprint)
        audio_path = cache / "audio" / (key + ".wav")
        audio_receipt = audio_path.with_suffix(".json")
        if text:
            if not cache_valid(audio_path, audio_receipt, key):
                if args.assemble_only:
                    raise ValueError("Narration cache missing or changed: " + sid)
                tts_worker.narrate(text, voice, speed, audio_path)
                raw, rate = sf.read(audio_path, dtype="float32")
                if rate != 24000 or not len(raw) or not np.isfinite(raw).all() or not np.any(np.abs(raw) > .003):
                    raise ValueError("Narration was missing, silent or invalid: " + sid)
                atomic_json(audio_receipt, {"cache_key": key, "sha256": digest(audio_path), "voice": voice, "speed": speed, "kokoro_version": tts_version, "source_fingerprint": fingerprint})
        visual = scene["visual"]
        kind = visual["type"]
        seed = int(identity(manifest["project_metadata"]["project_id"], sid)[:12], 16)
        if kind == "ai_cinematic":
            image_key = identity(REVISION, template, comfy["checkpoint"], args.checkpoint_sha256, visual["prompt"], seed)
            image_path = cache / "visuals" / (image_key + ".png")
            if not cache_valid(image_path, image_path.with_suffix(".json"), image_key):
                if args.assemble_only:
                    raise ValueError("ComfyUI image cache missing or changed: " + sid)
                job = client.image(template, visual["prompt"], image_path, image_key, seed,
                                   comfy["checkpoint"], timeout=args.timeout, retry_failed=args.retry_failed)
            else:
                job = load(image_path.with_suffix(".job.json"))
            provenance = {"provider": "comfyui_ai_image", "kind": "image", "backend": "ComfyUI two-pass SDXL",
                          "title": comfy["checkpoint"], "checkpoint_sha256": args.checkpoint_sha256,
                          "workflow_sha256": identity(template), "seed": seed,
                          "prompt_id": job["prompt_id"], "display_label": "AI-GENERATED RECONSTRUCTION - NOT ORIGINAL FOOTAGE"}
        elif kind in {"archival_photo", "static_asset", "archival_anchor", "illustration_anchor"}:
            source, pin = resolve_pin(project, scene, sources)
            image_key = identity(REVISION, "complete_reference_fit", pin["sha256"], sid)
            image_path = cache / "visuals" / (image_key + ".png")
            if not cache_valid(image_path, image_path.with_suffix(".json"), image_key):
                fit_reference(source, image_path)
                atomic_json(image_path.with_suffix(".json"), {"cache_key": image_key, "sha256": digest(image_path)})
            provenance = {**pin, "kind": "image", "original_sha256": pin["sha256"],
                          "modifications": "Complete source fitted in dark frame; EXIF orientation respected; repeated reference views are intentional editorial reuse"}
        else:
            import pipeline
            card_text = visual.get("card_text") or "\n\n".join(str(visual.get(field, "")) for field in ("title", "subtitle") if visual.get(field))
            if not card_text.strip():
                raise ValueError("Title card needs text: " + sid)
            image_key = identity(REVISION, "card", sid, card_text, digest(cache / "clips/hud-font.ttf"))
            image_path = cache / "visuals" / (image_key + ".png")
            if not cache_valid(image_path, image_path.with_suffix(".json"), image_key):
                pipeline.card(image_path, card_text, cache / "clips/hud-font.ttf")
                atomic_json(image_path.with_suffix(".json"), {"cache_key": image_key, "sha256": digest(image_path)})
            provenance = {"provider": "title_card", "kind": "image", "title": card_text}
        records.append({"scene_id": sid, "audio": str(audio_path.relative_to(project)) if text else None,
                        "audio_sha256": digest(audio_path) if text else None,
                        "image": str(image_path.relative_to(project)), "image_sha256": digest(image_path),
                        "provenance": provenance, "seed": seed})
        assert_frozen_inputs(manifest_path, args)
        atomic_json(cache / "prepare-progress.json", {"manifest_sha256": args._manifest_sha,
                    "workflow_sha256": identity(template), "checkpoint_sha256": args.checkpoint_sha256,
                    "completed_scenes": len(records), "selected_scenes": len(selected), "records": records})
    return records, comfy


def run_pipeline(args):
    manifest_path = Path(args.manifest).resolve()
    project = manifest_path.parent
    manifest = validate_manifest(manifest_path)
    args._manifest_sha = manifest["_source_sha256"]
    args.checkpoint_sha256 = args.checkpoint_sha256 or manifest["project_metadata"].get("checkpoint_sha256")
    if not isinstance(args.checkpoint_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", args.checkpoint_sha256):
        raise ValueError("Pin the actual checkpoint SHA-256 using --checkpoint-sha256 or project_metadata.checkpoint_sha256")
    template = load(args.workflow)
    if not isinstance(template, dict) or not all(isinstance(n, dict) and "class_type" in n for n in template.values()):
        raise ValueError("Expected API-format workflow JSON")
    cache = project / "cache"
    with project_lock(cache):
        source_path = project / "assets/source-map.json"
        source_bytes = source_path.read_bytes() if source_path.exists() else None
        args._source_map_sha = hashlib.sha256(source_bytes).hexdigest() if source_bytes is not None else None
        sources = json.loads(source_bytes.decode("utf-8-sig")) if source_bytes is not None else {}
        assert_frozen_inputs(manifest_path, args)
        if args.preflight:
            from engine.normalizer import preflight
            work = cache / "preflight"; work.mkdir(parents=True, exist_ok=True)
            report = {"manifest_sha256": args._manifest_sha, "source_map_sha256": args._source_map_sha, "workflow_sha256": identity(template),
                      "comfyui": ComfyClient(args.comfy_url).preflight(template, args.checkpoint),
                      "hardware": preflight(work, software=False)}
            for chapter in manifest["chapters"]:
                for scene in chapter["scenes"]:
                    if scene["visual"]["type"] in {"archival_photo", "static_asset", "archival_anchor", "illustration_anchor"}:
                        resolve_pin(project, scene, sources)
            for field in ("global_music_file", "coda_music_file"):
                if manifest["project_metadata"].get(field):
                    local_file(project, manifest["project_metadata"][field])
            atomic_json(cache / "preflight.json", report)
            print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
            return
        started = time.time()
        records, comfy = prepare(manifest, manifest_path, template, args, sources)
        assert_frozen_inputs(manifest_path, args)
        preparation = {"manifest_sha256": args._manifest_sha, "source_map_sha256": args._source_map_sha, "workflow_sha256": identity(template),
                       "records": records, "comfyui": comfy, "seconds": time.time() - started}
        atomic_json(cache / ("prepared-" + args.scene + ".json" if args.scene else "prepared.json"), preparation)
        if args.prepare_only:
            print("PREPARATION COMPLETE", len(records), flush=True)
            return
        assemble(manifest, manifest_path, records, preparation, args)


def assemble(manifest, manifest_path, records, preparation, args):
    import numpy as np
    import soundfile as sf
    from engine import audio_mixer as audio, composer, hud_overlay, metadata_exporter
    from engine import motion_worker, score_worker, subtitle_worker
    from engine.normalizer import preflight, probe, SR, FPS
    project = manifest_path.parent
    cache, output = project / "cache", project / "output"
    output.mkdir(parents=True, exist_ok=True)
    stem = manifest["project_metadata"]["project_id"] + ("_PROOF_" + args.scene if args.scene else "_DOCUMENTARY_MASTER")
    movie = output / (stem + ".mp4")
    receipt_path = movie.with_suffix(".verification.json")
    assert_frozen_inputs(manifest_path, args)
    run_identity = identity(REVISION, args._manifest_sha, args._source_map_sha, preparation["workflow_sha256"],
                            preparation["comfyui"]["checkpoint"], args.checkpoint_sha256, args.scene, records)
    if receipt_path.exists() and movie.exists():
        old = load(receipt_path)
        if old.get("run_identity") == run_identity and old.get("sha256") == digest(movie):
            print("EXISTING VERIFIED MASTER", movie, flush=True)
            return
        raise ValueError("A different prior master exists; preserve/version it before rendering the new input")
    if movie.exists():
        raise ValueError("Master exists without its verification receipt; reconcile it before retry")
    start = time.time()
    work = cache / "work" / run_identity[:24]
    work.mkdir(parents=True, exist_ok=True)
    hardware = preflight(cache / "clips", software=False)
    by_id = {row["scene_id"]: row for row in records}
    meta = copy.deepcopy(manifest["project_metadata"])
    scenes = [scene for chapter in manifest["chapters"] for scene in chapter["scenes"] if scene["scene_id"] in by_id]
    voices, effects, clips, credits, cues, proof_cues, score_timeline, chapters, chapter_audio = [], [], [], [], [], [], [], [], []
    wall_frame = 0
    for chapter in manifest["chapters"]:
        chapter_scenes = [s for s in chapter["scenes"] if s["scene_id"] in by_id]
        if not chapter_scenes:
            continue
        chapter_start = wall_frame
        chapters.append((wall_frame, chapter["chapter_title"]))
        for scene in chapter_scenes:
            sid = scene["scene_id"]
            row = by_id[sid]
            print(f"ASSEMBLE {len(credits)+1}/{len(scenes)} {sid}", flush=True)
            text = scene.get("narration", "").strip()
            voiced = np.empty((0, 2), dtype="float32")
            if text:
                wav = local_file(project, row["audio"])
                if digest(wav) != row["audio_sha256"]:
                    raise ValueError("Narration changed after preparation")
                voiced = audio.read(wav, work)
                if not np.isfinite(voiced).all() or not np.any(np.abs(voiced) > .003):
                    raise ValueError("No actual speech energy: " + sid)
                caption_key = identity(row["audio_sha256"], os.getenv("WHISPER_MODEL", "tiny.en"),
                                       importlib.metadata.version("faster-whisper"))
                timed_path = cache / "captions" / (caption_key + ".json")
                if timed_path.exists():
                    words = load(timed_path)
                else:
                    words = subtitle_worker.transcribe(wav)
                    atomic_json(timed_path, words)
                if not words:
                    raise RuntimeError("Whisper returned no timed speech: " + sid)
                measured = [{"start": round(wall_frame / FPS + float(a), 3),
                             "end": round(wall_frame / FPS + min(float(b), len(voiced) / SR), 3), "word": word}
                            for a, b, word in words if 0 <= a < min(b, len(voiced) / SR)]
                if not measured:
                    raise RuntimeError("Whisper returned no valid word spans: " + sid)
                cues.append(measured)
                proof_cues.extend(script_cues(text, measured))
            narrated_seconds = len(voiced) / SR
            pause = float(scene.get("pause_after_seconds", .3))
            # Explicit duration is a minimum total scene duration. A voiced card is
            # never truncated to fit a shorter requested still duration.
            seconds = max(narrated_seconds + pause, float(scene.get("duration", 0)))
            frames = max(1, math.ceil(seconds * FPS))
            samples = frames * (SR // FPS)
            voice = np.zeros((samples, 2), dtype="float32")
            if len(voiced):
                voice[:len(voiced)] = voiced * min(2.5, .65 / float(np.abs(voiced).max()))
            voices.append(voice)
            visual = scene["visual"]
            entry = {"scene_id": sid, "start_sample": wall_frame * (SR // FPS),
                     "end_sample": (wall_frame + frames) * (SR // FPS),
                     "voice_end_sample": wall_frame * (SR // FPS) + len(voiced),
                     "narrated": bool(text), "title_card": visual["type"] in {"title_card", "black_screen_card"}}
            if scene.get("music_transition") and not args.scene:
                entry["music_transition"] = scene["music_transition"]
            score_timeline.append(entry)
            fx = np.zeros_like(voice)
            if scene.get("sfx"):
                name = scene["sfx"]
                if not re.fullmatch(r"[A-Za-z0-9_-]+\.wav", name):
                    raise ValueError("Unsafe SFX name")
                custom = project / "assets/sfx" / name
                effect = audio.read(local_file(project, "assets/sfx/" + name), work) if custom.is_file() else audio.sfx_wave(name)
                offset = round(float(scene.get("sfx_offset_seconds", 0)) * SR)
                if not 0 <= offset < samples:
                    raise ValueError("SFX offset falls outside scene")
                length = min(len(effect), samples - offset)
                fx[offset:offset+length] = effect[:length] * .53
            effects.append(fx)
            label = scene.get("timestamp_overlay")
            source_label = row["provenance"].get("display_label")
            motion = MOTION_ALIASES.get(visual.get("motion", "none"), visual.get("motion", "none"))
            clip_key = identity(REVISION, row["image_sha256"], frames, motion, label, source_label,
                                digest(cache / "clips/hud-font.ttf"))
            clip = cache / "clips" / (clip_key + ".mp4")
            clip_receipt = clip.with_suffix(".json")
            if not cache_valid(clip, clip_receipt, clip_key):
                filters = []
                if label:
                    filters.append(hud_overlay.hud_filter(label, clip.parent, clip_key))
                if source_label:
                    filters.append(hud_overlay.source_filter(source_label, clip.parent, clip_key))
                image_path = local_file(project, row["image"])
                if digest(image_path) != row["image_sha256"]:
                    raise ValueError("Prepared visual changed")
                motion_worker.render_scene(image_path, "image", motion, frames, ",".join(filters) or None, clip)
                stream = probe(clip)["streams"][0]
                if int(stream.get("nb_frames", 0)) != frames or stream["avg_frame_rate"] != "30/1":
                    raise ValueError("Intermediate frame-count mismatch")
                atomic_json(clip_receipt, {"cache_key": clip_key, "sha256": digest(clip), "frames": frames})
            clips.append(clip)
            credits.append({"scene_id": sid, **row["provenance"], "sha256": row["image_sha256"],
                            "start_frame": wall_frame, "frame_count": frames, "timestamp_overlay": label,
                            "narration_sha256": row["audio_sha256"], "requested_duration": scene.get("duration"),
                            "narration_seconds": narrated_seconds})
            wall_frame += frames
        duck = float(chapter.get("ducking_db", meta.get("default_ducking_db", -16)))
        chapter_audio.append({"chapter_id": chapter["chapter_id"], "start_frame": chapter_start, "end_frame": wall_frame, "ducking_db": duck})
    total_samples = wall_frame * (SR // FPS)
    voice_track = np.concatenate(voices)
    del voices
    if not meta.get("global_music_file"):
        raise ValueError("This supplied-score production requires global_music_file; no generated score fallback")
    score, score_receipt = score_worker.build(meta, score_timeline, total_samples, project, work)
    speech_db = float(meta.get("score_speech_db", meta.get("default_ducking_db", -16)))
    pause_db, title_db = float(meta.get("score_pause_db", -8)), float(meta.get("score_title_db", 0))
    gain = audio.score_envelope(voice_track, score_timeline, speech_db=speech_db, pause_db=pause_db, title_db=title_db)
    score_receipt["ducking"] = audio.score_envelope_metrics(gain, voice_track, score_timeline, speech_db=speech_db, pause_db=pause_db, title_db=title_db)
    mix = audio.mix_audio(voice_track, score, np.concatenate(effects), speech_db, work, evidence=True, gain_envelope=gain)
    del voice_track, score, gain, effects
    assert_frozen_inputs(manifest_path, args)
    master = composer.compose(clips, mix, movie, encoder="h264_nvenc", frames=wall_frame)
    # Sidecars are generated only after successful full decode/format verification.
    import pipeline
    pipeline.subtitles(cues, movie)
    raw_srt = movie.with_suffix(".whisper.srt")
    shutil.copyfile(movie.with_suffix(".srt"), raw_srt)
    srt = "\n\n".join(f"{i+1}\n{pipeline.srt_clock(a)} --> {pipeline.srt_clock(b)}\n{text}"
                       for i, (a, b, text) in enumerate(proof_cues)) + "\n"
    movie.with_suffix(".srt").write_text(srt, encoding="utf-8")
    atomic_json(movie.with_suffix(".caption-proof.json"), {"method": "Selected script words mapped monotonically to measured Whisper phrase spans; original word JSON and raw ASR SRT retained", "cue_count": len(proof_cues), "script_word_count": sum(len(s.get("narration", "").split()) for s in scenes)})
    thumbnail = local_file(project, meta.get("thumbnail_path", "thumbnail.png"))
    from PIL import Image, ImageOps
    with Image.open(thumbnail) as original:
        original_size = original.size
        ImageOps.fit(ImageOps.exif_transpose(original).convert("RGB"), (3840, 2160), Image.Resampling.LANCZOS).save(output / (stem + "_thumbnail.png"))
    metadata_exporter.export({**meta, "total_frames": wall_frame}, chapters, credits, output / (stem + "_youtube_package.txt"))
    chapter_lines = []
    for frame, title in chapters:
        minute, second = divmod(frame // FPS, 60)
        chapter_lines.append(f"{minute:02}:{second:02} {title}")
    package = {"title": meta["video_title"], "description": meta.get("video_description", "") + "\n\nCHAPTERS\n" + "\n".join(chapter_lines), "tags": meta.get("tags", []), "recommended_visibility": "unlisted", "ai_disclosure": True, "paid_promotion": False, "upload_status": "not_uploaded"}
    if len(package["title"]) > 100 or len(package["description"]) > 5000:
        raise ValueError("Publishing metadata exceeds YouTube limits")
    atomic_json(output / (stem + "_publishing_package.json"), package)
    (output / (stem + "_publishing_package.md")).write_text("# " + package["title"] + "\n\n" + package["description"] + "\n\nTags: " + ", ".join(package["tags"]) + "\n\nPrepared settings: Unlisted; AI disclosure Yes; paid promotion No. No upload performed.\n", encoding="utf-8")
    evidence = output / (stem + "_evidence")
    evidence.mkdir(exist_ok=True)
    for name in ("voice.wav", "music-before.wav", "music-ducked.wav", "sfx.wav", "mix.wav"):
        shutil.copyfile(work / name, evidence / name)
    assert_frozen_inputs(manifest_path, args)
    receipt = {"run_identity": run_identity, "manifest_sha256": args._manifest_sha, "source_map_sha256": args._source_map_sha, "workflow_sha256": preparation["workflow_sha256"],
               "checkpoint": preparation["comfyui"]["checkpoint"], "checkpoint_sha256": args.checkpoint_sha256,
               "sha256": digest(movie), "output": movie.name, "scene_count": len(scenes), "credits": credits,
               "duration_seconds": wall_frame / FPS, "master": master, "preflight": hardware,
               "chapter_audio": chapter_audio, "supplied_score": score_receipt, "word_caption_count": sum(len(c) for c in cues),
               "preparation_seconds": preparation["seconds"], "assembly_seconds": time.time() - start,
               "thumbnail_pixels": [3840, 2160], "thumbnail_source_pixels": list(original_size),
               "source_reuse": "Repeated genuine reference images are explicitly identified; no zero-repetition claim",
               "test_mode": "single_scene_proof" if args.scene else "manifest", "renderer_revision": REVISION}
    atomic_json(receipt_path, receipt)
    print("VERIFIED MASTER", movie, "NVENC", master["fps_wall"], "fps", flush=True)


def script_cues(text, measured):
    """Keep exactly the selected script words inside the measured speech interval."""
    import difflib
    tokens = text.split()
    if not measured or not tokens:
        raise ValueError("Caption proof needs script and actual timed speech")
    def norm(word):
        return re.sub(r"[^\w]", "", word.lower())
    buckets = [[] for _ in range((len(measured)+6)//7)]
    matcher = difflib.SequenceMatcher(a=[norm(w["word"]) for w in measured], b=[norm(w) for w in tokens], autojunk=False)
    for tag, a, b, c, d in matcher.get_opcodes():
        if tag == "delete":
            continue
        for offset, token in enumerate(tokens[c:d]):
            index = a + offset if tag == "equal" else a + min(max(b-a-1, 0), int(offset*(b-a)/max(d-c, 1)))
            buckets[min(index//7, len(buckets)-1)].append(token)
    cues = []
    for i, bucket in enumerate(buckets):
        if bucket:
            words = measured[i*7:(i+1)*7]
            cues.append((words[0]["start"], words[-1]["end"], " ".join(bucket)))
    if " ".join(c[2] for c in cues).split() != tokens:
        raise ValueError("Caption proof did not retain the exact selected script")
    return cues


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", required=True)
    cli.add_argument("--workflow", required=True)
    cli.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    cli.add_argument("--checkpoint")
    cli.add_argument("--checkpoint-sha256", help="Pinned on-disk checkpoint SHA-256 supplied by the operator; retained in cache identity and receipt")
    modes = cli.add_mutually_exclusive_group()
    modes.add_argument("--prepare-only", action="store_true")
    modes.add_argument("--assemble-only", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    cli.add_argument("--scene", help="One scene ID for a private proof; output name is separate from the full film")
    cli.add_argument("--timeout", type=float, default=1800, help="Polling timeout; expiry retains the existing job ID")
    cli.add_argument("--retry-failed", action="store_true", help="Explicit retry of a terminal failed job; maximum three attempts")
    return cli


if __name__ == "__main__":
    try:
        run_pipeline(parser().parse_args())
    except Exception as error:
        print(f"Render stopped ({type(error).__name__}): {error}", file=sys.stderr, flush=True)
        raise SystemExit(1)
