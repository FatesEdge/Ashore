"""Application instance routing and startup lifecycle for Ashore."""

from PyQt6.QtCore import QElapsedTimer, QEvent, QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox

from core.applicationInfo import configureApplication
from core.aria2Service import Aria2Startup
from core.configStore import boolValue, readAshore, writeAshore
from core.singleInstance import SingleInstanceCoordinator
from interface.languageManager import resolveLanguage
from interface.startupWindow import RecoveryWindow, StartupWindow
from interface.themeManager import ThemeManager
from paths import CONFIG_DIR, RESOURCE_DIR, ensureConfig


class AshoreApplication(QApplication):
    instanceMessage = pyqtSignal(list)

    def __init__(self, arguments):
        configureApplication()
        super().__init__(arguments)
        self.setQuitOnLastWindowClosed(False)
        self.pendingInstanceMessages = []
        self.instanceRoutingReady = False
        self.singleInstance = SingleInstanceCoordinator('Ashore', self)
        self.singleInstance.messageReceived.connect(self.routeInstanceMessage)
        self.aboutToQuit.connect(self.singleInstance.close)

    def claimSingleInstance(self, urls):
        return self.singleInstance.claimOrForward(urls)

    def routeInstanceMessage(self, urls):
        if self.instanceRoutingReady:
            self.instanceMessage.emit(urls)
        else:
            self.pendingInstanceMessages.append(list(urls))

    def enableInstanceRouting(self):
        self.instanceRoutingReady = True
        pending = self.pendingInstanceMessages
        self.pendingInstanceMessages = []
        for urls in pending:
            self.instanceMessage.emit(urls)

    def event(self, event):
        if event.type() == QEvent.Type.FileOpen:
            self.routeInstanceMessage([event.url().toString()])
        return super().event(event)


