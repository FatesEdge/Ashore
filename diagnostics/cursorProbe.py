"""Build Ashore one production component at a time to isolate cursor issues."""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtNetwork import QLocalServer
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


@dataclass(frozen=True)
class ProbeStage:
    name: str
    description: str


PROBE_STAGES = (
    ProbeStage('base', 'QApplication + plain QWidget'),
    ProbeStage('identity', 'Ashore application identity'),
    ProbeStage('shell', 'QMainWindow, menu bar and status bar'),
    ProbeStage('theme', 'ThemeManager and global style sheet'),
    ProbeStage('tasks', 'Page and Section task widgets'),
    ProbeStage('settings', 'SettingPage and local configuration'),
    ProbeStage('tray', 'QSystemTrayIcon, hide, show and quit actions'),
    ProbeStage('singleInstance', 'QLocalServer single-instance channel'),
    ProbeStage('ariaClient', 'Aria2Service and HTTP client configuration'),
    ProbeStage('ariaPoller', 'Background aria2 HTTP polling thread'),
    ProbeStage('webSocket', 'aria2 WebSocket notification channel'),
    ProbeStage('tracker', 'TrackerManager automatic update decision'),
    ProbeStage('asyncShutdown', 'Ashore asynchronous shutdown worker'),
    ProbeStage('startupWindow', 'StartupWindow to main-window transition'),
)


def stageIndex(name):
    return next(index for index, stage in enumerate(PROBE_STAGES)
                if stage.name == name)


def includes(selected, required):
    return stageIndex(selected) >= stageIndex(required)


class BaseProbeWindow(QWidget):
    def __init__(self, stage):
        super().__init__()
        self.setWindowTitle(f'Ashore Cursor Probe — {stage}')
        self.resize(640, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f'<h2>Cursor probe: {stage}</h2>'
            'This stage contains only a plain QWidget. Close it normally.'))
        layout.addStretch()


