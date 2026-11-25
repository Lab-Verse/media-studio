"""Assemble supplied music files at exact scene sample boundaries."""

import hashlib
import math
from pathlib import Path, PureWindowsPath

import numpy as np

from . import audio_mixer as audio
from .normalizer import SR


def _resolve(reference, root):
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("Supplied score references must be nonempty relative paths")
    if Path(reference).is_absolute() or PureWindowsPath(reference).drive or "\\" in reference:
        raise ValueError("Supplied score references must be relative POSIX paths")
    allowed = (root / "assets" / "music").resolve()
    path = (root / reference).resolve()
    if not allowed.is_relative_to(root) or not path.is_relative_to(allowed):
        raise ValueError("Supplied scores must stay within assets/music")
    if not path.is_file():
        raise ValueError(f"Supplied music file is missing: {reference}")
    return path


def _loop_into(output, source, *, overlap_samples=SR // 2):
    """Loop PCM with complementary weights without source-level normalization."""
    if not len(source) or source.ndim != 2 or source.shape[1] != 2 or not np.isfinite(source).all():
        raise ValueError("Supplied score must contain finite nonempty stereo PCM")
    length = min(len(source), len(output))
    output[:length] = source[:length]
    end = length
    overlap = min(overlap_samples, len(source) // 4)
    while end < len(output):
        fade = min(overlap, end)
        new_start = end - fade
        if fade:
            ramp = np.linspace(0, 1, fade, dtype="float32")[:, None]
            output[new_start:end] = output[new_start:end] * (1 - ramp) + source[:fade] * ramp
        length = min(len(source) - fade, len(output) - end)
        output[end:end + length] = source[fade:fade + length]
        end += length


def build(metadata, timeline, samples, source_root: Path, work: Path):
    """Return a sample-aligned stereo score plus a source and transition receipt.

    Timeline entries use absolute start_sample and end_sample boundaries. Each
    music_transition path starts at its scene boundary and fades for four
    seconds unless score_crossfade_seconds overrides that duration.
    """
    if not isinstance(samples, int) or samples <= 0:
        raise ValueError("Score length must be a positive integer sample count")
    seconds = float(metadata.get("score_crossfade_seconds", 4.0))
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("score_crossfade_seconds must be positive and finite")
    fade_samples = max(1, round(seconds * SR))
    root = source_root.resolve()
    main = _resolve(metadata.get("global_music_file"), root)
    current = main
    previous_end, previous_transition_end = 0, 0
    changes = []
    for scene in timeline:
        start, end = scene["start_sample"], scene["end_sample"]
        if not isinstance(start, int) or not isinstance(end, int) or start != previous_end or not start < end <= samples:
            raise ValueError("Score timeline must contain contiguous integer sample intervals")
        if scene.get("music_transition"):
            target = _resolve(scene["music_transition"], root)
            if start < previous_transition_end:
                raise ValueError("Score crossfades must not overlap")
            if start + fade_samples > samples:
                raise ValueError("The timeline ends before the score crossfade can complete")
            changes.append((scene.get("scene_id"), start, target))
            previous_transition_end = start + fade_samples
        previous_end = end
    if previous_end != samples:
        raise ValueError("Score timeline must cover the complete sample count")

    decoded, receipts = {}, []
    for path in dict.fromkeys([main, *(target for _, _, target in changes)]):
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        pcm = audio.read(path, work)
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise ValueError("Supplied score changed while it was decoded")
        if not len(pcm) or not np.isfinite(pcm).all():
            raise ValueError(f"Supplied score is empty or invalid: {path.relative_to(root)}")
        decoded[path] = pcm
        receipts.append({
            "path": path.relative_to(root).as_posix(), "sha256": digest,
            "source_samples": len(pcm), "duration_seconds": len(pcm) / SR,
        })
    output = np.empty((samples, 2), dtype="float32")
    _loop_into(output, decoded[main])
    transitions = []
    for scene_id, start, target in changes:
        # Preserve only the outgoing crossfade span before writing the new bed.
        outgoing = output[start:start + fade_samples].copy()
        _loop_into(output[start:], decoded[target])
        ramp = np.linspace(0, 1, fade_samples, dtype="float32")[:, None]
        output[start:start + fade_samples] = outgoing * (1 - ramp) + output[start:start + fade_samples] * ramp
        transitions.append({
            "scene_id": scene_id, "start_sample": start, "end_sample": start + fade_samples,
            "start_seconds": start / SR, "end_seconds": (start + fade_samples) / SR,
            "from_path": current.relative_to(root).as_posix(),
            "to_path": target.relative_to(root).as_posix(),
            "crossfade_seconds": fade_samples / SR, "curve": "linear_amplitude",
        })
        current = target
    return output, {
        "mode": "supplied_score", "sample_rate": SR, "channels": 2, "samples": samples,
        "duration_seconds": samples / SR, "crossfade_seconds": fade_samples / SR,
        "files": receipts, "transitions": transitions,
    }
