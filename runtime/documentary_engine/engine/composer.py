import json
from pathlib import Path
from time import perf_counter

from .normalizer import FPS, ffmpeg, probe, progress_stats


def compose(clips: list[Path], mix: Path, output: Path, *, encoder: str, frames: int):
    work = clips[0].parent
    concat = work / "scenes.ffconcat"
    concat.write_text("ffconcat version 1.0\n" + "".join(f"file '{p.name}'\n" for p in clips),
                      encoding="utf-8")
    preset = ["-preset", "p4", "-rc", "vbr", "-cq", "19", "-b:v", "0"] if encoder == "h264_nvenc" else [
        "-preset", "veryfast", "-crf", "19"]
    staged = output.with_suffix(".partial.mp4")
    start = perf_counter()
    try:
        progress = ffmpeg("-y", "-f", "concat", "-safe", "1", "-i", concat, "-i", mix.resolve(),
                          "-map", "0:v:0", "-map", "1:a:0", "-frames:v", frames,
                          "-r", str(FPS), "-fps_mode", "cfr",
                          "-c:v", encoder, *preset, "-pix_fmt", "yuv420p", "-color_range", "tv",
                          "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "aac",
                          "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
                          "-progress", "pipe:1", staged.resolve(), cwd=work, hw=encoder == "h264_nvenc")
        seconds = perf_counter() - start
        ffmpeg("-xerror", "-i", staged, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-")
        info = probe(staged)
        v, a = info["streams"]
        if (v["codec_name"], v["width"], v["height"], v["avg_frame_rate"], v["pix_fmt"],
            int(v.get("nb_frames", 0)), a["codec_name"], a["sample_rate"], a["channels"]) != (
                "h264", 1920, 1080, "30/1", "yuv420p", frames, "aac", "48000", 2):
            raise RuntimeError(f"Output format verification failed: {json.dumps(info['streams'])}")
        if abs(float(a["duration"]) - frames / FPS) > 0.05:
            raise RuntimeError(f"Audio/video duration mismatch: {a['duration']} vs {frames / FPS:.3f}")
        staged.replace(output)
    finally:
        staged.unlink(missing_ok=True)
    return {"encoder": encoder, "seconds": round(seconds, 3), "frames": frames,
            "fps_wall": round(frames / seconds, 1), "realtime_factor": round(frames / FPS / seconds, 2),
            "ffmpeg_stats": progress_stats(progress), "full_decode": "passed", "streams": info["streams"]}
