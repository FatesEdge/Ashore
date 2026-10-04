"""Use aria2 WebSocket notifications to refresh promptly while HTTP remains authoritative."""

import json

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QAbstractSocket

try:
    from PyQt6.QtWebSockets import QWebSocket
except ImportError:
    QWebSocket = None


class Aria2Events(QObject):
    notification = pyqtSignal(str, str)
    connectionStateChanged = pyqtSignal(str)

    def __init__(self, port, parent=None):
        super().__init__(parent)
        self.socket = None
        self.state = 'unavailable'
        self.stopped = False
        if QWebSocket is None:
            return
        self.address = QUrl(f'ws://127.0.0.1:{port}/jsonrpc')
        self.retry = QTimer(self)
        self.retry.setSingleShot(True)
        self.retry.setInterval(5000)
        self.retry.timeout.connect(self.openSocket)
        self.socket = QWebSocket()
        self.socket.textMessageReceived.connect(self.receive)
        self.socket.connected.connect(self.connected)
        self.socket.disconnected.connect(self.reconnect)
        (self.socket.errorOccurred if hasattr(self.socket, 'errorOccurred')
         else self.socket.error).connect(self.reconnect)
        self.openSocket()

    def setState(self, state):
        if state != self.state:
            self.state = state
            self.connectionStateChanged.emit(state)

    def connected(self):
        self.retry.stop()
        self.setState('connected')

    def openSocket(self):
        if (self.socket is not None and not self.stopped
                and self.socket.state() == QAbstractSocket.SocketState.UnconnectedState):
            self.setState('connecting')
            self.socket.open(self.address)

    def reconnect(self, *_):
        self.setState('disconnected')
        if not self.stopped and not self.retry.isActive():
            self.retry.start()

    def receive(self, message):
        try:
            data = json.loads(message)
            method = data['method']
            gid = data['params'][0]['gid']
        except (ValueError, KeyError, IndexError, TypeError):
            return
        if method.startswith('aria2.on'):
            self.notification.emit(method, gid)

    def stop(self):
        if self.socket is not None:
            self.stopped = True
            self.retry.stop()
            self.socket.close()
            self.setState('stopped')

    def setPort(self, port):
        if self.socket is not None and self.address.port() != port:
            self.retry.stop()
            self.socket.close()
            self.address = QUrl(f'ws://127.0.0.1:{port}/jsonrpc')
            self.stopped = False
            QTimer.singleShot(0, self.openSocket)
