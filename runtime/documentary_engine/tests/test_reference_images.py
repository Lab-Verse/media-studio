import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from engine.media_fetcher import pinned_archival, pinned_illustration


class PinnedReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "assets" / "illustrations" / "reactor.png"
        self.source.parent.mkdir(parents=True)
        image = Image.new("RGB", (1000, 500), "white")
        drawing = ImageDraw.Draw(image)
        drawing.rectangle((0, 0, 99, 499), fill="red")
        drawing.rectangle((900, 0, 999, 499), fill="blue")
        image.save(self.source)
        self.record = {
            "path": self.source.relative_to(self.root).as_posix(),
            "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "provider": "original_illustration",
            "source_url": "project://chernobyl_1986/technical-figures",
            "title": "RBMK fuel and control channel schematic",
            "creator": "BorrowedTime Films",
            "license": "Project-created original artwork",
            "display_label": "EXPLANATORY SCHEMATIC — NOT TO SCALE",
            "notes": "Control and fuel channels shown separately",
        }
        self.destination = self.root / "fitted.png"

    def tearDown(self):
        self.temporary.cleanup()

    def test_original_illustration_fit_retains_edges_label_and_provenance(self):
        path, receipt = pinned_illustration(self.root, self.record, self.destination)
        self.assertEqual(path, self.destination)
        with Image.open(path) as fitted:
            self.assertEqual(fitted.size, (1920, 1080))
            # Whole-frame fitting retains both original coloured edges.
            self.assertEqual(fitted.getpixel((150, 540)), (255, 0, 0))
            self.assertEqual(fitted.getpixel((1770, 540)), (0, 0, 255))
            self.assertEqual(fitted.getpixel((5, 5)), (15, 17, 20))
        for field in ("provider", "source_url", "title", "creator", "license", "display_label", "notes"):
            self.assertEqual(receipt[field], self.record[field])
        self.assertEqual(receipt["original_sha256"], self.record["sha256"])
        self.assertTrue(receipt["modifications"].startswith("Original project-created explanatory graphic; fitted"))
        self.assertNotIn("photograph", receipt["modifications"])
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.record["sha256"])

    def test_checksum_and_original_provider_are_required(self):
        for change in ({"sha256": "0" * 64}, {"sha256": None}, {"provider": "ai_image"}, {"provider": "wikimedia_commons"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                pinned_illustration(self.root, {**self.record, **change}, self.destination)
        self.assertFalse(self.destination.exists())

    def test_all_provenance_fields_are_nonempty_strings(self):
        for field in ("source_url", "title", "creator", "license"):
            for empty in ("", "   ", None, 12):
                with self.subTest(field=field, value=empty), self.assertRaises(ValueError):
                    pinned_illustration(self.root, {**self.record, field: empty}, self.destination)
        self.assertFalse(self.destination.exists())

    def test_path_bucket_escape_unknown_directory_and_original_overwrite_rejected(self):
        archive = self.root / "assets" / "archival" / "copy.png"
        archive.parent.mkdir()
        archive.write_bytes(self.source.read_bytes())
        for reference in ("assets/illustrations/../archival/copy.png", "../outside.png"):
            with self.subTest(path=reference), self.assertRaises(ValueError):
                pinned_illustration(self.root, {**self.record, "path": reference}, self.destination)
        with self.assertRaises(ValueError):
            pinned_archival(self.root, self.record, self.destination, asset_directory="../illustrations")
        with self.assertRaises(ValueError):
            pinned_illustration(self.root, self.record, self.source)

    def test_archival_default_and_cc_sharealike_notice_remain_compatible(self):
        archive = self.root / "assets" / "archival" / "photo.png"
        archive.parent.mkdir()
        archive.write_bytes(self.source.read_bytes())
        record = {
            **self.record, "path": archive.relative_to(self.root).as_posix(),
            "provider": "wikimedia_commons", "license": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        }
        _, receipt = pinned_archival(self.root, record, self.destination)
        self.assertEqual(
            receipt["modifications"],
            "Fitted to a dark 16:9 frame, upscaled and animated with pan or zoom"
            "; adapted photograph retains CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)",
        )
        self.assertEqual(receipt["license_url"], record["license_url"])
        # The optional keyword takes the same validated illustration path.
        _, original = pinned_archival(
            self.root, self.record, self.destination, asset_directory="illustrations",
        )
        self.assertEqual(original["provider"], "original_illustration")


if __name__ == "__main__":
    unittest.main()
