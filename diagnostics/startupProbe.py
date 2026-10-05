"""Add Ashore's real startup groups cumulatively to isolate cursor feedback."""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QObject, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from Ashore import Aria2Events, Ashore, AshoreApplication
from core.aria2Service import Aria2Startup
from core.configStore import boolValue, readAshore
from interface.startupWindow import StartupWindow
from interface.themeManager import ThemeManager
from paths import CONFIG_DIR, RESOURCE_DIR, ensureConfig


@dataclass(frozen=True)
class StartupStage:
    name: str
    description: str


STARTUP_STAGES = (
    StartupStage('base', 'AshoreApplication, StartupWindow and plain QWidget'),
    StartupStage('config', 'configuration loading and ThemeManager'),
    StartupStage('ariaStartup', 'Aria2Startup.ensureReady in its worker thread'),
    StartupStage('windowBase', 'Ashore base state and an empty central widget'),
    StartupStage('windowFrame', 'production window size, title and application icon'),
    StartupStage('windowControlsPlain', 'navigation and toolbar without image icons'),
    StartupStage('windowSingleIcon', 'add one selected button image icon'),
    StartupStage('windowFirstTwoIcons', 'add downloading and completed icons'),
    StartupStage('windowNavigationIcons', 'add the three navigation image icons'),
    StartupStage('windowControls', 'navigation and toolbar with placeholder pages'),
    StartupStage('windowContent', 'navigation, toolbar and all three pages'),
    StartupStage('windowMenus', 'production application menus'),
    StartupStage('windowStatus', 'production status bar and connection labels'),
    StartupStage('windowTray', 'construct the tray icon and its menu'),
    StartupStage('windowSignals', 'connect production window signals'),
    StartupStage('mainWindow', 'add the production aria2 WebSocket client'),
    StartupStage('runtime', 'wait for the first aria2 HTTP snapshot'),
    StartupStage('tracker', 'include the startup BT Tracker decision'),
    StartupStage('tray', 'register the production system tray icon'),
)


def stageIndex(name):
    return next(index for index, stage in enumerate(STARTUP_STAGES)
                if stage.name == name)


def includes(selected, required):
    return stageIndex(selected) >= stageIndex(required)


def iconLoader(names, mode='file'):
    def loadIcon(source=None):
        if source is not None and Path(str(source)).name in names:
            if mode == 'delayed':
                return QIcon()
            if mode == 'preloaded':
                pixmap = QPixmap(source).scaled(
                    QSize(24, 24), Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                return QIcon(pixmap)
            return QIcon(source)
        return QIcon()
    return loadIcon


class PlainWindow(QWidget):
    def __init__(self, stage, app):
        super().__init__()
        self.app = app
        self.setWindowTitle(f'Ashore Startup Probe — {stage}')
        self.resize(640, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f'<h2>Startup probe: {stage}</h2>'))
        closeButton = QPushButton('Exit probe')
        closeButton.clicked.connect(app.quit)
        layout.addWidget(closeButton)
        layout.addStretch()

    def closeEvent(self, event):
        event.accept()
        self.app.quit()


class IdleEvents(QObject):
    """Keep pre-WebSocket stages structurally identical without doing I/O."""

    notification = pyqtSignal(str, str)
    connectionStateChanged = pyqtSignal(str)
    state = 'unavailable'

    def __init__(self, _port, parent=None):
        super().__init__(parent)

    def stop(self):
        pass


class IdlePage(QWidget):
    """Stand in for download pages while retaining the production layout."""

    sectionAdded = pyqtSignal(object)

    def updateSections(self, _missions):
        pass


class StagedAshore(Ashore):
    """Expose cumulative boundaries inside Ashore.__init__ for diagnosis."""

    def __init__(
            self, aria2Service, themeManager, probeStage, singleIcon, iconMode):
        self.probeStage = probeStage
        self.singleIcon = singleIcon
        self.iconMode = iconMode
        super().__init__(aria2Service, themeManager)

    def initUI(self):
        if not includes(self.probeStage, 'windowFrame'):
            self.setCentralWidget(QLabel(f'Ashore window base: {self.probeStage}'))
            self.setWindowTitle('Ashore Startup Probe')
            self.resize(640, 360)
            return
        if not includes(self.probeStage, 'windowControlsPlain'):
            self.setCentralWidget(QLabel('Ashore production window frame'))
            self.setMinimumSize(1000, 520)
            self.setWindowTitle('Ashore')
            self.setWindowIcon(QIcon(
                self.resourcePath + 'static/icon/functionIcons/icon.png'))
            return
        if not includes(self.probeStage, 'windowSingleIcon'):
            with (
                    patch('Ashore.Page', IdlePage),
                    patch('Ashore.QIcon', lambda *_args: QIcon())):
                super().initUI()
            return
        if not includes(self.probeStage, 'windowFirstTwoIcons'):
            with (
                    patch('Ashore.Page', IdlePage),
                    patch('Ashore.QIcon', iconLoader(
                        {self.singleIcon}, self.iconMode))):
                super().initUI()
            return
        if not includes(self.probeStage, 'windowNavigationIcons'):
            firstIcons = {'download.png', 'completed.png'}
            with (
                    patch('Ashore.Page', IdlePage),
                    patch('Ashore.QIcon', iconLoader(firstIcons))):
                super().initUI()
            return
        if not includes(self.probeStage, 'windowControls'):
            navigationIcons = {'download.png', 'completed.png', 'setting.png'}
            with (
                    patch('Ashore.Page', IdlePage),
                    patch('Ashore.QIcon', iconLoader(navigationIcons))):
                super().initUI()
            return
        if not includes(self.probeStage, 'windowContent'):
            with patch('Ashore.Page', IdlePage):
                super().initUI()
            return
        super().initUI()

    def createMenuBar(self):
        if includes(self.probeStage, 'windowMenus'):
            super().createMenuBar()

    def createStatusBar(self):
        if includes(self.probeStage, 'windowStatus'):
            super().createStatusBar()

    def createTrayIcon(self):
        if includes(self.probeStage, 'windowTray'):
            super().createTrayIcon()

    def connectSignals(self):
        if includes(self.probeStage, 'windowSignals'):
            super().connectSignals()

    def updateConnection(self, httpStatus):
        if includes(self.probeStage, 'windowStatus'):
            super().updateConnection(httpStatus)

    def applyDelayedIcon(self):
        buttons = {
            'download.png': self.tabDownloading,
            'completed.png': self.tabDownloaded,
            'setting.png': self.tabSetting,
            'add.png': self.addBtn,
            'play.png': self.unpauseAllBtn,
            'pause.png': self.pauseAllBtn,
        }
        source = self.resourcePath + 'static/icon/functionIcons/' + self.singleIcon
        buttons[self.singleIcon].setIcon(QIcon(source))
        print(f'Delayed icon applied after first paint: {self.singleIcon}', flush=True)


