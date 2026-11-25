"""Meaningful regression checks for the supplied runner's production fixes."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("comfy_pipeline", Path(__file__).with_name("comfy_pipeline.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def graph():
    return {
        "prompt": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": "old"}, "_meta": {"title": "SCENE PROMPT"}},
        "seed": {"class_type": "PrimitiveInt", "inputs": {"value": 1}, "_meta": {"title": "SEED"}},
        "negative": {"class_type": "CLIPTextEncode", "inputs": {"text": "no logos"}, "_meta": {"title": "Negative"}},
        "loader": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "old.safetensors"}},
        "final": {"class_type": "SaveImage", "inputs": {"filename_prefix": "old"}},
    }


class RunnerTests(unittest.TestCase):
    def test_prompt_seed_and_final_filename_injection_preserves_negative(self):
        original = graph()
        actual, output = runner.inject_workflow(original, "scene", 42, "pinned.safetensors", "owned_token")
        self.assertEqual(actual["prompt"]["inputs"]["value"], "scene")
        self.assertEqual(actual["negative"]["inputs"]["text"], "no logos")
        self.assertEqual(actual["seed"]["inputs"]["value"], 42)
        self.assertEqual(actual["final"]["inputs"]["filename_prefix"], "BorrowedTime/owned_token")
        self.assertEqual(original["prompt"]["inputs"]["value"], "old")
        self.assertEqual(output, "final")

    def test_intermediate_preview_is_never_selected(self):
        record = {"status": {"completed": True, "status_str": "success"}, "outputs": {
            "preview": {"images": [{"filename": "wrong.png", "type": "temp"}]},
            "final": {"images": [{"filename": "final.png", "type": "output"}]},
        }}
        self.assertEqual(runner.ComfyClient.final_image(record, "final")["filename"], "final.png")

    def test_failed_history_does_not_return_old_output(self):
        record = {"status": {"completed": False, "status_str": "error"},
                  "outputs": {"final": {"images": [{"filename": "stale.png"}]}}}
        with self.assertRaisesRegex(RuntimeError, "generation failed"):
            runner.ComfyClient.final_image(record, "final")

    def test_resume_retains_existing_prompt_id_without_post(self):
        class Client(runner.ComfyClient):
            def request(self, route, payload=None):
                self_case.assertIsNone(payload, "A saved queued prompt must not be submitted again")
                self_case.assertEqual(route, "/history/existing-id")
                return {"existing-id": {"status": {"completed": False, "status_str": "error"}}}
        self_case = self
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "image.png"
            runner.atomic_json(out.with_suffix(".job.json"), {"cache_key": "k", "prompt_id": "existing-id", "state": "queued", "attempt": 1})
            with self.assertRaisesRegex(RuntimeError, "generation failed"):
                Client("http://unused").image(graph(), "scene", out, "k", 1, "ckpt")
            self.assertEqual(runner.load(out.with_suffix(".job.json"))["state"], "failed")

    def test_unknown_submission_refuses_duplicate_when_not_reconciled(self):
        class Client(runner.ComfyClient):
            def request(self, route, payload=None):
                self_case.assertIsNone(payload, "An unknown prior POST must never be blindly repeated")
                return {"queue_running": [], "queue_pending": []} if route == "/queue" else {}
        self_case = self
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "image.png"
            runner.atomic_json(out.with_suffix(".job.json"), {"cache_key": "k", "state": "unknown", "attempt": 1})
            with self.assertRaisesRegex(RuntimeError, "Refusing duplicate"):
                Client("http://unused").image(graph(), "scene", out, "k", 1, "ckpt")

    def test_cache_requires_matching_contract_and_current_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "audio.wav"
            out.write_bytes(b"first take")
            receipt = out.with_suffix(".json")
            runner.atomic_json(receipt, {"cache_key": "voice-v1", "sha256": runner.digest(out)})
            self.assertTrue(runner.cache_valid(out, receipt, "voice-v1"))
            self.assertFalse(runner.cache_valid(out, receipt, "voice-v2"))
            out.write_bytes(b"corrupted take")
            self.assertFalse(runner.cache_valid(out, receipt, "voice-v1"))

    def test_changed_manifest_cannot_be_attested_as_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text('{"script":"first"}')
            args = argparse.Namespace(_manifest_sha=runner.digest(path), _source_map_sha=None)
            runner.assert_frozen_inputs(path, args)
            path.write_text('{"script":"different"}')
            with self.assertRaisesRegex(ValueError, "Manifest changed"):
                runner.assert_frozen_inputs(path, args)

    def test_changed_source_map_cannot_be_attested_as_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text('{}')
            args = argparse.Namespace(_manifest_sha=runner.digest(path), _source_map_sha=None)
            (path.parent / "assets").mkdir()
            (path.parent / "assets/source-map.json").write_text('{}')
            with self.assertRaisesRegex(ValueError, "Source map changed"):
                runner.assert_frozen_inputs(path, args)

    def test_script_correction_does_not_invent_extra_time(self):
        measured = [{"start": i*.2, "end": (i+1)*.2, "word": word}
                    for i, word in enumerate("In nineteen ninety two men arrived".split())]
        text = "In nineteen ninety, two men in police uniforms arrived."
        cues = runner.script_cues(text, measured)
        self.assertEqual(" ".join(c[2] for c in cues), text)
        self.assertGreaterEqual(cues[0][0], measured[0]["start"])
        self.assertLessEqual(cues[-1][1], measured[-1]["end"])

    def test_source_path_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                runner.local_file(Path(folder), "../private.txt")
            with self.assertRaises(ValueError):
                runner.local_file(Path(folder), "C:/private.txt")


if __name__ == "__main__":
    unittest.main()
