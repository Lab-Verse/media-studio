"""Create an upload-ready 16:9 thumbnail from the local image model."""

from pathlib import Path
from tempfile import TemporaryDirectory

from . import ai_fallback


def generate(prompt: str, destination: Path, *, seed: int) -> None:
    """Generate at 1024×576 and upscale the finished thumbnail to 4K."""
    from PIL import Image, ImageOps

    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as name:
        temporary = Path(name)
        source = temporary / "source.png"
        output = temporary / destination.name
        ai_fallback.generate(prompt, source, seed=seed)
        with Image.open(source) as generated:
            thumbnail = ImageOps.fit(generated.convert("RGB"), (3840, 2160), Image.Resampling.LANCZOS)
        if destination.suffix.lower() in {".jpg", ".jpeg"}:
            thumbnail.save(output, format="JPEG", quality=92, optimize=True, progressive=True)
        elif destination.suffix.lower() == ".png":
            thumbnail.save(output, format="PNG", optimize=True)
        else:
            raise ValueError("Thumbnail output must be a PNG or JPEG")
        output.replace(destination)
