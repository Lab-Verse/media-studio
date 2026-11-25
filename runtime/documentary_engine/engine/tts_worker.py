"""Generate narration with Kokoro's model and voice defaults."""

import math
import os
import re
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile


@lru_cache(maxsize=2)
def _pipeline(language: str, device: str | None):
    from kokoro import KPipeline

    return KPipeline(lang_code=language, device=device, repo_id="hexgrad/Kokoro-82M")


def narrate(text: str, voice: str, speed: float, destination: Path) -> None:
    """Write mono, 24 kHz Kokoro narration. The caller inserts scene pauses."""
    import numpy as np
    import soundfile as sf

    if not text.strip():
        raise ValueError("Kokoro narration must contain text")
    if not re.fullmatch(r"[abefhijpz][fm]_[a-z0-9_]+", voice):
        raise ValueError("Use a Kokoro voice ID such as am_adam or bm_george")
    if not math.isfinite(speed) or not 0.5 <= speed <= 2.0:
        raise ValueError("Kokoro narration speed must be between 0.5 and 2.0")

    pipeline = _pipeline(voice[0], os.getenv("KOKORO_DEVICE") or None)
    chunks = [
        audio.detach().cpu().numpy()
        for _, _, audio in pipeline(text, voice=voice, speed=speed)
        if audio is not None and audio.numel()
    ]
    if not chunks:
        raise RuntimeError("Kokoro produced no narration samples")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, suffix=".wav", delete=False) as file:
        temporary = Path(file.name)
    try:
        sf.write(temporary, np.concatenate(chunks), 24_000, subtype="PCM_16")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