class ProbeWindow(QMainWindow):
    def __init__(self, stage, app):
        super().__init__()
        self.stage = stage
        self.app = app
        self.trayIcon = None
        self.trayMenu = None
        self.localServer = None
        self.aria2Service = None
        self.aria2Poller = None
        self.aria2Events = None
        self.shutdown = None
        self.setWindowTitle(f'Ashore Cursor Probe — {stage}')
        self.resize(960, 620)
        self.tabs = QTabWidget()
        overview = QWidget()
        overviewLayout = QVBoxLayout(overview)
        overviewLayout.addWidget(QLabel(
            f'<h2>Cursor probe: {stage}</h2>'
            'Close normally before the tray stage. At and after the tray stage, '
            'close the window, reopen it from the tray, then choose Quit.'))
        overviewLayout.addStretch()
        self.tabs.addTab(overview, 'Overview')
        self.setCentralWidget(self.tabs)
        self.buildStage()

    def buildStage(self):
        if includes(self.stage, 'shell'):
            self.buildShell()
        if includes(self.stage, 'theme'):
            self.buildTheme()
        if includes(self.stage, 'tasks'):
            self.buildTasks()
        if includes(self.stage, 'settings'):
            self.buildSettings()
        if includes(self.stage, 'tray'):
            self.buildTray()
        if includes(self.stage, 'singleInstance'):
            self.buildSingleInstance()
        if includes(self.stage, 'ariaClient'):
            self.buildAriaClient()
        if includes(self.stage, 'ariaPoller'):
            self.buildAriaPoller()
        if includes(self.stage, 'webSocket'):
            self.buildWebSocket()
        if includes(self.stage, 'tracker'):
            self.buildTracker()

    def buildShell(self):
        fileMenu = self.menuBar().addMenu('File')
        quitAction = QAction('Quit', self)
        quitAction.setShortcut('Ctrl+Q')
        quitAction.triggered.connect(self.quitProbe)
        fileMenu.addAction(quitAction)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage('Shell ready')

    def buildTheme(self):
        from interface.themeManager import ThemeManager

        self.themeManager = ThemeManager(self.app, self)
        self.themeManager.apply('system', '#5d795f')

    def buildTasks(self):
        from interface.page import Page

        page = Page()
        page.updateSections({'active': {'probe-gid': {
            'filename': 'cursor-probe.bin',
            'totalLength': 100,
            'completedLength': 42,
            'downloadSpeed': 1024,
            'isTorrent': False,
        }}})
        self.tabs.addTab(page, 'Tasks')
        self.taskPage = page

    def buildSettings(self):
        from interface.settingPage import SettingPage

        self.settingPage = SettingPage()
        self.tabs.addTab(self.settingPage, 'Settings')

    def buildTray(self):
        from paths import RESOURCE_DIR

        self.app.setQuitOnLastWindowClosed(False)
        self.trayMenu = QMenu()
        showAction = QAction('Show window', self)
        quitAction = QAction('Quit probe', self)
        showAction.triggered.connect(
            lambda: self.deferTrayAction(self.showFromTray))
        quitAction.triggered.connect(
            lambda: self.deferTrayAction(self.quitProbe))
        self.trayMenu.addAction(showAction)
        self.trayMenu.addAction(quitAction)
        iconPath = RESOURCE_DIR / 'static/icon/functionIcons/trayIcon.png'
        self.trayIcon = QSystemTrayIcon(QIcon(str(iconPath)), self)
        self.trayIcon.setContextMenu(self.trayMenu)
        self.trayIcon.setToolTip(f'Ashore cursor probe: {self.stage}')
        self.trayIcon.show()

    def deferTrayAction(self, callback):
        self.trayMenu.close()
        QTimer.singleShot(0, callback)

    def showFromTray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def buildSingleInstance(self):
        name = f'Ashore-CursorProbe-{os.getpid()}'
        self.localServer = QLocalServer(self)
        QLocalServer.removeServer(name)
        if not self.localServer.listen(name):
            self.statusBar().showMessage(
                'QLocalServer unavailable: ' + self.localServer.errorString())

    def buildAriaClient(self):
        from core.aria2Service import Aria2Service

        self.aria2Service = Aria2Service(False)

    def buildAriaPoller(self):
        from core.aria2Service import Aria2Poller

        self.aria2Poller = Aria2Poller(self.aria2Service.client, 2000, self)
        self.aria2Poller.updated.connect(
            lambda _snapshot: self.statusBar().showMessage('aria2 HTTP snapshot received'))
        self.aria2Poller.poll()

    def buildWebSocket(self):
        from core.aria2Events import Aria2Events

        self.aria2Events = Aria2Events(self.aria2Service.client.rpcPort, self)
        self.aria2Events.connectionStateChanged.connect(
            lambda state: self.statusBar().showMessage(f'WebSocket: {state}'))

    def buildTracker(self):
        if not hasattr(self, 'settingPage'):
            return
        manager = self.settingPage.trackerManager
        manager.statusChanged.connect(self.statusBar().showMessage)
        manager.start()

    def closeEvent(self, event):
        if self.trayIcon is not None and self.trayIcon.isVisible():
            event.ignore()
            self.hide()
        else:
            event.accept()

    def quitProbe(self):
        if self.aria2Poller is not None:
            self.aria2Poller.timer.stop()
        if self.aria2Events is not None:
            self.aria2Events.stop()
        self.hide()
        if self.trayIcon is not None:
            self.trayIcon.hide()
        if includes(self.stage, 'asyncShutdown') and self.aria2Poller is not None:
            from core.aria2Service import Aria2Shutdown

            self.shutdown = Aria2Shutdown(
                self.aria2Service, self.aria2Poller, self.app)
            self.shutdown.finished.connect(self.app.quit)
            self.shutdown.start()
            return
        if self.aria2Poller is not None:
            self.aria2Poller.wait()
        self.app.quit()


class CursorProbe(QObject):
    def __init__(self, app, stage):
        super().__init__(app)
        self.app = app
        self.stage = stage
        self.window = None
        if not includes(stage, 'startupWindow'):
            self.window = self.buildWindow()
        self.startupWindow = None

    def buildWindow(self):
        return (ProbeWindow(self.stage, self.app)
                if includes(self.stage, 'shell') else BaseProbeWindow(self.stage))

    def start(self):
        print(f'Cursor probe stage: {self.stage}', flush=True)
        if includes(self.stage, 'startupWindow'):
            from interface.startupWindow import StartupWindow
            from paths import RESOURCE_DIR

            self.startupWindow = StartupWindow(RESOURCE_DIR / 'static/img/cover.png')
            self.startupWindow.firstPainted.connect(self.buildAfterSplash)
            self.startupWindow.show()
            return
        self.window.show()

    def buildAfterSplash(self):
        self.window = self.buildWindow()
        QTimer.singleShot(900, self.finishStartup)

    def finishStartup(self):
        self.window.show()
        self.startupWindow.close()
        self.startupWindow.deleteLater()
        self.startupWindow = None


def buildParser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=[stage.name for stage in PROBE_STAGES],
                        default='base')
    parser.add_argument('--list', action='store_true', help='list cumulative stages')
    return parser


def main(arguments=None):
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    options = buildParser().parse_args(arguments)
    if options.list:
        for index, stage in enumerate(PROBE_STAGES):
            print(f'{index:2d}  {stage.name:15s} {stage.description}')
        return 0
    if includes(options.stage, 'identity'):
        from core.applicationInfo import configureApplication

        configureApplication()
    app = QApplication([sys.argv[0]])
    probe = CursorProbe(app, options.stage)
    app.cursorProbe = probe
    probe.start()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
