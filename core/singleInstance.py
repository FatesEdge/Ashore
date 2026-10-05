"""Single-instance ownership and IPC handoff for Ashore."""

import json
import os
from pathlib import Path

from PyQt6.QtCore import QLockFile, QObject, QStandardPaths, QThread, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceCoordinator(QObject):
    messageReceived = pyqtSignal(list)

    def __init__(self, applicationName='Ashore', parent=None, lockDirectory=None):
        super().__init__(parent)
        user = str(
            os.getuid()
            if hasattr(os, 'getuid')
            else os.environ.get('USERNAME', 'user'))
        self.serverName = f'{applicationName}-{user}'
        if lockDirectory is None:
            location = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.TempLocation)
            lockDirectory = Path(location or '.')
        else:
            lockDirectory = Path(lockDirectory)
        lockDirectory.mkdir(parents=True, exist_ok=True)
        self.lock = QLockFile(
            str(lockDirectory / f'{self.serverName}.instance.lock'))
        self.lock.setStaleLockTime(5000)
        self.server = None

    def claimOrForward(self, payload):
        """Return True for the primary process, False after forwarding."""
        if self.forward(payload, attempts=1):
            return False

        if self.lock.tryLock(0):
            self.startServer()
            return True

        if self.forward(payload, attempts=20):
            return False

        if self.lock.removeStaleLockFile() and self.lock.tryLock(0):
            self.startServer()
            return True

        raise RuntimeError(
            '另一个 Ashore 实例正在启动，但无法建立本地通信。')

    def startServer(self):
        QLocalServer.removeServer(self.serverName)
        self.server = QLocalServer(self)
        if not self.server.listen(self.serverName):
            self.lock.unlock()
            self.server = None
            raise RuntimeError('无法建立 Ashore 单实例通信通道')
        self.server.newConnection.connect(self.receiveConnection)

    def forward(self, payload, attempts=1):
        payload = list(payload or [])
        for attempt in range(max(1, attempts)):
            socket = QLocalSocket(self)
            socket.connectToServer(self.serverName)
            if socket.waitForConnected(120):
                socket.write(json.dumps(payload).encode('utf-8'))
                if not socket.waitForBytesWritten(1000):
                    socket.abort()
                    return False
                socket.disconnectFromServer()
                return True
            socket.abort()
            if attempt + 1 < attempts:
                QThread.msleep(50)
        return False

    def receiveConnection(self):
        socket = self.server.nextPendingConnection()
        if socket is None:
            return
        if not socket.bytesAvailable():
            socket.waitForReadyRead(1000)
        try:
            payload = json.loads(bytes(socket.readAll()).decode('utf-8'))
            if isinstance(payload, list):
                self.messageReceived.emit(payload)
        except (ValueError, UnicodeDecodeError):
            pass
        socket.disconnectFromServer()

    def close(self):
        if self.server is not None:
            self.server.close()
            self.server = None
        if self.lock.isLocked():
            self.lock.unlock()
