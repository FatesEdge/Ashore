import configparser
import unittest
from pathlib import Path


class DesktopTests(unittest.TestCase):
    def test_magnet_and_torrent_open_as_arguments(self):
        desktop = Path(__file__).resolve().parents[1] / 'packaging/ashore.desktop'
        config = configparser.ConfigParser(interpolation=None)
        config.read(desktop, encoding='utf-8')
        entry = config['Desktop Entry']
        self.assertIn('%U', entry['Exec'])
        self.assertIn('x-scheme-handler/magnet;', entry['MimeType'])
        self.assertIn('x-scheme-handler/ashore;', entry['MimeType'])
        self.assertNotIn('x-scheme-handler/http;', entry['MimeType'])
        self.assertNotIn('x-scheme-handler/https;', entry['MimeType'])
        self.assertIn('application/x-bittorrent;', entry['MimeType'])

    def test_desktop_does_not_leave_startup_cursor_spinning(self):
        desktop = Path(__file__).resolve().parents[1] / 'packaging/ashore.desktop'
        config = configparser.ConfigParser(interpolation=None)
        config.read(desktop, encoding='utf-8')
        self.assertEqual(config['Desktop Entry']['StartupNotify'], 'false')
        self.assertEqual(config['Desktop Entry']['StartupWMClass'], 'Ashore')
        self.assertEqual(config['Desktop Entry']['X-GNOME-UsesNotifications'], 'true')


if __name__ == '__main__':
    unittest.main()
