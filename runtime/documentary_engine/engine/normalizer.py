import json
import os
import shutil
import subprocess
from pathlib import Path
from time import perf_counter

FPS, WIDTH, HEIGHT, SR = 30, 1920, 1080, 48000


def run(args, *, cwd=None):
    result = subprocess.run([str(x) for x in args], cwd=cwd, capture_output=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} exited {result.returncode}: {result.stderr.strip()[-3000:]}")
    return result.stdout


def ffmpeg(*args, cwd=None, hw=False):
    binary = os.environ.get("FFMPEG", "ffmpeg")
    if hw:
        binary = os.environ.get("FFMPEG_NVENC", binary)
    return run([binary, "-nostdin", "-hide_banner", "-v", "error",
                *args], cwd=cwd)


def probe(path):
    return json.loads(run([os.environ.get("FFPROBE", "ffprobe"), "-v", "error",
                           "-show_streams", "-show_format", "-of", "json", path]))


def preflight(directory: Path, *, software: bool):
    from .hud_overlay import install_font

    install_font(directory)
    encoder = "libx264" if software else "h264_nvenc"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30", "-vf",
           "drawtext=fontfile=hud-font.ttf:text=HUD:fontsize=32", "-frames:v", "1",
           "-f", "null", "-", cwd=directory)
    start = perf_counter()
    result = ffmpeg("-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30",
                    "-frames:v", "60", "-pix_fmt", "yuv420p", "-c:v", encoder,
                    "-progress", "pipe:1", "-f", "null", "-", cwd=directory, hw=not software)
    elapsed = perf_counter() - start
    binary = os.environ.get("FFMPEG", "ffmpeg")
    if not software:
        binary = os.environ.get("FFMPEG_NVENC", binary)
    return {"encoder": encoder, "frames": 60, "seconds": round(elapsed, 3),
            "fps_wall": round(60 / elapsed, 1), "ffmpeg": shutil.which(binary),
            "ffmpeg_stats": progress_stats(result)}


def progress_stats(data):
    stats = {}
    for line in data.splitlines():
        key, _, value = line.partition("=")
        if key in {"frame", "fps", "speed", "out_time"}:
            stats[key] = value.strip()
    return stats
