import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QSizePolicy

import paths
from Ashore import StartupController
from interface.section import Section
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

    def test_light_and_dark_palettes_are_visibly_distinct(self):
        manager = ThemeManager(self.app)
        manager.apply('light', '#3f7cac')
        light = self.app.palette().color(QPalette.ColorRole.Window)
        manager.apply('dark', '#3f7cac')
        dark = self.app.palette().color(QPalette.ColorRole.Window)
        self.assertGreater(light.lightness(), 220)
        self.assertLess(dark.lightness(), 80)

    def test_semantic_styles_cover_command_navigation_cards_and_scrollbars(self):
        manager = ThemeManager(self.app)
        manager.apply('dark', '#3f7cac')
        style = self.app.styleSheet()
        self.assertIn('QPushButton[commandPrimary="true"]', style)
        self.assertIn('QPushButton[navigationTab="true"]:checked', style)
        self.assertIn('QFrame[downloadCard="true"]', style)
        self.assertIn('QScrollBar:vertical', style)

    def test_tracker_and_download_progress_use_dense_row_card_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            page = self.makePage(folder)
            self.assertGreaterEqual(page.btTracker.minimumHeight(), 120)
            self.assertTrue(page.saveBtn.property('primaryAction'))
        section = Section('gid', 'example.bin', 'completed', 100, 100, 0)
        self.assertEqual(section.progressBar.height(), 4)
        self.assertFalse(section.progressBar.isTextVisible())
        self.assertEqual(section.rateLabel.text(), '100%')
        self.assertEqual(section.progressBar.value(), 100)
        self.assertEqual(section.property('downloadCard'), True)


if __name__ == '__main__':
    unittest.main()
