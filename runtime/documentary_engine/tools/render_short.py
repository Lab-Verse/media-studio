"""Render a source-reviewed Short with Kokoro, ComfyUI and FFmpeg.

The caller owns Spark's shared GPU reservation. This runner never stops services,
clears queues, creates placeholder media, or publishes to a video platform.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

VERSION = "1.0-production"
COMPOSER_VERSION = "1.1-normalized-master"
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")
COMFY_DEFAULT_URL = "http://127.0.0.1:8188"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def supplied_music(project, reference):
    """Confine a reviewed score reference to its production package."""
    from pathlib import PureWindowsPath
    if (not isinstance(reference, str) or not reference or "\\" in reference
            or PureWindowsPath(reference).drive):
        raise ValueError("Music must be a project-relative POSIX file path")
    relative = Path(reference)
    if relative.is_absolute() or any(p in {".", ".."} for p in reference.split("/")):
        raise ValueError("Music path is outside the project")
    root = Path(project).resolve()
    selected = (root / relative).resolve()
    if not selected.is_relative_to(root) or not selected.is_file():
        raise ValueError("Music must be an existing in-project file")
    return selected


def command(args):
    subprocess.run([str(x) for x in args], check=True)


def probe(path, decode=False):
    result = subprocess.run([FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], check=True, capture_output=True, text=True)
    info = json.loads(result.stdout)
    if not info.get("streams") or float(info.get("format", {}).get("duration", 0)) <= 0:
        raise RuntimeError(f"Empty or invalid media: {path}")
    if decode:
        command([FFMPEG, "-v", "error", "-xerror", "-i", path, "-f", "null", "-"])
    return info


def duration(info, media_type=None):
    if media_type:
        stream = next(s for s in info["streams"] if s["codec_type"] == media_type)
        return float(stream.get("duration", info["format"]["duration"]))
    return float(info["format"]["duration"])


def scene_signature(scene, meta, workflow):
    return digest({"runner": VERSION, "scene": scene, "voice": meta["default_voice"], "workflow": workflow})


def validate_manifest(manifest):
    meta = manifest["project_metadata"]
    for key in ("project_id", "short_id"):
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", meta[key]):
            raise ValueError(f"Unsafe {key}")
    if not re.fullmatch(r"[abefhijpz][fm]_[a-z0-9_]+", meta["default_voice"]):
        raise ValueError("Expected a Kokoro voice ID")
    scenes = manifest["scenes"]
    ids = [s["scene_id"] for s in scenes]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Scene IDs must be nonempty and unique")
    for scene in scenes:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", scene["scene_id"]):
            raise ValueError("Unsafe scene ID")
        if not scene["narration"].strip() or not scene["still_prompt"].strip() or not scene["motion_prompt"].strip():
            raise ValueError("Narration and both visual prompts are required")
        if not math.isfinite(float(scene["target_duration"])) or scene["target_duration"] <= 0:
            raise ValueError("Scene target duration must be positive")


def validate_graph(graph, mapping, schemas=None):
    expected = {"node_prompt_inject": "PrimitiveStringMultiline", "node_seed_inject": "PrimitiveInt", "node_motion_prompt": "CLIPTextEncode", "node_save_still": "SaveImage", "node_save_video": "SaveVideo"}
    for name, class_type in expected.items():
        key = mapping.get(name)
        if key not in graph:
            raise ValueError(f"Missing workflow mapping {name}: {key!r}. Mapping IDs must exactly match the API graph, including percent escapes.")
        if graph[key]["class_type"] != class_type:
            raise ValueError(f"Unexpected class for {name}")
    for key, node in graph.items():
        for name, value in node["inputs"].items():
            if isinstance(value, list) and len(value) == 2:
                if str(value[0]) not in graph or not isinstance(value[1], int):
                    raise ValueError(f"Broken graph link {key}.{name}: {value}")
        if not schemas:
            continue
        class_type = node["class_type"]
        if class_type not in schemas:
            raise ValueError(f"ComfyUI node unavailable: {class_type}")
        required = schemas[class_type].get("input", {}).get("required", {})
        for name, spec in required.items():
            if name not in node["inputs"] and not any(x.startswith(name + ".") for x in node["inputs"]):
                raise ValueError(f"Required graph input missing: {key}.{name}")
            if name not in node["inputs"]:
                continue
            value = node["inputs"][name]
            if isinstance(value, list):
                continue
            options = spec[0] if isinstance(spec[0], list) else spec[1].get("options") if len(spec) > 1 and isinstance(spec[1], dict) else None
            if options is not None and (not options or isinstance(options[0], (str, int, float))) and value not in options:
                raise ValueError(f"Unavailable model/choice at {key}.{name}: {value!r}")


def build_graph(template, mapping, scene, token):
    validate_graph(template, mapping)
    graph = deepcopy(template)
    graph[mapping["node_prompt_inject"]]["inputs"]["value"] = scene["still_prompt"]
    graph[mapping["node_motion_prompt"]]["inputs"]["text"] = scene["motion_prompt"]
    graph[mapping["node_seed_inject"]]["inputs"]["value"] = int(scene["seed"])
    for node in graph.values():
        if "noise_seed" in node["inputs"] and node["inputs"].get("add_noise") == "enable":
            node["inputs"]["noise_seed"] = int(scene["seed"])
    graph[mapping["node_save_still"]]["inputs"]["filename_prefix"] = f"halifax-shorts/{token}/still"
    graph[mapping["node_save_video"]]["inputs"]["filename_prefix"] = f"halifax-shorts/{token}/video"
    return graph


class ComfyClient:
    def __init__(self, base_url=COMFY_DEFAULT_URL):
        self.base_url = base_url.rstrip("/")

    def get(self, route):
        with urllib.request.urlopen(self.base_url + route, timeout=45) as response:
            return json.load(response)

    def submit(self, graph, token):
        payload = json.dumps({"prompt": graph, "client_id": token}).encode()
        request = urllib.request.Request(self.base_url + "/prompt", data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.load(response)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"ComfyUI rejected graph: {e.read().decode(errors='replace')}") from e
        if not result.get("prompt_id") or result.get("node_errors"):
            raise RuntimeError(f"ComfyUI graph not accepted: {result}")
        return result["prompt_id"]

    def reconcile(self, token):
        matches = set()
        queue = self.get("/queue")
        for item in queue.get("queue_running", []) + queue.get("queue_pending", []):
            if token in json.dumps(item):
                matches.add(item[1])
        for prompt_id, item in self.get("/history?max_items=200").items():
            if token in json.dumps(item):
                matches.add(prompt_id)
        if len(matches) != 1:
            raise RuntimeError(f"Submission reconciliation found {len(matches)} matching jobs. Preserve the receipt and reconcile with the operator; refusing duplicate submission.")
        return matches.pop()

    def wait(self, prompt_id, timeout=14400):
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            history = self.get("/history/" + urllib.parse.quote(prompt_id))
            item = history.get(prompt_id)
            if item:
                status = item.get("status", {})
                if status.get("status_str") == "error" or any(m[0] in ("execution_error", "execution_interrupted") for m in status.get("messages", [])):
                    raise RuntimeError(f"ComfyUI job failed: {status}")
                if status.get("completed"):
                    return item
            time.sleep(5)
        raise TimeoutError(f"Job {prompt_id} is not complete. Its receipt is retained; resume to reconcile, do not submit again.")

    def download(self, record, destination):
        query = urllib.parse.urlencode({"filename": record["filename"], "subfolder": record.get("subfolder", ""), "type": record.get("type", "output")})
        temporary = destination.with_suffix(".part")
        with urllib.request.urlopen(self.base_url + "/view?" + query, timeout=180) as response, temporary.open("wb") as f:
            import shutil
            shutil.copyfileobj(response, f)
        temporary.replace(destination)


@lru_cache(maxsize=2)
def kokoro_pipeline(language):
    from kokoro import KPipeline
    return KPipeline(lang_code=language, device="cpu", repo_id="hexgrad/Kokoro-82M")


def bounded_word_timings(text, speech_start, speech_end):
    words = text.split()
    weights = [max(1, len(re.sub(r"\W", "", word))) for word in words]
    total = sum(weights)
    current = speech_start
    result = []
    for word, weight in zip(words, weights):
        end = current + (speech_end - speech_start) * weight / total
        result.append({"word": word, "start": current, "end": end})
        current = end
    return result


def script_word_timings(text, tokens, speech_start, speech_end):
    """Keep proofread script spelling while projecting compatible token timings.

    Punctuation and hyphens do not affect matching. Spoken normalization (for
    example a digit expanded to several words) needs alignment review, so an
    incompatible token sequence uses an explicitly identified estimate.
    """
    normal = lambda text: "".join(c for c in text.casefold() if c.isalnum())
    script = text.split()
    token_chars, char_times = [], []
    for token in tokens:
        chars = normal(token["word"])
        start, end = float(token["start"]), float(token["end"])
        if not chars or not math.isfinite(start) or not math.isfinite(end) or end <= start:
            continue
        token_chars.append(chars)
        char_times.extend((start + (end - start) * i / len(chars), start + (end - start) * (i + 1) / len(chars)) for i in range(len(chars)))
    if not char_times or "".join(token_chars) != "".join(normal(w) for w in script):
        return bounded_word_timings(text, speech_start, speech_end), "speech_bounded_character_weighted_estimate_requires_listening_review"
    result, offset = [], 0
    for word in script:
        length = len(normal(word))
        if not length:
            # A punctuation-only script token belongs to the preceding word.
            if result:
                result[-1]["word"] += " " + word
            continue
        start = max(speech_start, char_times[offset][0])
        end = min(speech_end, char_times[offset + length - 1][1])
        if end <= start:
            return bounded_word_timings(text, speech_start, speech_end), "speech_bounded_character_weighted_estimate_requires_listening_review"
        result.append({"word": word, "start": start, "end": end})
        offset += length
    return result, "proofread_script_projected_to_kokoro_token_timestamps"


def synthesize(scene, voice, directory):
    import numpy as np
    import soundfile as sf
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / "voice.wav"
    receipt_path = directory / "audio.json"
    audio_signature = digest({"version": VERSION, "text": scene["narration"], "voice": voice, "target": scene["target_duration"]})
    if receipt_path.exists() and output.exists():
        previous = read_json(receipt_path)
        if previous["signature"] == audio_signature and previous["sha256"] == sha256(output):
            probe(output)
            if previous.get("caption_timing_method") == "kokoro_token_timestamps":
                previous["words"], previous["caption_timing_method"] = script_word_timings(scene["narration"], previous["words"], previous["speech_start"], previous["speech_end"])
                write_json(receipt_path, previous)
            return previous
    pipeline = kokoro_pipeline(voice[0])

    def generate(speed):
        arrays, tokens, offset = [], [], 0.0
        for result in pipeline(scene["narration"], voice=voice, speed=speed, split_pattern=r"\n+"):
            audio = result.audio if hasattr(result, "audio") else result[2]
            if audio is None:
                continue
            array = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
            if not array.size:
                continue
            arrays.append(array)
            for token in getattr(result, "tokens", None) or []:
                ts, te = getattr(token, "start_ts", None), getattr(token, "end_ts", None)
                if ts is not None and te is not None and str(getattr(token, "text", "")).strip():
                    tokens.append({"word": token.text, "start": offset + float(ts), "end": offset + float(te)})
            offset += len(array) / 24000
        if not arrays:
            raise RuntimeError("Kokoro returned no speech; no silent substitute is allowed")
        return np.concatenate(arrays), tokens

    speed = 1.0
    audio, words = generate(speed)
    desired = max(1.0, float(scene["target_duration"]) - 0.25)
    if len(audio) / 24000 > desired:
        speed = min(1.25, max(0.85, len(audio) / 24000 / desired))
        audio, words = generate(speed)
    if not np.isfinite(audio).all() or np.max(np.abs(audio)) < 0.001:
        raise RuntimeError("Kokoro produced invalid or silent speech")
    active = np.flatnonzero(np.abs(audio) > 0.004)
    if not active.size:
        raise RuntimeError("Kokoro speech is below the activity threshold; cannot establish safe speech/caption bounds")
    speech_start = max(0, int(active[0]) / 24000 - 0.02)
    speech_end = min(len(audio) / 24000, int(active[-1]) / 24000 + 0.06)
    # Only trailing silence is reduced, never a word or breath within narration.
    audio = audio[:min(len(audio), math.ceil((speech_end + 0.15) * 24000))]
    words, word_method = script_word_timings(scene["narration"], words, speech_start, speech_end)
    sf.write(output, audio, 24000, subtype="PCM_16")
    info = probe(output)
    result = {"signature": audio_signature, "sha256": sha256(output), "voice": voice, "speed": speed, "duration": duration(info), "speech_start": speech_start, "speech_end": speech_end, "words": words, "caption_timing_method": word_method}
    write_json(receipt_path, result)
    return result


def ass_time(seconds):
    centis = round(seconds * 100)
    hours, centis = divmod(centis, 360000)
    minutes, centis = divmod(centis, 6000)
    secs, centis = divmod(centis, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centis:02}"


def srt_time(seconds):
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def ass_escape(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", r"\N")


def caption_events(timeline, chunk_size=3):
    events = []
    for timing in timeline:
        words = timing["audio"]["words"]
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            start = timing["start"] + chunk[0]["start"]
            end = timing["start"] + chunk[-1]["end"]
            if end <= start:
                continue
            events.append({"start": start, "end": min(end, timing["start"] + timing["duration"]), "words": [w["word"] for w in chunk], "emphasis": timing["scene"].get("emphasis_words", [])})
    return events


def write_captions(manifest, timeline, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    style = manifest.get("subtitle_styling", {})
    font = style.get("font_name", "DejaVu Sans")
    # Coordinates are authoring-space 720x1280; libass scales to the 1080 master.
    fontsize = min(48, int(style.get("font_size", 44)))
    lines = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 720", "PlayResY: 1280", "ScaledBorderAndShadow: yes", "WrapStyle: 0", "", "[V4+ Styles]", "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding", f"Style: Caption,{font},{fontsize},&H00FFFFFF,&H003CA9E5,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,1.5,2,60,110,250,1", f"Style: Hook,{font},34,&H00FFFFFF,&H003CA9E5,&H00000000,&H70000000,-1,0,0,0,100,100,0,0,3,12,0,8,65,95,235,1", "Style: Label,DejaVu Sans,19,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,3,5,0,7,48,110,165,1", "", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"]
    total = timeline[-1]["start"] + timeline[-1]["duration"]
    hook = manifest.get("hook_overlay", {})
    if hook.get("enabled", True):
        first = ass_escape(hook.get("line_1", "A COLLISION. A FIRE."))
        second = ass_escape(hook.get("line_2", "A CITY CHANGED."))
        lines.append(f"Dialogue: 1,{ass_time(hook.get('start_time', 0))},{ass_time(min(3.4, hook.get('end_time', 3.4)))},Hook,,0,0,0,,{{\\fad(100,150)}}{first}\\N{{\\c&H003CA9E5&}}{second}")
    reconstruction = manifest.get("reconstruction_overlay", {})
    default_label = reconstruction.get("text", "AI RECONSTRUCTION")
    scene_overrides = reconstruction.get("scene_overrides", {})
    for timing in timeline:
        scene = timing["scene"]
        override = scene.get("reconstruction_overlay", scene_overrides.get(scene.get("scene_id"), {}))
        label = override.get("text", default_label) if isinstance(override, dict) else str(override)
        lines.append(f"Dialogue: 0,{ass_time(timing['start'])},{ass_time(timing['start'] + timing['duration'])},Label,,0,0,0,,{ass_escape(label)}")
    events = caption_events(timeline, min(3, int(style.get("chunk_words", 3))))
    srt = []
    for index, event in enumerate(events, 1):
        emphasis = {re.sub(r"[^A-Z0-9-]", "", w.upper()) for w in event["emphasis"]}
        words = []
        for w in event["words"]:
            clean = re.sub(r"[^A-Z0-9-]", "", w.upper())
            text = ass_escape(w.upper())
            words.append(r"{\c&H003CA9E5&}" + text + r"{\c&H00FFFFFF&}" if clean in emphasis else text)
        lines.append(f"Dialogue: 2,{ass_time(event['start'])},{ass_time(event['end'])},Caption,,0,0,0,,{' '.join(words)}")
        srt.append(f"{index}\n{srt_time(event['start'])} --> {srt_time(event['end'])}\n{' '.join(event['words'])}\n")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    output.with_suffix(".srt").write_text("\n".join(srt), encoding="utf-8")
    return events


def get_video(client, scene, meta, template, mapping, directory, signature, schemas):
    raw = directory / "raw.mp4"
    receipt_path = directory / "comfy-job.json"
    receipt = read_json(receipt_path) if receipt_path.exists() else None
    if receipt and receipt["signature"] != signature:
        raise RuntimeError("Cache signature mismatch; refusing to use another scene's receipt")
    if raw.exists() and receipt and receipt.get("raw_sha256") == sha256(raw):
        probe(raw, decode=True)
        return raw, receipt
    if receipt is None:
        token = f"{meta['short_id']}-{scene['scene_id']}-{signature[:12]}-{uuid.uuid4().hex[:10]}"
        graph = build_graph(template, mapping, scene, token)
        validate_graph(graph, mapping, schemas)
        receipt = {"signature": signature, "token": token, "graph_sha256": digest(graph), "state": "submitting", "started_epoch": time.time()}
        write_json(directory / "graph.json", graph)
        # Written before POST: an interrupted response must be reconciled, never retried blindly.
        write_json(receipt_path, receipt)
        prompt_id = client.submit(graph, token)
        receipt.update(prompt_id=prompt_id, state="submitted")
        write_json(receipt_path, receipt)
    elif not receipt.get("prompt_id"):
        receipt.update(prompt_id=client.reconcile(receipt["token"]), state="reconciled")
        write_json(receipt_path, receipt)
    item = client.wait(receipt["prompt_id"])
    outputs = item.get("outputs", {}).get(mapping["node_save_video"], {})
    records = outputs.get("videos") or outputs.get("gifs") or outputs.get("images")
    if not records:
        raise RuntimeError("ComfyUI completed without the mapped video output")
    record = next((x for x in records if str(x.get("filename", "")).lower().endswith((".mp4", ".webm", ".mov"))), None)
    if record is None:
        raise RuntimeError(f"Mapped output is not a video: {records}")
    client.download(record, raw)
    info = probe(raw, decode=True)
    stream = next(x for x in info["streams"] if x["codec_type"] == "video")
    if (stream["width"], stream["height"]) != (720, 1280):
        raise RuntimeError(f"Unexpected ComfyUI output dimensions: {stream['width']}x{stream['height']}")
    rate = stream["avg_frame_rate"].split("/")
    if abs(float(rate[0]) / float(rate[1]) - 32) > 0.001:
        raise RuntimeError("ComfyUI output is not the required interpolated 32fps video")
    if not 4.8 <= duration(info, "video") <= 5.25:
        raise RuntimeError("ComfyUI output is not the requested approximately five-second take")
    receipt.update(state="complete", raw_sha256=sha256(raw), raw_probe=info, elapsed_seconds=time.time() - receipt["started_epoch"], finished_epoch=time.time())
    write_json(receipt_path, receipt)
    return raw, receipt


def retime_filter(source_duration, target_duration, fps=32):
    if source_duration <= 0 or target_duration <= 0:
        raise ValueError("Positive measured durations are required")
    multiplier = target_duration / source_duration
    return f"setpts={multiplier:.12f}*(PTS-STARTPTS),fps={fps},tpad=stop_mode=clone:stop_duration=1,trim=duration={target_duration:.9f},setpts=PTS-STARTPTS"


def retime_scene(video, voice, target_duration, output):
    info = probe(video)
    vf = retime_filter(duration(info, "video"), target_duration)
    command([FFMPEG, "-nostdin", "-y", "-filter_complex_threads", "2", "-i", video, "-i", voice, "-filter_complex", f"[0:v]{vf}[v];[1:a]aresample=48000,apad,atrim=duration={target_duration:.9f},asetpts=PTS-STARTPTS[a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-threads", "4", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", "-t", f"{target_duration:.9f}", output])
    result = probe(output, decode=True)
    if abs(duration(result, "video") - target_duration) > 1 / 32 + 0.01 or abs(duration(result, "audio") - target_duration) > 0.04:
        raise RuntimeError("Retimed scene duration does not match the timeline")
    return result


def filter_filename(path):
    return str(Path(path).resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def assemble(timeline, captions, music, output, db=-18):
    total = timeline[-1]["start"] + timeline[-1]["duration"]
    concat = output.parent / "short_scene_concat.txt"
    concat.write_text("".join("file '" + str(Path(t["retimed"]).resolve()).replace("\\", "/").replace("'", "'\\''") + "'\n" for t in timeline), encoding="utf-8")
    stem_name = output.stem.removesuffix(".rendering")
    voice_stem = output.with_name(stem_name + "_voice.wav")
    music_stem = output.with_name(stem_name + "_music_ducked.wav")
    # Normalize disabled: narration retains its gain. Score starts at exactly -18dB,
    # then actual voice-driven sidechain compression reduces it further during speech.
    audio = f"[0:a]aresample=48000,asplit=3[voice][detector][stem];[1:a]aresample=48000,volume={db}dB,atrim=duration={total:.9f},afade=t=out:st={max(0,total-1):.9f}:d=1[score];[score][detector]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=300:makeup=1[duck];[duck]asplit=2[bg][musicstem];[voice][bg]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95:level=0,loudnorm=I=-16:TP=-1:LRA=11:print_format=json[mix]"
    vf = f"[0:v]scale=1080:1920:flags=lanczos,setsar=1,ass=filename='{filter_filename(captions)}'[picture]"
    command([FFMPEG, "-nostdin", "-y", "-filter_complex_threads", "2", "-f", "concat", "-safe", "0", "-i", concat, "-stream_loop", "-1", "-i", music, "-filter_complex", vf + ";" + audio, "-map", "[picture]", "-map", "[mix]", "-c:v", "libx264", "-threads", "4", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "32", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-t", f"{total:.9f}", "-movflags", "+faststart", output, "-map", "[stem]", "-c:a", "pcm_s24le", "-ar", "48000", "-t", f"{total:.9f}", voice_stem, "-map", "[musicstem]", "-c:a", "pcm_s24le", "-ar", "48000", "-t", f"{total:.9f}", music_stem])
    return {"voice_stem": str(voice_stem), "music_stem": str(music_stem), "score_base_gain_db": db, "sidechain": {"threshold": 0.02, "ratio": 6, "attack_ms": 20, "release_ms": 300}, "amix_normalize": False, "master_loudness_target_lufs": -16, "master_true_peak_target_dbtp": -1, "composer_version": COMPOSER_VERSION}


def retained_visual_progress(timeline, previous):
    old = {t["scene"]["scene_id"]: t for t in previous.get("timeline", [])}
    count = 0
    for timing in timeline:
        retained = old.get(timing["scene"]["scene_id"], {})
        if retained.get("signature") == timing["signature"]:
            for key in ("comfy", "retimed"):
                if key in retained:
                    timing[key] = retained[key]
            if timing.get("comfy", {}).get("state") == "complete":
                count += 1
    return count


def run(args):
    started = time.time()
    manifest_path, workflow_path = Path(args.manifest).resolve(), Path(args.workflow).resolve()
    manifest, template = read_json(manifest_path), read_json(workflow_path)
    validate_manifest(manifest)
    scene_limit = getattr(args, "scene_limit", None)
    visuals_only = getattr(args, "visuals_only", False)
    if scene_limit is not None:
        if not 1 <= scene_limit <= len(manifest["scenes"]):
            raise ValueError("--scene-limit must be between one and the manifest's scene count")
        if args.audio_only or args.assemble_only or args.preflight:
            raise ValueError("--scene-limit is for visual proof runs, not audio-only, assembly-only or preflight")
    mapping, meta = manifest["workflow_mapping"], manifest["project_metadata"]
    validate_graph(template, mapping)
    project = manifest_path.parent.parent
    cache = manifest_path.parent / "cache" / meta["short_id"]
    output_dir = project / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    client = ComfyClient(args.comfy_url)
    schemas = None
    if not args.audio_only and not args.assemble_only:
        client.get("/system_stats")  # Connection failure is fatal, never a mock export.
        schemas = client.get("/object_info")
        validate_graph(template, mapping, schemas)
    if args.preflight:
        print("Preflight passed: exact mappings, live nodes, required inputs and model choices")
        return
    music = supplied_music(project, meta.get("music_track", "assets/music/main_score.mp3"))
    timeline, current = [], 0.0
    for scene in manifest["scenes"]:
        signature = scene_signature(scene, meta, template)
        directory = cache / scene["scene_id"] / signature[:16]
        directory.mkdir(parents=True, exist_ok=True)
        audio = synthesize(scene, meta["default_voice"], directory)
        seconds = max(float(scene["target_duration"]), audio["duration"] + 0.15)
        seconds = math.ceil(seconds * 32) / 32
        timeline.append({"scene": scene, "signature": signature, "directory": str(directory), "start": current, "duration": seconds, "audio": audio, "voice": str(directory / "voice.wav")})
        current += seconds
        print(f"Narration {scene['scene_id']}: {audio['duration']:.2f}s; scene {seconds:.2f}s; voice speed {audio['speed']:.3f}", flush=True)
    captions = output_dir / (meta["project_id"] + "_SHORT.ass")
    events = write_captions(manifest, timeline, captions)
    timeline_path = output_dir / (meta["project_id"] + "_SHORT_timeline.json")
    base_receipt = {"status": "audio_prepared", "runner_version": VERSION, "composer_version": COMPOSER_VERSION, "runner_sha256": sha256(Path(__file__)), "manifest_sha256": sha256(manifest_path), "workflow_sha256": sha256(workflow_path), "music_sha256": sha256(music), "duration_seconds": current, "scene_count": len(timeline), "timeline": timeline, "caption_events": events, "started_epoch": started}
    if timeline_path.exists():
        previous = read_json(timeline_path)
        retained = retained_visual_progress(timeline, previous)
        if retained:
            base_receipt.update(status="resuming_visuals", retained_visual_receipts=retained, previous_status=previous.get("status"))
    write_json(timeline_path, base_receipt)
    if args.audio_only:
        print(f"Audio and captions prepared: {timeline_path}")
        return
    selected = timeline if scene_limit is None else timeline[:scene_limit]
    for timing in selected:
        directory = Path(timing["directory"])
        raw = directory / "raw.mp4"
        if args.assemble_only:
            receipt = read_json(directory / "comfy-job.json")
            if receipt.get("signature") != timing["signature"] or receipt.get("raw_sha256") != sha256(raw):
                raise RuntimeError("Assembly requires an exact verified ComfyUI render")
            probe(raw, decode=True)
        else:
            raw, receipt = get_video(client, timing["scene"], meta, template, mapping, directory, timing["signature"], schemas)
        timing["comfy"] = receipt
        timing["retimed"] = str(directory / "retimed.mkv")
        retime_scene(raw, timing["voice"], timing["duration"], Path(timing["retimed"]))
        base_receipt.update(status="visuals_in_progress", completed_visual_count=sum(t.get("comfy", {}).get("state") == "complete" for t in timeline))
        write_json(timeline_path, base_receipt)
    if visuals_only or scene_limit is not None:
        complete = all(t.get("comfy", {}).get("state") == "complete" for t in timeline)
        base_receipt.update(status="visuals_prepared" if complete else "visuals_partial", processed_scene_count=len(selected), elapsed_seconds=time.time() - started)
        write_json(timeline_path, base_receipt)
        print(f"Visual preparation saved ({len(selected)} scene(s) processed); no master was assembled: {timeline_path}")
        return
    master = output_dir / (meta["project_id"] + "_SHORT.mp4")
    rendering = master.with_name(master.stem + ".rendering.mp4")
    mix = assemble(timeline, captions, music, rendering, float(meta.get("music_ducking_db", -18)))
    info = probe(rendering, decode=True)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
    checks = {"width_1080": video["width"] == 1080, "height_1920": video["height"] == 1920, "fps_32": video["avg_frame_rate"] == "32/1", "h264": video["codec_name"] == "h264", "aac": audio["codec_name"] == "aac", "audio_48khz": audio["sample_rate"] == "48000", "duration_matches": abs(duration(info) - current) < 0.1, "all_scenes": len(timeline) == len(manifest["scenes"])}
    if not all(checks.values()):
        raise RuntimeError(f"Master did not satisfy delivery checks: {checks}")
    rendering.replace(master)
    base_receipt.update(status="rendered_awaiting_picture_and_audio_review", master=str(master), master_sha256=sha256(master), master_probe=info, checks=checks, full_decode="passed", mix=mix, elapsed_seconds=time.time() - started, caption_timing_methods=sorted({t["audio"]["caption_timing_method"] for t in timeline}))
    write_json(timeline_path, base_receipt)
    write_json(output_dir / (meta["project_id"] + "_SHORT_QA.json"), base_receipt)
    print(f"Rendered and decoded master: {master}; {current:.3f}s; review picture, sound and captions before release.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--workflow", default="tools/workflow_shorts_wan21.json")
    parser.add_argument("--comfy-url", default=COMFY_DEFAULT_URL)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--audio-only", action="store_true")
    modes.add_argument("--assemble-only", action="store_true")
    modes.add_argument("--visuals-only", action="store_true", help="Prepare video takes and retimed clips without assembling a master")
    modes.add_argument("--preflight", action="store_true")
    parser.add_argument("--scene-limit", type=int, help="Render only this many prefix scenes as a visual proof; never assembles a master")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
