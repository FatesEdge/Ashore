"""Desktop-session synchronization kept outside the application window."""

from PyQt6.QtCore import QObject, QTimer

try:
    from PyQt6.QtDBus import QDBusConnection, QDBusMessage, QDBusPendingCallWatcher
except ImportError:  # QtDBus is not shipped on every supported platform.
    QDBusConnection = QDBusMessage = QDBusPendingCallWatcher = None


class DesktopIntegration(QObject):
    """Wait until a tray D-Bus action has completed before ending the process."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.watchers = set()

    def afterTrayEvent(self, callback):
        QTimer.singleShot(0, lambda: self.startRoundTrip(callback))

    def startRoundTrip(self, callback):
        if QDBusConnection is None:
            callback()
            return
        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            callback()
            return
        message = QDBusMessage.createMethodCall(
            'org.freedesktop.DBus',
            '/org/freedesktop/DBus',
            'org.freedesktop.DBus.Peer',
            'Ping')
        watcher = QDBusPendingCallWatcher(bus.asyncCall(message), self)
        self.watchers.add(watcher)
        watcher.finished.connect(
            lambda finished: self.finishRoundTrip(finished, callback))

    def finishRoundTrip(self, watcher, callback):
        self.watchers.discard(watcher)
        watcher.deleteLater()
        callback()
