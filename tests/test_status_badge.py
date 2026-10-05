import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QLabel

from interface.statusBadge import setConnectionBadge


class StatusBadgeTests(unittest.TestCase):
    def test_state_badges_are_semantic_and_not_inline_colored(self):
        self.app = QApplication.instance() or QApplication([])
        label = QLabel()

        setConnectionBadge(label, 'Connected', 'connected')
        self.assertEqual(label.text(), '● Connected')
        connectedColor = label.palette().color(
            QPalette.ColorRole.WindowText)
        self.assertIsNone(label.property('connectionState'))
        self.assertEqual(label.styleSheet(), '')

        setConnectionBadge(label, 'Disconnected', 'disconnected')
        self.assertEqual(label.text(), '● Disconnected')
        disconnectedColor = label.palette().color(
            QPalette.ColorRole.WindowText)
        self.assertNotEqual(connectedColor, disconnectedColor)
        self.assertIsNone(label.property('connectionState'))


if __name__ == '__main__':
    unittest.main()
