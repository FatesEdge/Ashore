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
                    with self.assertRaisesRegex(ValueError, 'complete Ashore Linux package'):
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


    def test_pyinstaller_command_excludes_unused_heavy_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory)
            command = make.pyinstallerCommand('Linux', 'onefile', staging)

        self.assertIn('--strip', command)
        for module in (
                'numpy', 'cryptography', 'tkinter',
                'PyQt6.QtDBus', 'PyQt6.QtMultimedia',
                'PyQt6.QtQml', 'PyQt6.QtQuick',
                'PyQt6.QtWebEngineWidgets'):
            pairFound = any(
                command[index:index + 2] == ['--exclude-module', module]
                for index in range(len(command) - 1))
            self.assertTrue(pairFound, module)

        for required in (
                'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
                'PyQt6.QtNetwork', 'PyQt6.QtSvg',
                'PyQt6.QtWebSockets'):
            self.assertNotIn(required, make.PYINSTALLER_EXCLUDES)

    def test_macos_bundle_identifier_matches_repository_identity(self):
        import plistlib

        plist = make.ROOT / 'packaging' / 'Info.plist'
        with plist.open('rb') as file:
            info = plistlib.load(file)

        self.assertEqual(
            info['CFBundleIdentifier'],
            'io.github.kai-x64.ashore')

    def test_non_linux_build_does_not_request_binary_stripping(self):
        with tempfile.TemporaryDirectory() as directory:
            command = make.pyinstallerCommand(
                'Darwin', 'app', Path(directory))
        self.assertNotIn('--strip', command)


if __name__ == '__main__':
    unittest.main()
