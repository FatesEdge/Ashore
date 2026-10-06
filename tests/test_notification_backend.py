"""Notification backend behaviour."""

import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtWidgets import QApplication

from interface.notifications.qt import QtNotificationBackend


class NotificationBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_qt_fallback_maps_click_to_pending_gid(self):
        tray = Mock()
        tray.messageClicked.connect = Mock()
        backend = QtNotificationBackend(tray)
        activated = Mock()
        backend.activated.connect(activated)
        backend.pendingGid = 'gid-1'

        backend._messageClicked()
        self.app.processEvents()

        activated.assert_called_once_with('gid-1')

    @patch('interface.notifications.qt.QSystemTrayIcon.supportsMessages',
           return_value=True)
    @patch('interface.notifications.qt.QSystemTrayIcon.isSystemTrayAvailable',
           return_value=True)
    def test_qt_fallback_shows_message(self, _available, _supports):
        tray = Mock()
        tray.messageClicked.connect = Mock()
        backend = QtNotificationBackend(tray)

        backend.show('gid-2', 'Done', 'file.iso')

        self.assertEqual(backend.pendingGid, 'gid-2')
        tray.showMessage.assert_called_once_with('Done', 'file.iso')


if __name__ == '__main__':
    unittest.main()
