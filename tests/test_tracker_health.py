import os
import unittest
from PyQt6.QtWidgets import QApplication

from core.trackerHealth import probeTracker
from interface.trackerManagerPanel import TrackerManagerPanel


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

    def test_panel_normalizes_and_deduplicates_trackers(self):
        panel = TrackerManagerPanel([
            'udp://tracker.example:80/announce',
            'udp://tracker.example:80/announce',
            'https://tracker.example/announce',
        ])
        self.assertEqual(
            panel.trackers(),
            [
                'udp://tracker.example:80/announce',
                'https://tracker.example/announce',
            ])
        panel.close()

    def test_panel_applies_health_result_without_network(self):
        panel = TrackerManagerPanel(
            ['https://tracker.example/announce'], language='en')
        panel.applyHealthResult(0, 'healthy', 42, '')
        self.assertEqual(panel.table.item(0, 1).text(), 'Reachable')
        self.assertEqual(panel.table.item(0, 2).text(), '42 ms')
        panel.close()


if __name__ == '__main__':
    unittest.main()
