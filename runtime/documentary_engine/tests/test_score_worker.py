import hashlib
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

from engine import audio_mixer as audio
from engine import score_worker as score
from engine.normalizer import SR


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.directory = self.root / "assets" / "music"
        self.directory.mkdir(parents=True)
        self.main = self.directory / "main.wav"
        self.coda = self.directory / "coda.wav"
        sf.write(self.main, np.full((SR, 2), .2, dtype="float32"), SR, subtype="FLOAT")
        sf.write(self.coda, np.full((SR, 2), .4, dtype="float32"), SR, subtype="FLOAT")
        self.timeline = [
            {"scene_id": "main", "start_sample": 0, "end_sample": 2 * SR},
            {"scene_id": "coda", "start_sample": 2 * SR, "end_sample": 8 * SR,
             "music_transition": "assets/music/coda.wav"},
        ]

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def read_pcm(path, work):
        data, rate = sf.read(path, dtype="float32", always_2d=True)
        if rate != SR:
            raise ValueError("Fixture audio must be 48 kHz")
        return data

    def test_score_coda_four_second_fade_exact_length_receipt(self):
        with patch.object(audio, "read", side_effect=self.read_pcm):
            output, receipt = score.build(
                {"global_music_file": "assets/music/main.wav"}, self.timeline,
                8 * SR, self.root, self.root,
            )
        self.assertEqual(output.shape, (8 * SR, 2))
        np.testing.assert_allclose(output[:2 * SR], .2, atol=1e-7)
        self.assertAlmostEqual(output[4 * SR, 0], .3, places=5)
        np.testing.assert_allclose(output[6 * SR:], .4, atol=1e-7)
        self.assertLessEqual(float(output.max()), .4000001)
        self.assertEqual(receipt["transitions"][0]["end_sample"], 6 * SR)
        self.assertEqual(receipt["transitions"][0]["curve"], "linear_amplitude")
        self.assertEqual(receipt["files"][0]["sha256"], hashlib.sha256(self.main.read_bytes()).hexdigest())
        self.assertEqual(receipt["samples"], 8 * SR)

    def test_correlated_scores_have_no_crossfade_level_bump(self):
        sf.write(self.coda, np.full((SR, 2), .2, dtype="float32"), SR, subtype="FLOAT")
        with patch.object(audio, "read", side_effect=self.read_pcm):
            output, _ = score.build(
                {"global_music_file": "assets/music/main.wav"}, self.timeline,
                8 * SR, self.root, self.root,
            )
        np.testing.assert_allclose(output, .2, atol=1e-7)

    def test_path_escape_and_incomplete_crossfade_rejected(self):
        outside = self.root / "outside.wav"
        outside.write_bytes(self.main.read_bytes())
        for reference in ("outside.wav", "assets/music/../../../outside.wav", str(self.main.resolve()),
                          "C:/assets/music/main.wav", "../assets/music/main.wav"):
            with self.assertRaises(ValueError):
                score.build({"global_music_file": reference}, self.timeline, 8 * SR, self.root, self.root)
        short = [{"start_sample": 0, "end_sample": 2 * SR},
                 {"start_sample": 2 * SR, "end_sample": 3 * SR, "music_transition": "assets/music/coda.wav"}]
        with self.assertRaisesRegex(ValueError, "ends before"):
            score.build({"global_music_file": "assets/music/main.wav"}, short, 3 * SR, self.root, self.root)

    def test_envelope_speech_pause_title_and_narrated_title(self):
        voice = np.zeros((12 * SR, 2), dtype="float32")
        t = np.arange(3 * SR) / SR
        voice[:3 * SR] = (.2 * np.sin(2 * np.pi * 220 * t))[:, None]
        voice[9 * SR:] = voice[:3 * SR]
        timeline = [
            {"start_sample": 0, "end_sample": 6 * SR, "voice_end_sample": 3 * SR, "narrated": True},
            {"start_sample": 6 * SR, "end_sample": 9 * SR, "narrated": False, "title_card": True},
            {"start_sample": 9 * SR, "end_sample": 12 * SR, "narrated": True, "title_card": True},
        ]
        gain = audio.score_envelope(voice, timeline)
        self.assertEqual(len(gain), len(voice))
        for second, expected in ((2,-14), (5,-8), (8.8,0), (11,-14)):
            self.assertAlmostEqual(20 * np.log10(gain[round(second * SR)]), expected, delta=.03)
        self.assertLessEqual(float(gain.max()), 1)
        report = audio.score_envelope_metrics(gain, voice, timeline)
        self.assertGreater(report["samples_at_targets"]["speech"], 4 * SR)
        self.assertGreater(report["samples_at_targets"]["pause"], SR)
        self.assertGreater(report["samples_at_targets"]["title"], SR)
        alternate = audio.score_envelope(voice, timeline, speech_db=-16, pause_db=-10, title_db=-2)
        self.assertAlmostEqual(20 * np.log10(alternate[2 * SR]), -16, delta=.03)

    def test_previous_mixer_default_and_optional_envelope(self):
        voice = np.full((SR, 2), .1, dtype="float32")
        music = np.full((SR, 2), .2, dtype="float32")
        effects = np.zeros_like(voice)
        scalar = audio.mix_audio(voice, music, effects, -14, self.root, evidence=True)
        actual, _ = sf.read(scalar, dtype="float32", always_2d=True)
        expected = voice + music * audio.sidechain(voice, -14)[:, None]
        np.testing.assert_array_equal(actual, expected)
        audio.mix_audio(voice, music, effects, [(0, SR, -14)], self.root, evidence=False)
        chapter, _ = sf.read(scalar, dtype="float32", always_2d=True)
        np.testing.assert_array_equal(chapter, expected)
        gain = np.full(SR, .5, dtype="float32")
        audio.mix_audio(voice, music, effects, -14, self.root, evidence=True, gain_envelope=gain)
        explicit, _ = sf.read(scalar, dtype="float32", always_2d=True)
        np.testing.assert_allclose(explicit, .2, atol=1e-7)

    @unittest.skipUnless(shutil.which(os.getenv("FFMPEG", "ffmpeg")), "Full FFmpeg binary unavailable")
    def test_actual_supplied_mp3_decoding_and_coda(self):
        package = Path(os.getenv(
            "CHERNOBYL_PACKAGE_ROOT",
            Path(__file__).resolve().parents[2] / "chernobyl_1986_DGX_PACKAGE" / "chernobyl_1986",
        ))
        if not (package / "assets/music/main_score.mp3").is_file():
            self.skipTest("Supplied Chernobyl score package unavailable")
        timeline = [
            {"start_sample": 0, "end_sample": 2 * SR},
            {"scene_id": "coda", "start_sample": 2 * SR, "end_sample": 8 * SR,
             "music_transition": "assets/music/coda_score.mp3"},
        ]
        output, receipt = score.build(
            {"global_music_file": "assets/music/main_score.mp3"}, timeline, 8 * SR, package, self.root,
        )
        main = audio.read(package / "assets/music/main_score.mp3", self.root)
        coda = audio.read(package / "assets/music/coda_score.mp3", self.root)
        np.testing.assert_array_equal(output[:2 * SR], main[:2 * SR])
        ramp = np.linspace(0, 1, 4 * SR, dtype="float32")[:, None]
        expected = main[2 * SR:6 * SR] * (1 - ramp) + coda[:4 * SR] * ramp
        np.testing.assert_allclose(output[2 * SR:6 * SR], expected, atol=1e-7)
        np.testing.assert_array_equal(output[6 * SR:], coda[4 * SR:6 * SR])
        self.assertEqual(receipt["transitions"][0]["crossfade_seconds"], 4)
        self.assertEqual(len(output), 8 * SR)


if __name__ == "__main__":
    unittest.main()
