"""aria2 process lifecycle and asynchronous polling."""

import copy
import shutil
import subprocess
import time

from PyQt6.QtCore import QThread, QTimer, pyqtSignal

from core.aria2Client import RPC_METHODS, Aria2Client
from paths import CONFIG_DIR


class Aria2Service:
    """Own aria2 lifecycle separately from its JSON-RPC client."""

    def __init__(self, quitWithAshore=False):
        self.client = Aria2Client()
        self.quitWithAshore = quitWithAshore
        self.process = None

    def ensureReady(self):
        if not self.client.isRpcReady():
            self.start()

    def start(self):
        executable = shutil.which('aria2c')
        if not executable:
            raise RuntimeError('未检测到 aria2c。请先安装 aria2，再启动 Ashore。')
        self.client.readRpcOptions()
        logPath = CONFIG_DIR / 'aria2-startup.log'
        with logPath.open('ab') as log:
            self.process = subprocess.Popen(
                [executable, f'--conf-path={self.client.confPath}'],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.client.isRpcReady():
                return
            if self.process.poll() is not None:
                break
            time.sleep(0.25)
        if self.process.poll() is None:
            self.stopOwned()
        raise RuntimeError(
            f'aria2 RPC 未能在端口 {self.client.rpcPort} 启动。'
            f'请检查 {logPath} 和 aria2.conf。')

    def restart(self):
        self.client.saveSession()
        if self.process is not None and self.process.poll() is None:
            self.stopOwned()
        else:
            result = self.client.call(
                self.client.makeRequest(RPC_METHODS['shutdown']))
            if result != 'OK':
                message = result.get('ResultError', result) if isinstance(result, dict) else result
                raise RuntimeError(f'无法通过 RPC 正常关闭当前 aria2：{message}')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and self.client.isRpcReady():
                time.sleep(0.1)
            if self.client.isRpcReady():
                raise RuntimeError('当前 aria2 收到关闭请求后仍在运行。')
        self.start()

    def stopOwned(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process = None

    def close(self):
        self.client.saveSession()
        if self.quitWithAshore:
            self.stopOwned()


class Aria2Startup(QThread):
    statusChanged = pyqtSignal(str)
    ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, quitWithAshore=False, parent=None):
        super().__init__(parent)
        self.quitWithAshore = quitWithAshore

    def run(self):
        try:
            self.statusChanged.emit('正在检查 aria2')
            service = Aria2Service(self.quitWithAshore)
            service.ensureReady()
            self.statusChanged.emit('aria2 已连接')
            self.ready.emit(service)
        except (RuntimeError, OSError, ValueError) as exc:
            self.failed.emit(str(exc))


class Aria2Removal(QThread):
    """Run stateful task removal without blocking the GUI thread."""

    resultReady = pyqtSignal(str, dict)

    def __init__(self, client, gid, deleteFiles=False, parent=None):
        super().__init__(parent)
        self.client = client
        self.gid = gid
        self.deleteFiles = deleteFiles

    def run(self):
        result = self.client.removeMission(
            self.gid, delFile=self.deleteFiles)
        self.resultReady.emit(self.gid, result)


class Aria2Shutdown(QThread):
    """Finish pending RPC work and close aria2 without blocking the GUI."""

    failed = pyqtSignal(str)

    def __init__(self, service, poller, parent=None):
        super().__init__(parent)
        self.service = service
        self.poller = poller

    def run(self):
        try:
            self.poller.wait()
            self.service.close()
        except (RuntimeError, OSError, ValueError) as exc:
            self.failed.emit(str(exc))


class Aria2Poller(QThread):
    updated = pyqtSignal(dict)

    def __init__(self, client, interval=2000, parent=None):
        super().__init__(parent)
        self.client = client
        self.version = ''
        self.timer = QTimer(parent)
        self.timer.setInterval(max(500, interval))
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    def poll(self):
        if not self.isRunning():
            self.start()

    def run(self):
        missions = self.client.getMissions()
        status = self.client.lastPollGlobalStatus
        if 'ResultError' not in status and not self.version:
            self.version = self.client.getAria2Version()
        self.updated.emit({
            'missions': copy.deepcopy(missions),
            'globalStatus': dict(status),
            'aria2Version': self.version,
        })
