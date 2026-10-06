"""Platform notification backend selection."""

import sys

from .qt import QtNotificationBackend


def createNotificationBackend(trayIcon, iconPath='', parent=None):
    if sys.platform.startswith('linux'):
        try:
            from .linux import LinuxNotificationBackend
            backend = LinuxNotificationBackend(iconPath, parent)
            if backend.available:
                return backend
        except (ImportError, RuntimeError):
            pass
    return QtNotificationBackend(trayIcon, parent)
