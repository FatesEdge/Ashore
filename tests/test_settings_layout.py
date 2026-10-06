import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QFormLayout, QSizePolicy

import paths
from Ashore import StartupController
from interface.addNewDialog import AddNewDialog
from interface.controls import AshoreComboBox, AshoreSpinBox
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

    def test_settings_use_ashore_combo_and_spin_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            page = self.makePage(folder)
            self.assertIsInstance(page.languageComboBox, AshoreComboBox)
            self.assertIsInstance(page.updateIntervalSpin, AshoreSpinBox)
            self.assertTrue(
                page.defaultDownloadDirLabel.property('settingsFormLabel'))

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
        self.assertIn('QPushButton[navigationTab="true"]:hover', style)
        self.assertIn('QLabel[statusMetricText="true"]', style)
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
        self.assertTrue(section.actionButton.isHidden())
        self.assertTrue(section.openFolderButton.isHidden())
        section.setQuickActionsVisible(True)
        self.assertEqual(section.actionButton.iconSize().width(), 18)
        self.assertEqual(section.actionSlot.height(), 22)
        self.assertFalse(section.actionButton.isHidden())
        self.assertFalse(section.openFolderButton.isHidden())
        self.assertFalse(section.copyUrlButton.isHidden())
        self.assertFalse(section.moreButton.isHidden())
        self.assertEqual(section.deleteAction.text(), '删除任务和文件…')
        self.assertEqual(section.overflowMenu.dismissTimer.interval(), 450)
        self.assertEqual(section.height(), 84)
        self.assertEqual(section.CONTENT_MIN_WIDTH, 660)
        self.assertEqual(section.CONTENT_MAX_WIDTH, 820)
        self.assertEqual(
            section.actionSlot.layout().contentsMargins().left(), 30)
        layout = section.rateLabel.parentWidget().layout()
        namePosition = layout.getItemPosition(layout.indexOf(section.nameLabel))
        ratePosition = layout.getItemPosition(layout.indexOf(section.rateLabel))
        self.assertEqual(namePosition[:2], (0, 0))
        self.assertEqual(ratePosition[:2], (1, 1))

    def test_completed_multifile_task_opens_folder_as_primary_action(self):
        multi = Section(
            'gid', 'Example', 'completed', 100, 100, 0,
            isTorrent=True, files=['a.bin', 'b.bin'])
        single = Section(
            'gid2', 'single.iso', 'completed', 100, 100, 0,
            files=['single.iso'])
        self.assertEqual(multi.primaryActionKind(), 'open-folder')
        self.assertEqual(single.primaryActionKind(), 'open-file')

    def test_settings_retranslate_without_recreating_page(self):
        with tempfile.TemporaryDirectory() as folder:
            page = self.makePage(folder)
            page.setLanguage('en')
            self.assertEqual(
                page.defaultDownloadDirLabel.text(),
                'Default download directory:')
            self.assertEqual(page.saveBtn.text(), 'Save Settings')
            self.assertEqual(page.rpcListenAllComboBox.itemText(0), 'Yes')
            self.assertEqual(page.themeModeComboBox.itemText(2), 'Dark')
            self.assertTrue(page.defaultDownloadDirLabel.wordWrap())
            self.assertEqual(
                page.formLayout.rowWrapPolicy(),
                QFormLayout.RowWrapPolicy.WrapAllRows)
            self.assertEqual(
                page.formLayout.labelAlignment(),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.assertEqual(
                page.showAria2StatusLabel.text(),
                'Show aria2 status in main window:')

    def test_overflow_menu_only_contains_non_quick_actions(self):
        section = Section(
            'gid-menu', 'file.bin', 'paused', 100, 50, 0,
            files=['file.bin'])
        overflow = [
            action for action in section.overflowMenu.actions()
            if not action.isSeparator()]
        self.assertEqual(
            overflow, [section.removeAction, section.deleteAction])

        section.prepareContextMenu()
        context = [
            action for action in section.contextMenu.actions()
            if not action.isSeparator()]
        self.assertEqual(
            context,
            [
                section.primaryAction,
                section.openFolderAction,
                section.copyUrlAction,
                section.removeAction,
                section.deleteAction,
            ])

    def test_multifile_context_menu_does_not_duplicate_open_folder(self):
        section = Section(
            'gid-multi', 'bundle', 'completed', 100, 100, 0,
            isTorrent=True, files=['a.bin', 'b.bin'])
        section.prepareContextMenu()
        actions = [
            action for action in section.contextMenu.actions()
            if not action.isSeparator()]
        self.assertEqual(actions.count(section.openFolderAction), 0)
        self.assertEqual(section.primaryActionKind(), 'open-folder')


    def test_show_aria2_status_is_a_persistable_boolean_setting(self):
        with tempfile.TemporaryDirectory() as folder:
            page = self.makePage(folder)
            self.assertIn('show_aria2_status', page.ashoreKeys)
            self.assertEqual(
                page.getBoolOption(page.showAria2StatusComboBox), 'true')
            page.setBoolOption(page.showAria2StatusComboBox, False)
            self.assertEqual(
                page.getBoolOption(page.showAria2StatusComboBox), 'false')

    def test_theme_styles_combo_spin_controls_and_accent_arrows(self):
        manager = ThemeManager(self.app)
        manager.apply('dark', '#a51d2d')
        style = self.app.styleSheet()
        self.assertIn('QComboBox::down-arrow', style)
        self.assertIn('QSpinBox::up-arrow', style)
        self.assertIn('QSpinBox::down-arrow', style)
        self.assertNotIn('QLabel[connectionState="connected"]', style)
        self.assertIn('QLabel[mainConnectionDot="true"]', style)
        self.assertIn('QSpinBox {', style)
        self.assertIn('QComboBox, QSpinBox {', style)
        self.assertNotIn('background-color: #2e7d32', style)

    def test_new_download_advanced_control_uses_ashore_chevron(self):
        dialog = AddNewDialog('/tmp', language='en')
        self.assertEqual(
            dialog.advancedToggle.arrowType(),
            Qt.ArrowType.NoArrow)
        self.assertFalse(dialog.advancedToggle.icon().isNull())
        dialog.advancedToggle.setChecked(True)
        self.assertFalse(dialog.advancedToggle.icon().isNull())
        self.assertGreaterEqual(dialog.headersEdit.minimumHeight(), 64)
        dialog.close()


    def test_chinese_settings_labels_remain_single_line(self):
        with tempfile.TemporaryDirectory() as folder:
            page = self.makePage(folder)
            page.setLanguage('zh_CN')
            self.assertTrue(page.defaultDownloadDirLabel.wordWrap())
            self.assertEqual(
                page.formLayout.rowWrapPolicy(),
                QFormLayout.RowWrapPolicy.WrapAllRows)
            self.assertEqual(
                page.formLayout.labelAlignment(),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.assertFalse(page.showAria2StatusLabel.wordWrap())



if __name__ == '__main__':
    unittest.main()
