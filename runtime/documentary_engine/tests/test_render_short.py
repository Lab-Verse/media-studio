"""Contract tests for the Shorts runner's production failure boundaries."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "tools/render_short.py"
spec = importlib.util.spec_from_file_location("render_short", MODULE)
short = importlib.util.module_from_spec(spec)
spec.loader.exec_module(short)


def template():
    mapping = {"node_prompt_inject": "p", "node_seed_inject": "s", "node_motion_prompt": "motion%22id", "node_save_still": "still", "node_save_video": "video"}
    types = ["PrimitiveStringMultiline", "PrimitiveInt", "CLIPTextEncode", "SaveImage", "SaveVideo"]
    graph = {key: {"class_type": typ, "inputs": {}} for key, typ in zip(mapping.values(), types)}
    return graph, mapping


class ProductionContracts(unittest.TestCase):
    def test_literal_quote_mapping_does_not_silently_keep_wrong_motion(self):
        graph, mapping = template()
        mapping["node_motion_prompt"] = 'motion"id'
        with self.assertRaisesRegex(ValueError, "percent escapes"):
            short.validate_graph(graph, mapping)

    def test_missing_model_is_fatal_before_submission(self):
        graph, mapping = template()
        graph["model"] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "missing.safetensors"}}
        schemas = {n["class_type"]: {"input": {"required": {}}} for n in graph.values()}
        schemas["CheckpointLoaderSimple"] = {"input": {"required": {"ckpt_name": [["installed.safetensors"], {}]}}}
        with self.assertRaisesRegex(ValueError, "Unavailable model"):
            short.validate_graph(graph, mapping, schemas)

    def test_cache_changes_with_voice_script_prompt_seed_or_workflow(self):
        scene = {"narration": "A ship burned.", "still_prompt": "Ship", "motion_prompt": "Fire", "seed": 1}
        meta = {"default_voice": "bm_george"}
        graph, _ = template()
        original = short.scene_signature(scene, meta, graph)
        for key in scene:
            changed = dict(scene, **{key: 2 if key == "seed" else "changed"})
            self.assertNotEqual(original, short.scene_signature(changed, meta, graph))
        self.assertNotEqual(original, short.scene_signature(scene, {"default_voice": "am_adam"}, graph))
        self.assertNotEqual(original, short.scene_signature(scene, meta, dict(graph, extra={})))

    def test_retime_uses_measured_duration_and_pads_full_target(self):
        self.assertIn("setpts=1.250000000000", short.retime_filter(4.8, 6.0))
        with patch.object(short, "probe", side_effect=[{"streams": [{"codec_type": "video", "duration": "4.8"}], "format": {"duration": "4.8"}}, {"streams": [{"codec_type": "video", "duration": "6"}, {"codec_type": "audio", "duration": "6"}], "format": {"duration": "6"}}]), patch.object(short, "command") as command:
            short.retime_scene("video.mp4", "voice.wav", 6, "retimed.mkv")
            args = command.call_args.args[0]
            self.assertNotIn("-shortest", args)
            self.assertIn("apad,atrim=duration=6.000000000", args[args.index("-filter_complex") + 1])

    def test_submission_response_loss_is_not_retried(self):
        graph, mapping = template()
        scene = {"scene_id": "shot", "still_prompt": "New", "motion_prompt": "Moves", "seed": 42}
        meta = {"short_id": "short_01"}
        class Client:
            submits = 0
            def submit(self, graph, token):
                self.submits += 1
                raise TimeoutError("response lost")
            def reconcile(self, token):
                raise RuntimeError("No definitive job; operator reconciliation required")
        client = Client()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            with self.assertRaises(TimeoutError):
                short.get_video(client, scene, meta, graph, mapping, directory, "signature", None)
            self.assertEqual(short.read_json(directory / "comfy-job.json")["state"], "submitting")
            with self.assertRaisesRegex(RuntimeError, "operator reconciliation"):
                short.get_video(client, scene, meta, graph, mapping, directory, "signature", None)
            self.assertEqual(client.submits, 1)

    def test_error_status_beats_completed_flag(self):
        client = short.ComfyClient()
        with patch.object(client, "get", return_value={"owned": {"status": {"completed": True, "status_str": "error", "messages": []}}}):
            with self.assertRaisesRegex(RuntimeError, "job failed"):
                client.wait("owned")

    def test_subtitles_do_not_extend_over_silence_and_contain_safe_zones(self):
        timeline = [{"start": 0, "duration": 6, "scene": {"emphasis_words": ["FIRE"]}, "audio": {"words": [{"word": "A", "start": 0.2, "end": 0.4}, {"word": "ship", "start": 0.4, "end": 0.8}, {"word": "burned.", "start": 0.8, "end": 1.2}]}}]
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "captions.ass"
            events = short.write_captions({}, timeline, output)
            text = output.read_text()
            self.assertEqual(events[0]["end"], 1.2)
            self.assertIn("60,110,250", text)
            self.assertIn("AI RECONSTRUCTION", text)
            self.assertIn("0:00:03.40", text)
            self.assertIn("00:00:01,200", output.with_suffix(".srt").read_text())

    def test_time_rounding_carries_to_next_minute(self):
        self.assertEqual(short.ass_time(59.999), "0:01:00.00")
        self.assertEqual(short.srt_time(59.9999), "00:01:00,000")

    def test_script_spelling_survives_kokoro_punctuation_and_hyphen_tokens(self):
        tokens = [{"word": "Mont", "start": 0.1, "end": 0.4}, {"word": "Blanc", "start": 0.4, "end": 0.8}, {"word": "burned", "start": 1, "end": 1.5}]
        words, method = short.script_word_timings("Mont-Blanc burned.", tokens, 0.05, 1.6)
        self.assertEqual([x["word"] for x in words], ["Mont-Blanc", "burned."])
        self.assertEqual((words[0]["start"], words[0]["end"]), (0.1, 0.8))
        self.assertEqual(method, "proofread_script_projected_to_kokoro_token_timestamps")

    def test_numeric_spoken_form_never_replaces_proofread_caption_text(self):
        tokens = [{"word": "nine", "start": 0.1, "end": 0.4}, {"word": "oh", "start": 0.4, "end": 0.7}, {"word": "four", "start": 0.7, "end": 1.1}]
        words, method = short.script_word_timings("9:04.", tokens, 0.1, 1.1)
        self.assertEqual(words[0]["word"], "9:04.")
        self.assertIn("estimate_requires_listening_review", method)

    def test_symbolic_scene_label_overrides_global_label(self):
        timeline = [{"start": 0, "duration": 6, "scene": {}, "audio": {"words": []}}, {"start": 6, "duration": 5, "scene": {"reconstruction_overlay": {"text": "SYMBOLIC AI RECONSTRUCTION"}}, "audio": {"words": []}}]
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "captions.ass"
            short.write_captions({"reconstruction_overlay": {"text": "AI RECONSTRUCTION"}}, timeline, output)
            labels = [line for line in output.read_text().splitlines() if line.startswith("Dialogue: 0,")]
            self.assertIn("0:00:00.00,0:00:06.00", labels[0])
            self.assertTrue(labels[0].endswith(",,AI RECONSTRUCTION"))
            self.assertIn("0:00:06.00,0:00:11.00", labels[1])
            self.assertTrue(labels[1].endswith(",,SYMBOLIC AI RECONSTRUCTION"))

    def test_scene_override_map_labels_only_the_selected_symbolic_scene(self):
        # Self-contained contract fixture; private episode inputs are not distributed.
        manifest = {
            "reconstruction_overlay": {"text": "AI RECONSTRUCTION", "scene_overrides": {
                "scene08_shattered_watch": "SYMBOLIC AI RECONSTRUCTION"}},
            "scenes": [{"scene_id": identifier, "target_duration": 6}
                       for identifier in ("scene01_opening", "scene08_shattered_watch", "scene09_close")],
        }
        timeline, current = [], 0.0
        for scene in manifest["scenes"]:
            timeline.append({"start": current, "duration": scene["target_duration"], "scene": scene, "audio": {"words": []}})
            current += scene["target_duration"]
        self.assertEqual(manifest["reconstruction_overlay"]["scene_overrides"]["scene08_shattered_watch"], "SYMBOLIC AI RECONSTRUCTION")
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "captions.ass"
            short.write_captions(manifest, timeline, output)
            labels = [line for line in output.read_text().splitlines() if line.startswith("Dialogue: 0,")]
            self.assertEqual(len(labels), len(manifest["scenes"]))
            for timing, label in zip(timeline, labels):
                expected = "SYMBOLIC AI RECONSTRUCTION" if timing["scene"]["scene_id"] == "scene08_shattered_watch" else "AI RECONSTRUCTION"
                self.assertTrue(label.endswith(",," + expected))
                self.assertIn(f",{short.ass_time(timing['start'])},{short.ass_time(timing['start'] + timing['duration'])},Label,", label)

    def test_one_scene_proof_does_not_assemble_or_claim_eight_scenes_complete(self):
        graph, mapping = template()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shorts = root / "shorts"
            shorts.mkdir()
            music = root / "assets/music/main_score.mp3"
            music.parent.mkdir(parents=True)
            music.write_bytes(b"test-fixture-only")
            scenes = [{"scene_id": f"scene_{i}", "narration": "A ship burned.", "still_prompt": "Ship", "motion_prompt": "Fire", "seed": i, "target_duration": 6} for i in range(8)]
            manifest = {"project_metadata": {"project_id": "halifax", "short_id": "short_01", "default_voice": "bm_george"}, "workflow_mapping": mapping, "scenes": scenes}
            short.write_json(shorts / "manifest.json", manifest)
            short.write_json(root / "workflow.json", graph)
            args = SimpleNamespace(manifest=shorts / "manifest.json", workflow=root / "workflow.json", comfy_url="http://fixture.invalid", audio_only=False, assemble_only=False, visuals_only=False, preflight=False, scene_limit=1)
            audio = {"duration": 5, "speed": 1, "words": [{"word": "A ship burned.", "start": 0, "end": 5}], "caption_timing_method": "fixture"}
            schemas = {n["class_type"]: {"input": {"required": {}}} for n in graph.values()}
            with patch.object(short, "ComfyClient") as client, patch.object(short, "synthesize", return_value=audio), patch.object(short, "get_video", return_value=(root / "fixture.mp4", {"state": "complete"})) as render, patch.object(short, "retime_scene"), patch.object(short, "assemble") as assemble:
                client.return_value.get.side_effect = [{}, schemas]
                short.run(args)
                assemble.assert_not_called()
                self.assertEqual(render.call_count, 1)
            receipt = short.read_json(root / "output/halifax_SHORT_timeline.json")
            self.assertEqual(receipt["status"], "visuals_partial")
            self.assertEqual(receipt["completed_visual_count"], 1)
            self.assertEqual(receipt["scene_count"], 8)
            self.assertNotIn("master", receipt)

    def test_resume_retains_only_matching_scene_visual_receipts(self):
        timeline = [{"scene": {"scene_id": "one"}, "signature": "same"}, {"scene": {"scene_id": "two"}, "signature": "new"}]
        previous = {"timeline": [{"scene": {"scene_id": "one"}, "signature": "same", "comfy": {"state": "complete", "prompt_id": "owned"}, "retimed": "one.mkv"}, {"scene": {"scene_id": "two"}, "signature": "old", "comfy": {"state": "complete"}}]}
        self.assertEqual(short.retained_visual_progress(timeline, previous), 1)
        self.assertEqual(timeline[0]["comfy"]["prompt_id"], "owned")
        self.assertNotIn("comfy", timeline[1])

    def test_subthreshold_audio_fails_clearly_without_empty_index_error(self):
        import numpy as np
        scene = {"narration": "A ship burned.", "target_duration": 6}
        audio = np.full(2400, 0.002, dtype=np.float32)
        with tempfile.TemporaryDirectory() as d, patch.object(short, "kokoro_pipeline", return_value=lambda *a, **k: [("", "", audio)]):
            with self.assertRaisesRegex(RuntimeError, "below the activity threshold"):
                short.synthesize(scene, "bm_george", Path(d))
            self.assertFalse((Path(d) / "voice.wav").exists())


if __name__ == "__main__":
    unittest.main()
