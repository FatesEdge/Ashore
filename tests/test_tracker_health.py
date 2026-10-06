import os
import unittest
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from core.trackerHealth import probeTracker
from interface.trackerManagerDialog import TrackerManagerDialog


class TrackerHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def test_unsupported_tracker_scheme_is_reported(self):
        ok, latency, error = probeTracker('ftp://tracker.example/announce')
        self.assertFalse(ok)
        self.assertIsNone(latency)
        self.assertIn('协议', error)

    def test_dialog_normalizes_and_deduplicates_trackers(self):
        dialog = TrackerManagerDialog([
            'udp://tracker.example:80/announce',
            'udp://tracker.example:80/announce',
            'https://tracker.example/announce',
        ])
        self.assertEqual(
            dialog.trackers(),
            [
                'udp://tracker.example:80/announce',
                'https://tracker.example/announce',
            ])
        dialog.close()

    def test_dialog_applies_health_result_without_network(self):
        dialog = TrackerManagerDialog(
            ['https://tracker.example/announce'], language='en')
        dialog.applyHealthResult(0, 'healthy', 42, '')
        self.assertEqual(dialog.table.item(0, 1).text(), 'Reachable')
        self.assertEqual(dialog.table.item(0, 2).text(), '42 ms')
        dialog.close()


if __name__ == '__main__':
    unittest.main()
