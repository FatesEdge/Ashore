"""Check that rebuilding a release does not expose partial packages."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import make


class PackagingTests(unittest.TestCase):
    def test_onefile_rebuild_replaces_complete_package_only(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)
            previous = dist / 'Ashore.Linux.onefile'
            previous.mkdir()
            (previous / 'Ashore').write_text('old')

            def incomplete(command, **kwargs):
                (previous / 'Ashore').write_text('old')

            with patch.object(make, 'DIST', dist), patch.object(make.platform, 'system', return_value='Linux'):
                with patch.object(make.subprocess, 'run', side_effect=incomplete):
                    with self.assertRaisesRegex(ValueError, '未生成完整'):
                        make.build('onefile')
                self.assertEqual((previous / 'Ashore').read_text(), 'old')

                def completed(command, **kwargs):
                    destination = Path(command[command.index('--distpath') + 1])
                    (destination / 'Ashore').write_text('new')

                with patch.object(make.subprocess, 'run', side_effect=completed):
                    make.build('onefile')
                self.assertEqual((previous / 'Ashore').read_text(), 'new')
                self.assertTrue((previous / 'install.sh').is_file())
                self.assertTrue((previous / 'ashore.desktop').is_file())
                self.assertTrue((previous / 'icon.png').is_file())


if __name__ == '__main__':
    unittest.main()
