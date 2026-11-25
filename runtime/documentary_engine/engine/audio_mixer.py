from pathlib import Path

import numpy as np
import soundfile as sf

from .normalizer import FPS, SR, ffmpeg

HOP = SR // 100
ATTACK = 0.06
RELEASE = 0.38


def read(path: Path, work: Path):
    converted = work / "resample-tmp.wav"
    ffmpeg("-y", "-i", path, "-vn", "-ac", "2", "-ar", SR, "-c:a", "pcm_f32le", converted)
    data, _ = sf.read(converted, dtype="float32", always_2d=True)
    return data


def write(path, data):
    sf.write(path, data, SR, subtype="FLOAT")


def _speech_blocks(voice: np.ndarray):
    if voice.ndim != 2 or voice.shape[1] != 2 or not len(voice):
        raise ValueError("Voice audio must be nonempty stereo PCM")
    if not np.isfinite(voice).all():
        raise ValueError("Voice audio contains nonfinite samples")
    samples = len(voice)
    padded = np.pad(voice, ((0, -samples % HOP), (0, 0)))
    level = np.sqrt(np.mean(padded.reshape(-1, HOP, 2) ** 2, axis=(1, 2)))
    threshold = max(0.003, float(np.percentile(level, 97)) * 0.035)
    speech = level >= threshold
    # Bridge intra-word gaps and anticipate each phrase by one 10 ms block.
    speech = np.convolve(speech.astype(int), np.ones(7, dtype=int), mode="full")[4 : 4 + len(speech)] > 0
    return speech


def sidechain(voice: np.ndarray, duck_db: float):
    if not np.isfinite(duck_db) or not -36 <= duck_db <= 0:
        raise ValueError("default_ducking_db must be between -36 and 0")
    samples = len(voice)
    speech = _speech_blocks(voice)
    floor = 10 ** (duck_db / 20)
    gain, gains = 1.0, []
    for active in speech:
        target, period = (floor, ATTACK) if active else (1.0, RELEASE)
        gain += (target - gain) * (1 - np.exp(-0.01 / period))
        gains.append(gain)
    return np.interp(np.arange(samples), (np.arange(len(gains)) + 1) * HOP, gains, left=1.0).astype("float32")


def _score_targets(voice, timeline, speech_db, pause_db, title_db):
    for value in (speech_db, pause_db, title_db):
        if not np.isfinite(value) or not -60 <= value <= 0:
            raise ValueError("Score gains must be finite decibels between -60 and 0")
    speech = _speech_blocks(voice)
    targets = np.full(len(speech), pause_db, dtype="float32")
    states = np.full(len(speech), "pause", dtype="<U6")
    positions = np.arange(len(speech)) * HOP
    previous = 0
    for scene in timeline:
        start, end = scene["start_sample"], scene["end_sample"]
        if not isinstance(start, int) or not isinstance(end, int) or start != previous or not start < end <= len(voice):
            raise ValueError("Score timeline must contain contiguous integer sample intervals")
        voiced_end = scene.get("voice_end_sample", end)
        if not isinstance(voiced_end, int) or not start <= voiced_end <= end:
            raise ValueError("voice_end_sample must fall within its scene")
        selected = (positions >= start) & (positions < end)
        narrated = bool(scene.get("narrated"))
        if bool(scene.get("title_card")) and not narrated:
            targets[selected], states[selected] = title_db, "title"
        elif narrated:
            active = selected & speech & (positions < voiced_end)
            targets[active], states[active] = speech_db, "speech"
        previous = end
    if previous != len(voice):
        raise ValueError("Score timeline must cover the entire voice array")
    return targets, states


def score_envelope(voice, timeline, *, speech_db=-14.0, pause_db=-8.0, title_db=0.0):
    """Apply the supplied-score speech, pause and silent-title gain policy."""
    targets, _ = _score_targets(voice, timeline, speech_db, pause_db, title_db)
    targets = 10 ** (targets / 20)
    gain = float(targets[0])
    gains = np.empty(len(targets), dtype="float32")
    for index, target in enumerate(targets):
        period = ATTACK if target < gain else RELEASE
        gain += (float(target) - gain) * (1 - np.exp(-0.01 / period))
        gains[index] = gain
    return np.interp(
        np.arange(len(voice)), np.arange(len(gains)) * HOP, gains,
        left=float(gains[0]), right=float(gains[-1]),
    ).astype("float32")


