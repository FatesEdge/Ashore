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

    def test_linux_installer_does_not_require_aria2_before_install(self):
        installer = (make.ROOT / 'packaging' / 'install.sh').read_text(
            encoding='utf-8')

        self.assertNotIn('command -v aria2c', installer)
        self.assertNotIn('Install aria2 first', installer)

    def test_linux_spec_excludes_unused_python_modules_and_native_plugins(self):
        spec = make.linuxSpecText('onefile')

        for module in (
                'numpy', 'cryptography', 'tkinter',
                'PyQt6.QtDBus', 'PyQt6.QtMultimedia',
                'PyQt6.QtQml', 'PyQt6.QtQuick',
                'PyQt6.QtWebEngineWidgets'):
            self.assertIn(repr(module), spec)

        for plugin in (
                'PyQt6/Qt6/lib/libQt6Pdf.so.6',
                'PyQt6/Qt6/plugins/imageformats/libqpdf.so',
                'PyQt6/Qt6/plugins/platforms/libqeglfs.so',
                'PyQt6/Qt6/plugins/platforms/libqvnc.so'):
            self.assertIn(repr(plugin), spec)
            self.assertFalse(make.linuxBundleEntryAllowed(plugin))

        for required in (
                'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
                'PyQt6.QtNetwork', 'PyQt6.QtSvg',
                'PyQt6.QtWebSockets'):
            self.assertNotIn(required, make.PYINSTALLER_EXCLUDES)

    def test_linux_native_filter_keeps_desktop_integrations(self):
        for required in (
                'PyQt6/Qt6/plugins/platforms/libqxcb.so',
                'PyQt6/Qt6/plugins/platforms/libqwayland.so',
                'PyQt6/Qt6/plugins/platformthemes/libqgtk3.so',
                'PyQt6/Qt6/plugins/platformthemes/libqxdgdesktopportal.so',
                'PyQt6/Qt6/plugins/platforminputcontexts/libibusplatforminputcontextplugin.so',
                'PyQt6/Qt6/plugins/imageformats/libqsvg.so',
                'PyQt6/Qt6/lib/libQt6Network.so.6',
                'PyQt6/Qt6/lib/libQt6WebSockets.so.6'):
            self.assertTrue(make.linuxBundleEntryAllowed(required))

    def test_linux_spec_preserves_onefile_and_onedir_shapes(self):
        onefile = make.linuxSpecText('onefile')
        onedir = make.linuxSpecText('onedir')

        self.assertNotIn('COLLECT(', onefile)
        self.assertIn('COLLECT(', onedir)
        self.assertIn('exclude_binaries=True', onedir)
        self.assertIn('strip=True', onefile)
        self.assertIn('strip=True', onedir)

    def test_directory_size_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / 'payload.bin'
            payload.write_bytes(b'x' * 4096)
            alias = root / 'alias.bin'
            alias.symlink_to(payload.name)

            size = make.directorySize(root)

            self.assertGreaterEqual(size, payload.stat().st_size)
            self.assertLess(size, payload.stat().st_size * 2)

    def test_macos_bundle_copy_preserves_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'Source.app'
            destination = root / 'Destination.app'
            resources = source / 'Contents' / 'Resources'
            frameworks = source / 'Contents' / 'Frameworks'
            resources.mkdir(parents=True)
            frameworks.mkdir(parents=True)
            target = resources / 'payload.dat'
            target.write_text('payload')
            linkPath = frameworks / 'payload.dat'
            linkPath.symlink_to(Path('../Resources/payload.dat'))

            make.copyMacAppBundle(source, destination)

            copiedLink = destination / 'Contents' / 'Frameworks' / 'payload.dat'
            self.assertTrue(copiedLink.is_symlink())
            self.assertEqual(
                copiedLink.readlink(), Path('../Resources/payload.dat'))

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

    def test_windows_onefile_command_and_package_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory)
            command = make.pyinstallerCommand(
                'Windows', 'onefile', staging)

        self.assertIn('--onefile', command)
        self.assertNotIn('--onedir', command)
        self.assertNotIn('--strip', command)

        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)

            def completed(command, **kwargs):
                destination = Path(command[command.index('--distpath') + 1])
                (destination / 'Ashore.exe').write_text('windows')

            with patch.object(make, 'DIST', dist), patch.object(
                    make.platform, 'system', return_value='Windows'):
                with patch.object(make.subprocess, 'run', side_effect=completed):
                    make.build('onefile')

            package = dist / 'Ashore.Windows.onefile'
            self.assertTrue((package / 'Ashore.exe').is_file())
            self.assertTrue((package / 'icon.png').is_file())


if __name__ == '__main__':
    unittest.main()
