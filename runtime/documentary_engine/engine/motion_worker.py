from pathlib import Path

from .normalizer import FPS, HEIGHT, WIDTH, ffmpeg

FILL = (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:"
        f"out_range=tv:out_color_matrix=bt709,crop={WIDTH}:{HEIGHT},setsar=1")
MOTIONS = {"slow_zoom_in", "slow_zoom_out", "slow_pan_left", "slow_pan_right", "slow_pan_up", "none"}


def render_scene(source: Path, kind: str, motion: str, frames: int, hud: str | None, output: Path):
    if motion not in MOTIONS:
        raise ValueError(f"Unsupported motion: {motion}")
    if kind == "video":
        args = ["-stream_loop", "-1", "-i", source.resolve()]
        base = f"fps={FPS},{FILL}"
    else:
        args = ["-i", source.resolve()]
        if motion == "none":
            base = f"{FILL},tpad=stop_mode=clone:stop={frames - 1},fps={FPS}"
        else:
            fraction = f"on/{max(frames - 1, 1)}"
            eased = f"(0.5-0.5*cos(PI*{fraction}))"
            z, x, y = "1.13", "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
            if motion == "slow_zoom_in":
                z = f"1.02+0.14*{eased}"
            elif motion == "slow_zoom_out":
                z = f"1.16-0.14*{eased}"
            elif motion == "slow_pan_up":
                y = f"(ih-ih/zoom)*(1-{eased})"
            else:
                travel = eased if motion == "slow_pan_right" else f"(1-{eased})"
                x = f"(iw-iw/zoom)*{travel}"
            base = ("scale=3840:2160:force_original_aspect_ratio=increase:out_range=tv:out_color_matrix=bt709,format=yuv420p,crop=3840:2160,"
                    f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},setsar=1")
    vf = ",".join(filter(None, [base, hud, "format=yuv420p"]))
    ffmpeg("-y", "-filter_threads", "3", *args, "-an", "-vf", vf, "-frames:v", frames,
           "-c:v", "libx264", "-threads", "5", "-preset", "ultrafast", "-crf", "13",
           "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           output.resolve(), cwd=output.parent)
