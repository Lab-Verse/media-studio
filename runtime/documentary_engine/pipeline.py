import argparse
from contextlib import contextmanager
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from time import perf_counter

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("HF_HOME", str(ROOT / "models" / "huggingface"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

from engine import ai_fallback, audio_mixer as audio, composer, hud_overlay, metadata_exporter
from engine import motion_worker, music_worker, score_worker, subtitle_worker, thumbnail_worker, tts_worker
from engine.media_fetcher import MediaFetcher, pinned_archival, pinned_illustration
from engine.normalizer import FPS, HEIGHT, SR, WIDTH, ffmpeg, preflight

SAFE_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}")


def validated(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    data["_source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    meta = data["project_metadata"]
    if not SAFE_ID.fullmatch(meta["project_id"]):
        raise ValueError("Invalid project_id")
    if (meta.get("target_resolution", "1920x1080"), meta.get("fps", FPS)) != ("1920x1080", FPS):
        raise ValueError("Only 1920x1080 at 30 fps is supported")
    if not data["chapters"] or any(not c["scenes"] for c in data["chapters"]):
        raise ValueError("Manifest must have at least one scene in each chapter")
    seen = set()
    for chapter in data["chapters"]:
        for scene in chapter["scenes"]:
            identifier = scene["scene_id"]
            if not SAFE_ID.fullmatch(identifier) or identifier in seen:
                raise ValueError(f"Invalid or repeated scene_id: {identifier}")
            seen.add(identifier)
            visual = scene["visual"]
            visual_type = visual.get("type")
            if visual_type == "ai_cinematic":
                visual["preferred_source"] = "ai_image"
                visual["ai_fallback_prompt"] = visual["prompt"]
            elif visual_type == "black_screen_card":
                visual["preferred_source"] = "black_screen_card"
            elif visual_type in {"archival_anchor", "illustration_anchor"}:
                visual["preferred_source"] = visual_type
            elif visual_type is not None:
                raise ValueError(f"Unsupported visual type in {identifier}: {visual_type}")
            if visual.get("motion", "none") not in motion_worker.MOTIONS:
                raise ValueError(f"Unsupported motion in {identifier}")
            if not -36 <= float(meta.get("default_ducking_db", -14)) <= 0:
                raise ValueError("default_ducking_db must be between -36 and 0")
            pause = float(scene.get("pause_after_seconds", 0.5))
            speed = float(scene.get("voice_speed", 1.0))
            if not 0 <= pause <= 120 or not .5 <= speed <= 2:
                raise ValueError(f"Invalid pause or narration speed in {identifier}")
            sfx = scene.get("sfx")
            if sfx and not re.fullmatch(r"[a-zA-Z0-9_-]+\.wav", sfx):
                raise ValueError(f"Invalid SFX name: {sfx}")
            if "sfx_offset_seconds" in scene and not 0 <= float(scene["sfx_offset_seconds"]) <= 120:
                raise ValueError(f"Invalid SFX offset in {identifier}")
    return data


def key(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()[:24]


def hash_file(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def fixture_voice(wav, seed):
    t = np.arange(SR * 3) / SR
    active = np.minimum(1, np.minimum(t * 25, (3 - t) * 20))
    signal = .25 * np.sin(2 * np.pi * (124 * t + 1.3 * np.sin(t * 5 + seed)))
    signal += .065 * np.sin(2 * np.pi * 495 * t)
    signal *= active * (.65 + .35 * np.sin(t * 27) ** 2)
    audio.write(wav, np.column_stack((signal, signal)))


def fixture_music(wav):
    t = np.arange(SR * 6) / SR
    bed = sum(.06 * np.sin(2 * np.pi * freq * t) for freq in (55, 110, 165, 247))
    audio.write(wav, np.column_stack((bed, bed)))


def fixture_still(path, seed, *, thumbnail=False):
    w, h = (3840, 2160) if thumbnail else (1600, 900)
    rng = np.random.default_rng(seed)
    bg = Image.new("RGB", (w, h), (13, 31, 42) if seed % 2 else (50, 25, 32))
    draw = ImageDraw.Draw(bg)
    for _ in range(110):
        x, y = rng.integers(0, w), rng.integers(0, h)
        radius = int(rng.integers(2, 36))
        color = tuple(int(c) for c in rng.integers(50, 185, 3))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    draw.rectangle((0, int(.67 * h), w, int(.71 * h)), fill=(75, 116, 123))
    bg.save(path)


def card(path, text, font_path):
    bg = Image.new("RGB", (WIDTH, HEIGHT), "black")
    draw = ImageDraw.Draw(bg)
    font = ImageFont.truetype(str(font_path), 52)
    bounds = draw.multiline_textbbox((0, 0), text, font=font, spacing=22, align="center")
    if bounds[2] > WIDTH - 120 or bounds[3] > HEIGHT - 120:
        raise ValueError("Title card text exceeds the safe area")
    draw.multiline_text((WIDTH // 2, HEIGHT // 2 - (bounds[3] + bounds[1]) / 2), text,
                        anchor="ma", spacing=22, align="center", font=font, fill="#eeeeee")
    bg.save(path)


def srt_clock(seconds):
    total = round(seconds * 1000)
    m, ms = divmod(total, 1000)
    h, sec = divmod(m, 60)
    hour, minute = divmod(h, 60)
    return f"{hour:02}:{minute:02}:{sec:02},{ms:03}"


def subtitles(cues, output):
    # Keep precise words as JSON; group the readable SRT into short phrases.
    output.with_suffix(".words.json").write_text(json.dumps(cues, ensure_ascii=False, indent=2), encoding="utf-8")
    entries = []
    for words in cues:
        for i in range(0, len(words), 7):
            group = words[i:i + 7]
            entries.append(f"{len(entries) + 1}\n{srt_clock(group[0]['start'])} --> "
                           f"{srt_clock(group[-1]['end'])}\n{' '.join(w['word'] for w in group)}")
    output.with_suffix(".srt").write_text("\n\n".join(entries) + "\n", encoding="utf-8")


def visual_evidence(output, work, checkpoints):
    result = []
    for stem, start, stop, label in checkpoints:
        a, b = work / f"{stem}-start.png", work / f"{stem}-hud-frame.png"
        for index, target in ((start + 1, a), (stop - 2, b)):
            ffmpeg("-y", "-ss", f"{index / FPS:.6f}", "-i", output, "-frames:v", "1", target)
        with Image.open(a) as first, Image.open(b) as last:
            roi = np.asarray(last.crop((53, 54, 75 + 20 * (len(label) + 4), 98)).convert("RGB"))
            n = int((np.min(roi, axis=2) > 215).sum())
            aa = np.asarray(first.crop((0, 135, WIDTH, HEIGHT)).convert("L"), dtype="float32")
            bb = np.asarray(last.crop((0, 135, WIDTH, HEIGHT)).convert("L"), dtype="float32")
            motion = float(np.abs(aa - bb).mean())
        if n < 190 or motion < 1:
            raise RuntimeError(f"HUD or motion not visible for {stem}: HUD pixels={n}, motion={motion:.2f}")
        result.append({"scene": stem, "expected_text": label, "bright_hud_pixels": n,
                       "mean_luma_change": round(motion, 2), "frame": b.name})
    return result


def render(data, work, output, *, smoke, fixture, software, prefer_nvenc=False):
    started = perf_counter()
    times = {}
    cache_hits = {"narration": 0, "ai_stills": 0, "music": 0}
    image_geometry = os.getenv("DOCUMENTARY_IMAGE_SIZE")
    image_options = {}
    if image_geometry:
        if not re.fullmatch(r"[1-9][0-9]{1,3}x[1-9][0-9]{1,3}", image_geometry):
            raise ValueError("DOCUMENTARY_IMAGE_SIZE must look like 1024x576")
        width, height = map(int, image_geometry.split("x"))
        if any(v % 16 or not 256 <= v <= 2048 for v in (width, height)):
            raise ValueError("Still dimensions must be multiples of 16 from 256 through 2048")
        image_options = {"width": width, "height": height}
    scene_count = sum(len(c["scenes"]) for c in data["chapters"])
    @contextmanager
    def timed(name):
        start = perf_counter()
        if name not in times:
            print(f"Starting {name}", flush=True)
        try:
            yield
        finally:
            times[name] = times.get(name, 0) + perf_counter() - start

    meta = data["project_metadata"]
    chapters, credits, clips, cues, windows, checkpoints = [], [], [], [], [], []
    voices, music, effects = [], [], []
    score_timeline = []
    score_receipt = None
    chapter_audio = []
    preserve_audio = smoke or os.getenv("DOCUMENTARY_AUDIO_EVIDENCE") == "1"
    source_map = ROOT / "assets" / "archival" / meta["project_id"] / "scene_map.json"
    archival = json.loads(source_map.read_text(encoding="utf-8-sig")) if source_map.exists() else {}
    minimum_archival = int(os.getenv("DOCUMENTARY_REQUIRE_ARCHIVAL", "0"))
    if sum(record.get("provider") != "original_illustration" for record in archival.values()) < minimum_archival:
        raise ValueError(f"At least {minimum_archival} verified archival assets are required")
    required_archival = [scene["scene_id"] for chapter in data["chapters"]
                        for scene in chapter["scenes"]
                        if scene["visual"].get("preferred_source") in {"archival_anchor", "illustration_anchor"}]
    missing = set(required_archival) - set(archival)
    if missing:
        raise ValueError("Verified archival assets are missing for " + ", ".join(sorted(missing)))
    cache = ROOT / "cache"
    for part in ("audio", "music", "visuals", "downloads"):
        (cache / part).mkdir(parents=True, exist_ok=True)
    with timed("preflight"):
        hw = preflight(work, software=software)
    fetcher = MediaFetcher(cache / "downloads") if not fixture else None
    generated = set()
    fps_samples = SR // FPS
    wall_frame = 0
    for chapter in data["chapters"]:
        chapters.append((wall_frame, chapter["chapter_title"]))
        chapter_start = wall_frame
        for scene in chapter["scenes"]:
            sid = scene["scene_id"]
            stem = f"scene-{len(clips):04}"
            if not smoke:
                print(f"Scene {len(clips) + 1}/{scene_count}: {sid}", flush=True)
            raw, visual = scene.get("narration") or "", scene["visual"]
            speed, voice_id = float(scene.get("voice_speed", 1.0)), scene.get("voice", meta.get("default_voice", "bm_george"))
            voiced = np.empty((0, 2), dtype="float32")
            seed = int(key(meta["project_id"], sid)[:8], 16)
            if raw.strip():
                with timed("narration"):
                    wav = (work / f"{stem}-fixture.wav" if fixture else
                           cache / "audio" / (key("kokoro-v1", raw, voice_id, speed) + ".wav"))
                    if fixture:
                        fixture_voice(wav, seed)
                    elif not wav.exists():
                        tts_worker.narrate(raw, voice_id, speed, wav)
                    else:
                        cache_hits["narration"] += 1
                    voiced = audio.read(wav, work)
                if not fixture:
                    with timed("word_captions"):
                        words = subtitle_worker.transcribe(wav)
                    if smoke and not words:
                        raise RuntimeError(f"Whisper returned no timed words for {sid}")
                    cues.append([{"start": round(wall_frame / FPS + a, 3),
                                  "end": round(wall_frame / FPS + min(b, len(voiced) / SR), 3), "word": word}
                                 for a, b, word in words if a < min(b, len(voiced) / SR)])
            frames = max(1, math.ceil((len(voiced) + float(scene.get("pause_after_seconds", .5)) * SR) / fps_samples))
            if smoke:
                if not len(voiced):
                    raise RuntimeError("Smoke scene requires audio narration")
                activity = np.flatnonzero(np.max(np.abs(voiced), axis=1) >= .014)
                windows.append((wall_frame + math.ceil(activity[0] / fps_samples),
                                wall_frame + math.floor(activity[-1] / fps_samples)))
            samples = frames * fps_samples
            vx = np.zeros((samples, 2), dtype="float32")
            if len(voiced):
                vx[:len(voiced)] = voiced * (min(2.5, .65 / float(np.abs(voiced).max())) if np.any(voiced) else 1)
            voices.append(vx)
            score_timeline.append({
                "scene_id": sid, "start_sample": wall_frame * fps_samples,
                "end_sample": (wall_frame + frames) * fps_samples,
                "voice_end_sample": wall_frame * fps_samples + len(voiced),
                "narrated": bool(raw.strip()), "title_card": visual.get("preferred_source") == "black_screen_card",
                **({"music_transition": scene["music_transition"]} if scene.get("music_transition") else {}),
            })
            fx = np.zeros_like(vx)
            if scene.get("sfx"):
                name = scene["sfx"]
                custom = ROOT / "assets" / "sfx" / name
                effect = audio.read(custom, work) if custom.is_file() else audio.sfx_wave(name)
                offset = round(float(scene.get("sfx_offset_seconds", 0.0)) * SR)
                if offset >= samples:
                    raise ValueError(f"SFX offset is outside scene {sid}")
                length = min(len(effect), samples - offset)
                fx[offset:offset + length] = effect[:length] * .53
            effects.append(fx)

            preferred = visual.get("preferred_source")
            source = cache / "visuals" / f"{key(meta['project_id'], sid, visual)}.png"
            selected = None
            if (preferred == "illustration_anchor" or archival.get(sid, {}).get("provider") == "original_illustration") and not fixture:
                source, asset = pinned_illustration(ROOT, archival[sid], work / f"{stem}-illustration.png")
            elif (preferred == "archival_anchor" or sid in archival) and not fixture:
                source, asset = pinned_archival(ROOT, archival[sid], work / f"{stem}-archival.png")
            elif fixture:
                source = work / f"{stem}-fixture.png"
                fixture_still(source, seed)
                asset = {"provider": "fixture", "kind": "image"}
            elif preferred == "black_screen_card":
                card(source, visual["card_text"], work / "hud-font.ttf")
                asset = {"provider": "title_card", "kind": "image"}
            else:
                if preferred != "ai_image":
                    with timed("stock_sources"):
                        selected = fetcher.fetch(visual)
                if selected:
                    source, asset = selected
                else:
                    with timed("ai_stills"):
                        model = ai_fallback.model_name()
                        image_key = (model, os.getenv("IMAGE_VARIANT"), os.getenv("IMAGE_STEPS"),
                                     seed, visual["ai_fallback_prompt"])
                        if image_geometry:
                            image_key += (image_geometry,)
                        if os.getenv("IMAGE_STORAGE_FP8") == "1":
                            image_key += ("fp8-storage",)
                        source = cache / "visuals" / f"{key(*image_key)}.png"
                        if not source.exists():
                            ai_fallback.generate(visual["ai_fallback_prompt"], source, seed=seed, **image_options)
                        else:
                            cache_hits["ai_stills"] += 1
                    asset = {"provider": "ai_image", "title": Path(model).name if Path(model).is_absolute() else model,
                             "backend": os.getenv("IMAGE_BACKEND", "flux"), "kind": "image"}
            digest = hash_file(source) if asset["kind"] == "image" else asset["sha256"]
            if digest in generated:
                raise RuntimeError(f"Repeated visual at {sid}; supply a distinct title card or visual prompt")
            generated.add(digest)
            credits.append({"scene_id": sid, **asset, "sha256": digest, "start_frame": wall_frame,
                            "frame_count": frames, "timestamp_overlay": scene.get("timestamp_overlay")})
            label = scene.get("timestamp_overlay")
            hud = hud_overlay.hud_filter(label, work, stem) if label else None
            source_label = archival.get(sid, {}).get("display_label")
            if not source_label and meta.get("label_ai_reconstructions") and asset.get("provider") == "ai_image":
                source_label = "AI-GENERATED RECONSTRUCTION — NOT ARCHIVAL FOOTAGE"
            if source_label:
                caption = hud_overlay.source_filter(source_label, work, stem)
                hud = ",".join(filter(None, (hud, caption)))
            clip = work / f"{stem}.mp4"
            with timed("scene_motion_hud"):
                motion_worker.render_scene(source, asset["kind"], visual.get("motion", "none"), frames, hud, clip)
            clips.append(clip)
            if smoke and label:
                checkpoints.append((stem, wall_frame, wall_frame + frames, label))
            wall_frame += frames
        seconds = (wall_frame - chapter_start) / FPS
        chapter_duck = float(chapter.get("ducking_db", meta.get("default_ducking_db", -14)))
        if not math.isfinite(chapter_duck) or not -36 <= chapter_duck <= 0:
            raise ValueError("Chapter ducking_db must be between -36 and 0")
        chapter_audio.append({"chapter_id": chapter["chapter_id"], "start_frame": chapter_start,
                              "end_frame": wall_frame, "ducking_db": chapter_duck})
        if meta.get("global_music_prompt") or meta.get("global_music_file"):
            continue
        with timed("music"):
            model_key = (os.getenv("MUSICGEN_BACKEND", "transformers"), os.getenv("MUSICGEN_MODEL", "facebook/musicgen-small"))
            prompt = chapter["music_prompt"]
            length = round(min(6 if smoke else 29, seconds), 2)
            wav = work / "fixture-music.wav" if fixture else cache / "music" / (key(model_key, prompt, length) + ".wav")
            if fixture:
                fixture_music(wav)
            elif not wav.exists():
                music_worker.generate(prompt, length, wav)
            else:
                cache_hits["music"] += 1
            music.append(audio.music_bed(audio.read(wav, work), (wall_frame - chapter_start) * fps_samples))

    if meta.get("global_music_file"):
        if os.getenv("DOCUMENTARY_RELEASE_MODELS") == "1":
            ai_fallback.release()
            gc.collect()
        with timed("supplied_score"):
            score, score_receipt = score_worker.build(meta, score_timeline, wall_frame * fps_samples, ROOT, work)
            music = [score]
    elif meta.get("global_music_prompt"):
        with timed("music"):
            prompt = meta["global_music_prompt"]
            model_key = (os.getenv("MUSICGEN_BACKEND", "transformers"),
                         os.getenv("MUSICGEN_MODEL", "facebook/musicgen-small"))
            length = round(min(29, wall_frame / FPS), 2)
            wav = cache / "music" / (key(model_key, prompt, length) + ".wav")
            if not wav.exists():
                music_worker.generate(prompt, length, wav)
            else:
                cache_hits["music"] += 1
            music = [audio.music_bed(audio.read(wav, work), wall_frame * fps_samples)]

    if smoke and not fixture:
        if credits[0]["provider"] in {"ai_image", "title_card"} or credits[1]["provider"] != "ai_image":
            raise RuntimeError("Live smoke must acquire a stock image and exercise an independent AI fallback")
    if prefer_nvenc or os.getenv("DOCUMENTARY_RELEASE_MODELS") == "1":
        ai_fallback.release()
        music_worker.release()
        gc.collect()
    duck = float(meta.get("default_ducking_db", -14))
    with timed("audio_mix"):
        voice_track = np.concatenate(voices)
        score_gain = None
        if score_receipt is not None:
            score_gain = audio.score_envelope(voice_track, score_timeline,
                speech_db=float(meta.get("score_speech_db", duck)),
                pause_db=float(meta.get("score_pause_db", -8)),
                title_db=float(meta.get("score_title_db", 0)))
            score_receipt["ducking"] = audio.score_envelope_metrics(score_gain, voice_track, score_timeline,
                speech_db=float(meta.get("score_speech_db", duck)),
                pause_db=float(meta.get("score_pause_db", -8)),
                title_db=float(meta.get("score_title_db", 0)))
        mix = audio.mix_audio(voice_track, np.concatenate(music), np.concatenate(effects),
                              [(c["start_frame"] * fps_samples, c["end_frame"] * fps_samples,
                                c["ducking_db"]) for c in chapter_audio],
                              work, evidence=preserve_audio, gain_envelope=score_gain)
        ducking = audio.verify_duck(work, windows, duck) if smoke else None
    with timed("master_encode_and_decode"):
        master = None
        if prefer_nvenc:
            try:
                master = composer.compose(clips, mix, output, encoder="h264_nvenc", frames=wall_frame)
            except RuntimeError as error:
                if not any(marker in str(error) for marker in (
                    "CUDA_ERROR_OUT_OF_MEMORY", "No capable devices found",
                    "Driver does not support the required nvenc API version",
                    "Cannot load libnvidia-encode", "Unknown encoder 'h264_nvenc'",
                )):
                    raise
                print("NVENC unavailable at master encode; using libx264.", flush=True)
                hw["nvenc_result"] = str(error)
        if master is None:
            master = composer.compose(clips, mix, output, encoder=hw["encoder"], frames=wall_frame)
    with timed("thumbnail"):
        thumbnail = output.with_name(output.stem + "_thumbnail.png")
        if fixture:
            fixture_still(thumbnail, 608, thumbnail=True)
        else:
            thumb_key = key("thumbnail-4k", ai_fallback.model_name(), os.getenv("IMAGE_VARIANT"),
                            os.getenv("IMAGE_STEPS"), meta["thumbnail_prompt"], meta["project_id"])
            cached = cache / "visuals" / f"{thumb_key}.png"
            if cached.exists():
                cache_hits["thumbnail"] = 1
            else:
                thumbnail_worker.generate(meta["thumbnail_prompt"], cached,
                                          seed=int(key(meta["project_id"])[:8], 16))
            shutil.copyfile(cached, thumbnail)
        with Image.open(thumbnail) as sample:
            if sample.size != (3840, 2160):
                raise RuntimeError("Thumbnail is not 3840×2160")
    with timed("evidence_export"):
        hud_checks = visual_evidence(output, work, checkpoints) if smoke else None
        if cues:
            subtitles(cues, output)
        metadata_exporter.export({**meta, "total_frames": wall_frame}, chapters, credits,
                                 output.with_name(output.stem + "_youtube_package.txt"))
        if preserve_audio:
            evidence = output.parent / (output.stem + "_evidence")
            evidence.mkdir(exist_ok=True)
            for p in [*work.glob("*-hud-frame.png"), *work.glob("*-hud.txt"),
                      work / "voice.wav", work / "music-before.wav", work / "music-ducked.wav", work / "sfx.wav", mix]:
                shutil.copyfile(p, evidence / p.name)
    return {"test_mode": "fixture" if fixture else "live" if smoke else "manifest",
            "wall_seconds": round(perf_counter() - started, 3),
            "stage_seconds": {k: round(v, 3) for k, v in times.items()}, "preflight": hw, "master": master,
            "duration_seconds": round(wall_frame / FPS, 3), "credits": credits, "hud": hud_checks,
            "cache_hits": cache_hits, "sha256": hash_file(output),
            "ducking": ducking, "chapter_audio": chapter_audio,
            "manifest_sha256": data.get("_source_sha256"),
            "word_caption_count": sum(len(c) for c in cues),
            "music_backend": "supplied_files" if score_receipt is not None else "fixture" if fixture else os.getenv("MUSICGEN_BACKEND", "transformers"),
            "music_mode": "supplied_score" if score_receipt is not None else "global" if meta.get("global_music_prompt") else "chapter",
            "music_model": None if fixture or score_receipt is not None else os.getenv("MUSICGEN_MODEL", music_worker.DEFAULT_MODEL),
            "supplied_score": score_receipt,
            "thumbnail_pixels": [3840, 2160], "output": output.name}


def main():
    cli = argparse.ArgumentParser(description="Render a documentary manifest or run the two-scene verification")
    group = cli.add_mutually_exclusive_group(required=True)
    group.add_argument("--test", action="store_true", help="Run the live provider verification")
    group.add_argument("--manifest", type=Path)
    cli.add_argument("--fixture", action="store_true", help="Use deterministic test media; skips provider inference")
    cli.add_argument("--software", action="store_true", help="Explicit CPU encoding diagnostic")
    cli.add_argument("--prefer-nvenc", action="store_true",
                     help="Build assets without GPU preflight, try NVENC at export, fall back if unavailable")
    cli.add_argument("--output-dir", type=Path, default=ROOT / "output")
    args = cli.parse_args()
    if args.prefer_nvenc and (not args.software or args.test):
        cli.error("--prefer-nvenc requires --manifest and --software")
    if args.fixture and not args.test:
        cli.error("--fixture requires --test")
    load_dotenv(ROOT / ".env", override=False)
    model_dir = Path(os.environ["HF_HOME"]).expanduser()
    model_dir.mkdir(parents=True, exist_ok=True)
    cache = ROOT / "cache"
    cache.mkdir(exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = validated(ROOT / "projects" / "smoke" / "manifest.json" if args.test else args.manifest)
    slug = "test_fixture_render" if args.fixture else data["project_metadata"]["project_id"]
    output = args.output_dir.resolve() / f"{slug}.mp4"
    with tempfile.TemporaryDirectory(prefix="render-", dir=cache) as tmp:
        evidence = render(data, Path(tmp), output, smoke=args.test, fixture=args.fixture,
                          software=args.software, prefer_nvenc=args.prefer_nvenc)
    receipt = output.with_suffix(".verification.json")
    receipt.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{output}: {evidence['duration_seconds']:.2f}s video, {evidence['wall_seconds']:.2f}s total, "
          f"{evidence['master']['encoder']} at {evidence['master']['fps_wall']:.1f} fps. Evidence: {receipt}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"Render failed: {error}", file=sys.stderr)
        raise SystemExit(1)