class StartupProbe(QObject):
    TRACKER_GRACE_MS = 1000

    def __init__(self, app, stage, singleIcon, iconMode):
        super().__init__(app)
        self.app = app
        self.stage = stage
        self.singleIcon = singleIcon
        self.iconMode = iconMode
        self.splash = StartupWindow(RESOURCE_DIR / 'static/img/cover.png')
        self.splash.firstPainted.connect(self.begin)
        self.themeManager = ThemeManager(app, self)
        self.settings = None
        self.startup = None
        self.service = None
        self.window = None
        self.snapshotReady = False
        self.trackerReady = False

    def start(self):
        print(f'Startup probe stage: {self.stage}', flush=True)
        self.splash.show()

    def begin(self):
        if not includes(self.stage, 'config'):
            self.showPlain()
            return
        ensureConfig('ashore.conf')
        ensureConfig('aria2.conf')
        self.settings = readAshore(
            CONFIG_DIR / 'ashore.conf', RESOURCE_DIR / 'config/ashore.conf')
        self.themeManager.apply(
            self.settings.get('theme_mode', 'system'),
            self.settings.get('accent_color', '#5d795f'))
        if not includes(self.stage, 'ariaStartup'):
            self.showPlain()
            return
        self.startAria2()

    def showPlain(self):
        self.window = PlainWindow(self.stage, self.app)
        self.splash.finish(self.window)

    def startAria2(self):
        self.startup = Aria2Startup(
            boolValue(self.settings.get('quit_with_aria2')), self)
        self.startup.statusChanged.connect(
            lambda message: print(message, flush=True))
        self.startup.ready.connect(self.ariaReady)
        self.startup.failed.connect(self.fail)
        self.startup.start()

    def ariaReady(self, service):
        self.service = service
        if not includes(self.stage, 'windowBase'):
            self.showPlain()
            return
        self.buildWindow()

    def buildWindow(self):
        eventsClass = Aria2Events if includes(self.stage, 'mainWindow') else IdleEvents
        with patch('Ashore.Aria2Events', eventsClass):
            self.window = StagedAshore(
                self.service, self.themeManager, self.stage,
                self.singleIcon, self.iconMode)
        if not includes(self.stage, 'runtime'):
            self.window.aria2Poller.timer.stop()
            if self.iconMode == 'delayed':
                self.window.firstPainted.connect(self.window.applyDelayedIcon)
            self.splash.finish(self.window)
            return
        self.window.aria2Poller.updated.connect(self.snapshotFinished)
        self.window.startRuntime()
        if includes(self.stage, 'tracker'):
            tracker = self.window.pageSetting.trackerManager
            tracker.updated.connect(self.trackerFinished)
            tracker.failed.connect(self.trackerFinished)
            if self.window.pageSetting.startAutoTracker():
                QTimer.singleShot(self.TRACKER_GRACE_MS, self.trackerFinished)
            else:
                self.trackerReady = True
        else:
            self.trackerReady = True
        self.tryShow()

    def snapshotFinished(self, *_):
        self.snapshotReady = True
        self.tryShow()

    def trackerFinished(self, *_):
        self.trackerReady = True
        self.tryShow()

    def tryShow(self):
        if not self.snapshotReady or not self.trackerReady:
            return
        self.splash.finish(self.window)
        if includes(self.stage, 'tray'):
            QTimer.singleShot(0, self.window.showTray)

    def fail(self, message):
        print(f'Startup probe failed: {message}', file=sys.stderr, flush=True)
        self.app.quit()


def buildParser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=[stage.name for stage in STARTUP_STAGES],
                        default='base')
    parser.add_argument(
        '--single-icon', dest='singleIcon', default='download.png',
        choices=('download.png', 'completed.png', 'setting.png',
                 'add.png', 'play.png', 'pause.png'),
        help='button image used by the windowSingleIcon stage')
    parser.add_argument(
        '--icon-mode', dest='iconMode', choices=('file', 'preloaded', 'delayed'),
        default='file', help='how the selected image is converted to QIcon')
    parser.add_argument('--list', action='store_true', help='list cumulative stages')
    return parser


def main(arguments=None):
    options = buildParser().parse_args(
        sys.argv[1:] if arguments is None else arguments)
    if options.list:
        for index, stage in enumerate(STARTUP_STAGES):
            print(f'{index:2d}  {stage.name:12s} {stage.description}')
        return 0
    app = AshoreApplication([sys.argv[0]])
    probe = StartupProbe(
        app, options.stage, options.singleIcon, options.iconMode)
    app.startupProbe = probe
    probe.start()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
