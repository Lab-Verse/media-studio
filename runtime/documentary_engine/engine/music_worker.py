"""Generate a chapter music bed with Meta MusicGen."""

import math
import os
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile

DEFAULT_MODEL = "facebook/musicgen-small"
DEFAULT_MODEL_LICENSE = "CC BY-NC 4.0"


@lru_cache(maxsize=1)
def _load(backend: str, model_id: str, device: str):
    if backend == "audiocraft":
        from audiocraft.models import MusicGen

        return MusicGen.get_pretrained(model_id, device=device)

    import torch
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    processor = AutoProcessor.from_pretrained(model_id)
    model = MusicgenForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=torch.float16 if device.startswith("cuda") else torch.float32,
    ).to(device).eval()
    return processor, model


def _loop_ready(audio, sample_rate: int):
    """Overlap the bed's tail into its head so PCM loops have no hard cut."""
    import numpy as np

    blend_frames = min(round(sample_rate * 0.3), len(audio) // 8)
    if blend_frames < 2:
        return audio
    weight = np.linspace(0, 1, blend_frames, dtype=np.float32)[:, None]
    crossfade = audio[-blend_frames:] * (1 - weight) + audio[:blend_frames] * weight
    return np.concatenate((crossfade, audio[blend_frames:-blend_frames]), axis=0)


def generate(prompt: str, seconds: float, destination: Path) -> None:
    """Write up to thirty seconds of MusicGen audio for continuous looping."""
    import numpy as np
    import soundfile as sf
    import torch

    if not prompt.strip():
        raise ValueError("MusicGen requires a text prompt")
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("MusicGen duration must be positive and finite")
    backend = os.getenv("MUSICGEN_BACKEND", "transformers")
    if backend not in {"transformers", "audiocraft"}:
        raise ValueError("MUSICGEN_BACKEND must be transformers or audiocraft")
    device = os.getenv("MUSICGEN_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
    model_id = os.getenv("MUSICGEN_MODEL", DEFAULT_MODEL)
    # Reserve the crossfade and codebook delay within MusicGen's position limit.
    generation_seconds = min(30, max(1, seconds + 0.36))
    loaded = _load(backend, model_id, device)
    with torch.inference_mode():
        if backend == "audiocraft":
            loaded.set_generation_params(duration=generation_seconds)
            tracks = loaded.generate([prompt])
            sample_rate = loaded.sample_rate
        else:
            processor, model = loaded
            inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(device)
            tokens = min(1503, math.ceil(generation_seconds * 50) + 3)
            tracks = model.generate(**inputs, do_sample=True, guidance_scale=3, max_new_tokens=tokens)
            sample_rate = model.config.audio_encoder.sampling_rate

    samples = tracks[0].detach().float().cpu().numpy().T
    if len(samples) == 0 or not np.isfinite(samples).all():
        raise RuntimeError("MusicGen returned empty or invalid audio")
    samples = _loop_ready(samples, sample_rate)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, suffix=".wav", delete=False) as file:
        temporary = Path(file.name)
    try:
        sf.write(temporary, samples, sample_rate, subtype="PCM_16")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def release():
    """Drop the cached model before requesting encoder resources."""
    _load.cache_clear()
