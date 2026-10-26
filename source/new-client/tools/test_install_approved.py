"""Transaction, integrity, path confinement and rollback checks; no game/server needed."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib
import install_approved as installer

class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.project = root / 'project'
        self.project.mkdir()
        (self.project / 'project.godot').write_text('config_version=5')
        for zone in (207, 209):
            target = self.project / f'content/zones/zone{zone}/zone.json'
            target.parent.mkdir(parents=True)
            target.write_text('{}')
        self.package = root / 'package'
        (self.package / 'blobs').mkdir(parents=True)
        data = b'approved image bytes'
        self.row = {'path': '.enhanced-session/test/art.png', 'size': len(data),
                    'sha256': installer.digest(data), 'parts': ['one.z']}
        (self.package / 'blobs/one.z').write_bytes(zlib.compress(data))
        (self.package / 'manifest.json').write_text(json.dumps(
            {'schema': 1, 'id': 'test', 'files': [self.row]}))

    def run_mode(self, mode):
        with patch.object(installer, 'PACKAGE', self.package), patch('sys.argv',
                ['install', '--project', str(self.project), mode]), contextlib.redirect_stdout(io.StringIO()):
            installer.main()

    def test_install_verify_idempotent_rollback(self):
        self.run_mode('--apply')
        self.run_mode('--verify')
        self.run_mode('--apply')
        self.run_mode('--rollback')
        self.assertFalse((self.project / self.row['path']).exists())
        self.assertEqual((self.project / 'content/zones/zone207/zone.json').read_text(), '{}')

    def test_preview_writes_nothing(self):
        with patch.object(installer, 'PACKAGE', self.package), patch('sys.argv',
                ['install', '--project', str(self.project)]), contextlib.redirect_stdout(io.StringIO()):
            installer.main()
        self.assertFalse((self.project / '.enhanced-session').exists())

    def test_collision_preserves_existing(self):
        target = self.project / self.row['path']
        target.parent.mkdir(parents=True)
        target.write_bytes(b'local later work')
        with self.assertRaises(SystemExit): self.run_mode('--apply')
        self.assertEqual(target.read_bytes(), b'local later work')
        self.assertFalse((self.project / installer.MARKER).exists())

    def test_corrupt_blob_does_not_activate(self):
        (self.package / 'blobs/one.z').write_bytes(zlib.compress(b'corrupt'))
        with self.assertRaises(SystemExit): self.run_mode('--apply')
        self.assertFalse((self.project / self.row['path']).exists())
        self.assertFalse((self.project / installer.MARKER).exists())

    def test_rollback_refuses_later_changes(self):
        self.run_mode('--apply')
        (self.project / self.row['path']).write_bytes(b'later work')
        with self.assertRaises(SystemExit): self.run_mode('--rollback')
        self.assertTrue((self.project / installer.MARKER).exists())

    def test_paths_cannot_escape_or_touch_stock(self):
        for path in ['../outside', '/absolute', '.enhanced-session/../../outside', 'content/stock.png']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                installer.destination(self.project, path)

if __name__ == '__main__': unittest.main()
