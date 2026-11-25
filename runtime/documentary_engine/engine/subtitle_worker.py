"""Transcribe narration with the local faster-whisper engine."""

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _model(model_name: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model_name, device=device, compute_type=compute_type)


def transcribe(wav: Path) -> list[tuple[float, float, str]]:
    """Return timed words relative to the beginning of the narration WAV."""
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "float16" if device == "cuda" else "int8")
    model = _model(os.getenv("WHISPER_MODEL", "tiny.en"), device, compute_type)
    # Pass 16 kHz PCM directly; PyAV releases differ in their file-open API.
    import numpy as np
    import subprocess
    result = subprocess.run([os.getenv("FFMPEG", "ffmpeg"), "-nostdin", "-v", "error", "-i", str(wav),
                             "-vn", "-ar", "16000", "-ac", "1", "-f", "f32le", "-"], capture_output=True)
    if result.returncode or not result.stdout:
        raise RuntimeError("Could not decode narration to 16 kHz PCM for Whisper")
    waveform = np.frombuffer(result.stdout, dtype="<f4").astype("float32", copy=False)
    segments, _ = model.transcribe(waveform, beam_size=5, word_timestamps=True)
    return [
        (float(word.start), float(word.end), word.word.strip())
        for segment in segments
        for word in segment.words or []
        if word.end > word.start >= 0 and word.word.strip()
    ]
