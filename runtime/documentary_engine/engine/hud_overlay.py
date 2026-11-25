import os
import shutil
from pathlib import Path


def install_font(directory: Path):
    from .normalizer import run

    override = os.environ.get("DOCUMENTARY_MONO_FONT")
    if override:
        font = Path(override).expanduser()
    elif shutil.which("fc-match"):
        font = Path(run(["fc-match", "-f", "%{file}", "DejaVu Sans Mono"]).strip())
    else:
        font = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "consola.ttf"
    if not font.is_file():
        raise RuntimeError("Install DejaVu Sans Mono/Liberation Mono or set DOCUMENTARY_MONO_FONT")
    shutil.copyfile(font, directory / "hud-font.ttf")


def hud_filter(text: str, directory: Path, stem: str):
    if len(text) > 85 or any(ord(c) < 32 for c in text):
        raise ValueError("timestamp_overlay must be a single line of at most 85 characters")
    filename = f"{stem}-hud.txt"
    (directory / filename).write_text(f"[ {text} ]", encoding="utf-8")
    return (f"drawtext=fontfile=hud-font.ttf:textfile={filename}:expansion=none:"
            "x=60:y=60:fontsize=32:fontcolor=0xffeeee:shadowcolor=0xff3333@0.35:"
            "shadowx=1:shadowy=1:box=1:boxcolor=black@0.68:boxborderw=12")


def source_filter(text: str, directory: Path, stem: str):
    """Label the date and context of a verified reference photograph."""
    if len(text) > 110 or any(ord(c) < 32 for c in text):
        raise ValueError("Archival display_label must be a short single line")
    filename = f"{stem}-source.txt"
    (directory / filename).write_text(text, encoding="utf-8")
    return (f"drawtext=fontfile=hud-font.ttf:textfile={filename}:expansion=none:"
            "x=60:y=h-62:fontsize=25:fontcolor=white:box=1:"
            "boxcolor=black@0.75:boxborderw=8")