def score_envelope_metrics(gain, voice, timeline, *, speech_db=-14.0, pause_db=-8.0, title_db=0.0):
    """Describe the rendered gain envelope before the final mix safety trim."""
    targets, states = _score_targets(voice, timeline, speech_db, pause_db, title_db)
    values = 20 * np.log10(np.maximum(gain, np.finfo("float32").tiny))
    block_values = values[::HOP]
    block_lengths = np.minimum(HOP, len(voice) - np.arange(len(states)) * HOP)
    counts = {
        state: int(np.sum(block_lengths[(states == state) & (np.abs(block_values - target) <= 0.2)]))
        for state, target in (("speech", speech_db), ("pause", pause_db), ("title", title_db))
    }
    return {
        "targets_db": {"speech": speech_db, "pause": pause_db, "title": title_db},
        "minimum_db": float(values.min()), "maximum_db": float(values.max()),
        "samples_at_targets": counts,
        "speech_blocks": int(np.count_nonzero(states == "speech")),
        "pause_blocks": int(np.count_nonzero(states == "pause")),
        "title_blocks": int(np.count_nonzero(states == "title")),
        "measurement": "Music stem gain before final mix peak safety trim",
    }


def music_bed(audio: np.ndarray, samples: int):
    if not len(audio):
        raise ValueError("Empty music bed")
    if len(audio) >= samples:
        output = audio[:samples].copy()
    else:
        overlap = min(SR // 2, len(audio) // 4)
        output = np.empty((max(samples, len(audio)) + len(audio), 2), dtype="float32")
        output[:len(audio)] = audio
        end = len(audio)
        ramp = np.linspace(0, 1, overlap, dtype="float32")[:, None]
        while end < samples:
            if overlap:
                output[end - overlap:end] = output[end - overlap:end] * (1 - ramp) + audio[:overlap] * ramp
            output[end:end + len(audio) - overlap] = audio[overlap:]
            end += len(audio) - overlap
        output = output[:samples].copy()
    fade = min(SR // 4, len(output) // 2)
    if fade:
        ramp = np.linspace(0, 1, fade)[:, None]
        output[:fade] *= ramp
        output[-fade:] *= ramp[::-1]
    rms = float(np.sqrt(np.mean(output ** 2)))
    return output * (min(3.0, 0.115 / rms) if rms else 1.0)


def sfx_wave(name: str):
    # Original generated foley. The project can override individual WAVs in assets/sfx.
    shapes = {
        "ticking_clock": ("tick", 1.25, 1700), "warning_buzzer": ("pulse", .7, 315),
        "sub_bass_drop": ("drop", .86, 115), "paper_rustle": ("noise", .46, 630),
        "radio_static": ("noise", .62, 2100), "cinematic_riser": ("riser", 1.4, 210),
        "sub_bass_mechanical_thud": ("drop", .57, 86), "siren_alarm": ("siren", 1.1, 670),
        "camera_shutter": ("tick", .28, 1340), "radio_beep": ("pulse", .27, 1040),
        "teletype_chatter": ("tick", .72, 1520),
        "heavy_metal_door_slam": ("metal_slam", 1.6, 78),
    }
    stem = Path(name).stem
    if stem not in shapes:
        raise ValueError(f"Unknown sound effect: {name}. Supply a WAV in assets/sfx.")
    kind, length, frequency = shapes[stem]
    t = np.arange(round(length * SR)) / SR
    if kind == "noise":
        rng = np.random.default_rng(frequency)
        data = np.diff(rng.uniform(-1, 1, len(t) + 1)) * (.05 + .11 * np.sin(t * 26) ** 2)
    elif kind == "metal_slam":
        rng = np.random.default_rng(197103)
        impact = rng.uniform(-1, 1, len(t)) * np.exp(-70 * t)
        body = sum(np.sin(2 * np.pi * f * t) * np.exp(-d * t)
                   for f, d in ((78, 5.5), (143, 4), (389, 3.2), (811, 6)))
        data = .2 * impact + .12 * body
    elif kind == "tick":
        data = .26 * np.sin(2 * np.pi * frequency * t) * np.exp(-80 * (t % .41))
    elif kind == "drop":
        data = .34 * np.sin(2 * np.pi * frequency * np.log1p(3 * t) / 3) * np.exp(-4.3 * t)
    elif kind == "riser":
        data = .16 * (t / length) * np.sin(2 * np.pi * (frequency * t + 380 * t ** 2))
    elif kind == "siren":
        data = .19 * np.sin(2 * np.pi * frequency * t + 36 * np.sin(2 * np.pi * 1.8 * t))
    else:
        data = .21 * np.sin(2 * np.pi * frequency * t) * (np.sin(2 * np.pi * 4.2 * t) >= 0)
    data *= np.minimum(1, np.minimum(t * 250, (length - t) * 40))
    return np.column_stack((data, data)).astype("float32")


def mix_audio(voice, music, sfx, duck_db, work: Path, *, evidence: bool, gain_envelope=None):
    if voice.shape != music.shape or voice.shape != sfx.shape:
        raise ValueError("Voice, music and SFX must have matching stereo sample lengths")
    if gain_envelope is not None:
        gain = np.asarray(gain_envelope, dtype="float32")
        if gain.shape != (len(voice),) or not np.isfinite(gain).all() or np.any((gain < 0) | (gain > 1)):
            raise ValueError("The music gain envelope must have one finite gain between 0 and 1 per sample")
    elif isinstance(duck_db, list):
        gain = np.ones(len(voice), dtype="float32")
        for start, stop, target in duck_db:
            gain[start:stop] = sidechain(voice[start:stop], target)
    else:
        gain = sidechain(voice, duck_db)
    ducked = music * gain[:, None]
    mix = voice + ducked + sfx
    peak = float(np.abs(mix).max())
    if peak > 0.94:
        mix *= 0.94 / peak
    write(work / "mix.wav", mix)
    if evidence:
        for name, audio in (("voice", voice), ("music-before", music),
                            ("music-ducked", ducked), ("sfx", sfx)):
            write(work / f"{name}.wav", audio)
    return work / "mix.wav"


def verify_duck(work: Path, windows: list[tuple[int, int]], target: float):
    original, _ = sf.read(work / "music-before.wav", always_2d=True)
    ducked, _ = sf.read(work / "music-ducked.wav", always_2d=True)
    sfx, _ = sf.read(work / "sfx.wav", always_2d=True)

    def attenuation(a, b):
        a, b = round(a * SR / FPS), round(b * SR / FPS)
        x = np.sum(original[a:b] ** 2)
        y = np.sum(ducked[a:b] ** 2)
        if x == 0 or y == 0:
            raise RuntimeError("No signal in ducking measurement window")
        return round(10 * np.log10(y / x), 2)

    measures = []
    for start, stop in windows:
        speech = attenuation(start + 9, stop - 2)
        recovery = attenuation(stop + 26, stop + 37)
        if not target - .3 <= speech <= target + 3 or not -1.8 <= recovery <= 0.1:
            raise RuntimeError(f"Ducking outside tolerance: {speech:g} dB during speech, {recovery:g} dB after pause")
        measures.append({"speech_db": speech, "recovery_db": recovery,
                         "voice_frames": [start, stop]})
    if not measures or float(np.max(np.abs(sfx))) < 0.05:
        raise RuntimeError("Smoke duck/SFX evidence missing")
    first_sfx = int(np.flatnonzero(np.max(np.abs(sfx), axis=1) > 0.002)[0])
    expected = round(0.18 * SR)
    if abs(first_sfx - expected) > round(0.04 * SR):
        raise RuntimeError(f"Unexpected first SFX placement: {first_sfx / SR:.3f}s")
    return {"target_db": target, "measurements": measures, "first_sfx_seconds": round(first_sfx / SR, 3)}
