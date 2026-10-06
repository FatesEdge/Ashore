"""Freedesktop notification backend for Linux desktops."""

from .base import NotificationBackend


class LinuxNotificationBackend(NotificationBackend):
    SERVICE = 'org.freedesktop.Notifications'
    PATH = '/org/freedesktop/Notifications'
    INTERFACE = 'org.freedesktop.Notifications'

    def __init__(self, iconPath='', parent=None):
        super().__init__(parent)
        self.iconPath = iconPath
        self.notificationTargets = {}

        from PyQt6.QtDBus import (
            QDBusConnection, QDBusInterface, QDBusMessage,
        )

        self.errorMessageType = QDBusMessage.MessageType.ErrorMessage
        self.bus = QDBusConnection.sessionBus()
        self.interface = QDBusInterface(
            self.SERVICE, self.PATH, self.INTERFACE, self.bus)
        self.available = (
            self.bus.isConnected() and self.interface.isValid())
        if self.available:
            self.bus.connect(
                self.SERVICE,
                self.PATH,
                self.INTERFACE,
                'ActionInvoked',
                self._actionInvoked)

    def show(self, gid, title, body):
        if not self.available:
            raise RuntimeError('freedesktop notification service unavailable')

        actions = ['default', 'Open Ashore']
        hints = {
            'desktop-entry': 'ashore',
            'category': 'transfer.complete',
        }
        reply = self.interface.call(
            'Notify',
            'Ashore',
            0,
            self.iconPath,
            title,
            body,
            actions,
            hints,
            -1)
        if reply.type() == self.errorMessageType:
            raise RuntimeError(reply.errorMessage())
        arguments = reply.arguments()
        if not arguments:
            raise RuntimeError('notification service returned no id')
        notificationId = int(arguments[0])
        self.notificationTargets[notificationId] = gid

    def _actionInvoked(self, notificationId, actionKey):
        if actionKey != 'default':
            return
        gid = self.notificationTargets.pop(int(notificationId), None)
        if gid:
            self.activated.emit(gid)
