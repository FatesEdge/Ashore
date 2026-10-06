"""Cross-platform Qt notification manager behaviour."""

import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtWidgets import QApplication

from interface.notificationManager import NotificationManager


class NotificationManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_click_emits_pending_task_id(self):
        tray = Mock()
        tray.messageClicked.connect = Mock()
        manager = NotificationManager(tray)
        activated = Mock()
        manager.activated.connect(activated)
        manager.pendingGid = 'gid-1'

        manager.handleMessageClick()
        self.app.processEvents()

        activated.assert_called_once_with('gid-1')

    @patch('interface.notificationManager.QSystemTrayIcon.supportsMessages',
           return_value=True)
    @patch('interface.notificationManager.QSystemTrayIcon.isSystemTrayAvailable',
           return_value=True)
    def test_show_uses_qt_tray_notification(self, _available, _supports):
        tray = Mock()
        tray.messageClicked.connect = Mock()
        manager = NotificationManager(tray)

        shown = manager.show('gid-2', 'Done', 'file.iso')

        self.assertTrue(shown)
        self.assertEqual(manager.pendingGid, 'gid-2')
        tray.showMessage.assert_called_once_with('Done', 'file.iso')

    @patch('interface.notificationManager.QSystemTrayIcon.supportsMessages',
           return_value=False)
    @patch('interface.notificationManager.QSystemTrayIcon.isSystemTrayAvailable',
           return_value=True)
    def test_show_reports_when_desktop_notifications_are_unavailable(
            self, _available, _supports):
        tray = Mock()
        tray.messageClicked.connect = Mock()
        manager = NotificationManager(tray)

        self.assertFalse(manager.show('gid-3', 'Done', 'file.iso'))
        tray.showMessage.assert_not_called()


if __name__ == '__main__':
    unittest.main()
