import os
import unittest

from PyQt6.QtWidgets import QApplication

from interface.actionIcons import ACTION_NAMES, actionIcon


class ActionIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def test_all_standard_action_icons_render(self):
        for name in ACTION_NAMES:
            with self.subTest(name=name):
                self.assertFalse(actionIcon(name).isNull())


if __name__ == '__main__':
    unittest.main()
