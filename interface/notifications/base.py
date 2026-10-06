"""Notification backend contract."""

from PyQt6.QtCore import QObject, pyqtSignal


class NotificationBackend(QObject):
    activated = pyqtSignal(str)

    def show(self, gid, title, body):
        raise NotImplementedError
