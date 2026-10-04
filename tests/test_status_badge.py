import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtWidgets import QApplication, QLabel

from interface.statusBadge import (
    CONNECTED_COLOR,
    DISCONNECTED_COLOR,
    setConnectionBadge,
)


class StatusBadgeTests(unittest.TestCase):
    def test_connected_and_disconnected_colors(self):
        self.app = QApplication.instance() or QApplication([])
        label = QLabel()
        setConnectionBadge(label, '已连接', True)
        self.assertEqual(label.text(), '已连接')
        self.assertIn(CONNECTED_COLOR, label.styleSheet())
        self.assertIn('color: white', label.styleSheet())
        setConnectionBadge(label, '未连接', False)
        self.assertIn(DISCONNECTED_COLOR, label.styleSheet())


if __name__ == '__main__':
    unittest.main()
