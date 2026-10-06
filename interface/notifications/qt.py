"""Qt tray notification fallback."""

from PyQt6.QtWidgets import QSystemTrayIcon

from .base import NotificationBackend


class QtNotificationBackend(NotificationBackend):
    def __init__(self, trayIcon, parent=None):
        super().__init__(parent)
        self.trayIcon = trayIcon
        self.pendingGid = None
        self.trayIcon.messageClicked.connect(self._messageClicked)

    def show(self, gid, title, body):
        self.pendingGid = gid
        if (QSystemTrayIcon.isSystemTrayAvailable()
                and QSystemTrayIcon.supportsMessages()):
            self.trayIcon.showMessage(title, body)

    def _messageClicked(self):
        if self.pendingGid:
            self.activated.emit(self.pendingGid)