class StartupController(QObject):
    MIN_VISIBLE_MS = 900
    TRACKER_GRACE_MS = 1000

    def __init__(self, app, arguments, windowFactory):
        super().__init__(app)
        self.app = app
        self.arguments = arguments
        self.windowFactory = windowFactory
        self.window = None
        self.recovery = None
        self.finished = False
        self.finishScheduled = False
        self.firstSnapshotReady = False
        self.trackerReady = False
        self.clock = QElapsedTimer()
        self.themeManager = ThemeManager(app, self)
        self.splash = StartupWindow(RESOURCE_DIR / 'static/img/cover.png')
        self.splash.firstPainted.connect(self.checkInstance)
        self.startup = None
        self.settings = {}

    def start(self):
        self.clock.start()
        self.splash.show()

    def checkInstance(self):
        self.showStage('正在检查运行实例')
        try:
            if not self.app.claimSingleInstance(self.arguments[1:]):
                self.splash.close()
                self.app.quit()
                return
        except RuntimeError as exc:
            self.fail(str(exc))
            return
        QTimer.singleShot(0, self.loadConfig)

    def loadConfig(self):
        self.showStage('正在读取配置')
        try:
            ensureConfig('ashore.conf')
            ensureConfig('aria2.conf')
            self.settings = readAshore(
                CONFIG_DIR / 'ashore.conf',
                RESOURCE_DIR / 'config/ashore.conf')
            if self.settings.get('tray_icon_style') == 'monochrome':
                self.settings['tray_icon_style'] = 'gray'
                writeAshore(
                    CONFIG_DIR / 'ashore.conf',
                    {'tray_icon_style': 'gray'})
            self.themeManager.apply(
                self.settings.get('theme_mode', 'system'),
                self.settings.get('accent_color', '#5d795f'))
        except (OSError, ValueError) as exc:
            self.fail(str(exc))
            return
        QTimer.singleShot(0, self.startAria2)

    def startAria2(self):
        self.showStage('正在检查 aria2')
        self.startup = Aria2Startup(
            boolValue(self.settings.get('quit_with_aria2')), self)
        self.startup.statusChanged.connect(self.showStage)
        self.startup.ready.connect(self.buildWindow)
        self.startup.unhealthy.connect(self.showRecovery)
        self.startup.start()

    def buildWindow(self, service):
        if self.recovery is not None:
            self.recovery.close()
            self.recovery.deleteLater()
            self.recovery = None
        self.showStage('正在准备主界面')
        QTimer.singleShot(0, lambda: self.createWindow(service))

    def createWindow(self, service):
        try:
            self.window = self.windowFactory(service, self.themeManager)
        except (RuntimeError, OSError, ValueError) as exc:
            self.fail(str(exc))
            return

        self.app.instanceMessage.connect(self.handleInstance)
        self.window.aria2Poller.updated.connect(self.firstSnapshot)
        self.window.firstPainted.connect(self.mainPainted)

        tracker = self.window.pageSetting.trackerManager
        tracker.statusChanged.connect(self.showStage)
        tracker.updated.connect(self.trackerFinished)
        tracker.failed.connect(self.trackerFinished)

        self.showStage('正在同步下载任务')
        self.window.startRuntime()
        if self.window.pageSetting.startAutoTracker():
            QTimer.singleShot(self.TRACKER_GRACE_MS, self.trackerFinished)
        else:
            self.trackerReady = True
        self.tryFinish()

    def firstSnapshot(self, *_):
        self.firstSnapshotReady = True
        self.tryFinish()

    def trackerFinished(self, *_):
        self.trackerReady = True
        self.tryFinish()

    def tryFinish(self):
        if (self.finished or self.finishScheduled or self.window is None
                or not self.firstSnapshotReady or not self.trackerReady):
            return
        remaining = max(0, self.MIN_VISIBLE_MS - self.clock.elapsed())
        if remaining:
            self.finishScheduled = True
            QTimer.singleShot(remaining, self.finish)
        else:
            self.finish()

    def finish(self):
        if self.finished or self.window is None:
            return
        self.finished = True
        self.finishScheduled = False
        self.showStage('正在显示主界面')
        self.splash.finish(self.window)
        if len(self.arguments) > 1:
            self.window.addNew(self.arguments[1:])
        self.app.enableInstanceRouting()

    def mainPainted(self):
        QTimer.singleShot(0, self.finishRuntime)

    def finishRuntime(self):
        self.window.showTray()
        QTimer.singleShot(0, self.finishMigration)

    def finishMigration(self):
        self.window.offerDownloadMigration()

    def handleInstance(self, urls):
        if self.window is None:
            if self.recovery is not None:
                self.recovery.show()
                self.recovery.raise_()
                self.recovery.activateWindow()
            return
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        if urls:
            self.window.addNew(urls)

    def showRecovery(self, issue):
        self.splash.close()
        language = resolveLanguage(self.settings.get('language'))
        if self.recovery is None:
            self.recovery = RecoveryWindow(issue, language)
            self.recovery.recheckRequested.connect(self.retryEnvironment)
            self.recovery.quitRequested.connect(self.quit)
        else:
            self.recovery.setIssue(issue)
        self.recovery.show()
        self.recovery.raise_()
        self.recovery.activateWindow()

    def retryEnvironment(self):
        if self.startup is not None and self.startup.isRunning():
            return
        if self.recovery is not None:
            self.recovery.hide()
        self.splash.showStatus('正在重新检查 aria2')
        self.splash.show()
        self.splash.raise_()
        self.splash.activateWindow()
        QTimer.singleShot(0, self.startAria2)

    def showStage(self, message):
        self.splash.showStatus(message)

    def fail(self, message):
        self.splash.close()
        if self.recovery is not None:
            self.recovery.close()
        QMessageBox.critical(None, 'Ashore 启动失败', message)
        self.app.quit()

    def quit(self):
        if self.window:
            self.window.slotQuit()
            return
        if self.recovery is not None:
            self.recovery.close()
        self.app.quit()

    def dispose(self):
        """Break Python/Qt ownership cycles while QApplication is still alive."""
        app = self.app
        window = self.window

        if window is not None:
            try:
                app.instanceMessage.disconnect(self.handleInstance)
            except (TypeError, RuntimeError):
                pass
            window.windowChrome.uninstall()
            window.aria2Poller.timer.stop()
            window.aria2Events.stop()
            window.trayIcon.hide()
            window.close()
            window.deleteLater()
            self.window = None

        if self.recovery is not None:
            self.recovery.close()
            self.recovery.deleteLater()
            self.recovery = None

        if self.splash is not None:
            self.splash.close()
            self.splash.deleteLater()
            self.splash = None

        if self.startup is not None:
            if self.startup.isRunning():
                self.startup.wait()
            self.startup.deleteLater()
            self.startup = None

        self.themeManager = None
        self.app = None
