"""Cross-platform Qt notification handling."""

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QSystemTrayIcon


class NotificationManager(QObject):
    """Show Qt tray notifications and map clicks back to task ids."""

    activated = pyqtSignal(str)

    def __init__(self, trayIcon, parent=None):
        super().__init__(parent)
        self.trayIcon = trayIcon
        self.pendingGid = None
        self.trayIcon.messageClicked.connect(self.handleMessageClick)

    def show(self, gid, title, body):
        self.pendingGid = gid
        if not (
                QSystemTrayIcon.isSystemTrayAvailable()
                and QSystemTrayIcon.supportsMessages()):
            return False
        self.trayIcon.showMessage(title, body)
        return True

    def handleMessageClick(self):
        gid = self.pendingGid
        if gid:
            self.activated.emit(gid)
