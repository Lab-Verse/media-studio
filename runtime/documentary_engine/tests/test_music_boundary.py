"""An imported score cannot read outside the selected production package."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'tools/render_short.py'
SPEC = importlib.util.spec_from_file_location('short_music_boundary', MODULE)
short = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(short)


class MusicBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.outside = Path(self.temp.name) / 'private.wav'
        self.outside.write_bytes(b'private')
        self.project = Path(self.temp.name) / 'project'
        (self.project / 'assets').mkdir(parents=True)
        (self.project / 'assets/score.wav').write_bytes(b'approved')

    def test_in_project_score_is_accepted(self):
        self.assertEqual(short.supplied_music(self.project, 'assets/score.wav'),
                         (self.project / 'assets/score.wav').resolve())

    def test_absolute_drive_traversal_and_invalid_values_are_rejected(self):
        for value in [str(self.outside), '../private.wav', 'assets/../../private.wav',
                      'C:/private.wav', 'C:private.wav', '\\\\host\\share.wav', '', None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                short.supplied_music(self.project, value)

    def test_symlink_escape_is_rejected(self):
        link = self.project / 'assets/link.wav'
        try:
            link.symlink_to(self.outside)
        except OSError:
            self.skipTest('Host does not permit creating symlinks')
        with self.assertRaises(ValueError):
            short.supplied_music(self.project, 'assets/link.wav')


if __name__ == '__main__':
    unittest.main()
