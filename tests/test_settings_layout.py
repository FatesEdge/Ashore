import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QSizePolicy

import paths
from Ashore import StartupController
from interface.settingPage import SettingPage
from interface.themeManager import ACCENT_PRESETS, THEME_MODES, ThemeManager


class SettingsLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def makePage(self, folder):
        root = Path(folder)
        patches = (
            patch.object(paths, 'CONFIG_DIR', root),
            patch.object(SettingPage, 'ashoreConfDir', folder),
            patch.object(SettingPage, 'aria2ConfPath', str(root / 'aria2.conf')),
        )
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        return SettingPage()

    def test_long_text_fields_expand_while_compact_controls_do_not(self):
        with tempfile.TemporaryDirectory() as folder:
            page = self.makePage(folder)
            self.assertTrue(page.scrollArea.widgetResizable())
            for field in (page.pathLineEdit, page.userAgentComboBox,
                          page.rpcSecretLineEdit, page.btTracker):
                self.assertEqual(field.sizePolicy().horizontalPolicy(),
                                 QSizePolicy.Policy.Expanding)
            self.assertLess(page.rpcPortLineEdit.maximumWidth(), 1000)

    def test_token_mask_has_fixed_length_and_reveals_real_value(self):
        with tempfile.TemporaryDirectory() as folder:
            page = self.makePage(folder)
            page.rpcListenAllComboBox.setCurrentIndex(0)
            token = page.rpcSecret
            self.assertEqual(page.rpcSecretLineEdit.text(), '●' * 12)
            page.toggleToken()
            self.assertEqual(page.rpcSecretLineEdit.text(), token)

    def test_theme_and_tracker_controls_have_persistable_values(self):
        with tempfile.TemporaryDirectory() as folder:
            page = self.makePage(folder)
            self.assertEqual(
                {page.themeModeComboBox.itemData(index)
                 for index in range(page.themeModeComboBox.count())},
                set(THEME_MODES))
            self.assertIn(page.accentComboBox.currentText(), ACCENT_PRESETS)
            self.assertEqual(page.getBoolOption(page.autoTrackerComboBox), 'true')
            self.assertEqual(StartupController.TRACKER_GRACE_MS, 1000)

    def test_theme_manager_applies_each_mode(self):
        manager = ThemeManager(self.app)
        for mode in THEME_MODES:
            manager.apply(mode, '#3f7cac')
            self.assertEqual(manager.mode, mode)
            self.assertEqual(manager.accent, '#3f7cac')


if __name__ == '__main__':
    unittest.main()
