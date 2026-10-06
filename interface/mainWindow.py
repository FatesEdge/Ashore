"""Ashore main window and runtime UI orchestration."""

import platform
import sys

from PyQt6.QtCore import QEvent, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QIcon,
    QPainter,
    QPalette,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from core.applicationInfo import APP_AUTHOR, APP_VERSION, PROJECT_URL
from core.aria2Client import ERROR_MESSAGES
from core.aria2Events import Aria2Events
from core.aria2Service import Aria2Poller, Aria2Removal, Aria2Shutdown
from core.configStore import boolValue
from core.fileOperations import revealDownloadedFile
from core.formatters import formatSpeed
from interface.actionIcons import actionIcon
from interface.addNewDialog import AddNewDialog
from interface.languageManager import resolveLanguage, translate
from interface.notificationManager import NotificationManager
from interface.page import Page
from interface.settingPage import SettingPage
from interface.startupWindow import ExitWindow
from interface.themeManager import TRAY_GRAY
from interface.titleBar import TitleBar
from interface.windowChrome import WindowChrome
from paths import RESOURCE_DIR, legacyDownloadDirectoryMigration


class Ashore(QMainWindow):
    firstPainted = pyqtSignal()


    def __init__(self, aria2Service, themeManager):
        super().__init__()
        self.windowChrome = WindowChrome(self)
        self.hasPainted = False
        self.isRelease = bool(getattr(sys, 'frozen', False))
        self.resourcePath = str(RESOURCE_DIR) + '/'

        self.pageSetting = SettingPage()
        ashoreConfig = self.pageSetting.loadAshoreConfig()
        self.language = resolveLanguage(ashoreConfig.get('language'))
        self.trayIconStyle = ashoreConfig.get(
            'tray_icon_style', 'colorful')
        self.showAria2Status = boolValue(
            ashoreConfig.get('show_aria2_status', True))

        self.aria2Service = aria2Service
        self.aria2Service.quitWithAshore = ashoreConfig['quit_with_aria2']
        self.aria2Client = aria2Service.client
        self.aria2Poller = Aria2Poller(
            self.aria2Client,
            int(ashoreConfig['update_interval']),
            self)
        self.themeManager = themeManager

        self.exitWindow = None
        self.notificationTarget = None
        self.removalWorkers = {}
        self.knownStatuses = None
        self.pendingNotifications = {}
        self.notifiedDownloads = set()
        self.aria2ConfigError = None
        self.quitting = False
        self.websocketState = 'unavailable'
        self.aria2Version = ''
        self.pendingConnectionState = 'waitingCheck'

        self.initUI()
        self.windowChrome.install()
        self.connectSignals()
        self.aria2Poller.updated.connect(self.updatePage)

        self.aria2Events = Aria2Events(self.aria2Client.rpcPort, self)
        self.aria2Events.notification.connect(self.slotAria2Notification)
        self.aria2Events.connectionStateChanged.connect(
            self.slotWebSocketStateChanged)
        self.websocketState = self.aria2Events.state

    def startRuntime(self):
        """Start asynchronous work after the startup controller is listening."""
        self.aria2Poller.poll()

    def showEvent(self, event):
        self.windowChrome.install()
        super().showEvent(event)

    def closeEvent(self, event):
        self.windowChrome.uninstall()
        super().closeEvent(event)

    def showTray(self):
        if not self.trayIcon.isVisible():
            self.trayIcon.show()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.hasPainted:
            self.hasPainted = True
            QTimer.singleShot(0, self.finishFirstPaint)

    def finishFirstPaint(self):
        self.flushConnectionStatus()
        self.firstPainted.emit()

    def event(self, event):
        if (event.type() == QEvent.Type.StatusTip
                and hasattr(self, 'statusMessageLabel')):
            self.statusMessageLabel.setText(event.tip())
            return True
        return super().event(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if (event.type() == QEvent.Type.PaletteChange
                and hasattr(self, 'addBtn')):
            self.refreshActionIcons()
        elif (event.type() == QEvent.Type.WindowStateChange
                and hasattr(self, 'titleBar')):
            self.titleBar.syncWindowState()
            self.syncWindowSurfaceState()


    def syncWindowSurfaceState(self):
        if not hasattr(self, 'windowSurface'):
            return
        maximized = self.isMaximized() or self.isFullScreen()
        for widget in (self.windowSurface, self.titleBar, self.statusStrip):
            widget.setProperty('windowMaximized', maximized)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def createCommandActions(self) -> None:
        """Create low-frequency actions for the command-bar overflow menu."""
        self.menuActions = {}
        saveAction = QAction(self.tr('saveSession'), self, triggered=self.slotSaveSession)
        saveAction.setStatusTip(self.tr('saveSessionTip'))
        saveAction.setShortcut('Ctrl+S')
        restartAction = QAction(self.tr('restart'), self, triggered=self.slotRestartAria2)
        restartAction.setStatusTip(self.tr('restartAria2Tip'))
        showAction = QAction(self.tr('show'), self, triggered=self.show)
        showAction.setShortcut('Ctrl+R')
        hideAction = QAction(self.tr('hide'), self, triggered=self.hide)
        hideAction.setShortcut('Ctrl+W')
        aboutAction = QAction(self.tr('about'), self, triggered=self.slotAbout)
        quitAction = QAction(self.tr('quit'), self, triggered=self.slotQuit)
        quitAction.setShortcut('Ctrl+Q')
        self.menuActions.update(
            saveSession=saveAction,
            restart=restartAction,
            show=showAction,
            hide=hideAction,
            about=aboutAction,
            quit=quitAction,
        )
        self.moreMenu = QMenu(self)
        self.moreMenu.addAction(saveAction)
        self.moreMenu.addAction(restartAction)
        self.moreMenu.addSeparator()
        self.moreMenu.addAction(showAction)
        self.moreMenu.addAction(hideAction)
        self.moreMenu.addSeparator()
        self.moreMenu.addAction(aboutAction)
        self.moreMenu.addAction(quitAction)


    def refreshActionIcons(self):
        """Apply one icon language to command, menu, tray, and navigation."""
        primaryColor = self.palette().color(QPalette.ColorRole.HighlightedText)
        buttonIcons = (
            ('addBtn', 'add', 16, primaryColor),
            ('unpauseAllBtn', 'play', 15, None),
            ('pauseAllBtn', 'pause', 15, None),
            ('moreBtn', 'menu', 16, None),
        )
        for attribute, iconName, size, color in buttonIcons:
            button = getattr(self, attribute, None)
            if button is not None:
                button.setIcon(actionIcon(iconName, color=color, size=size))
                button.setIconSize(QSize(size, size))

        menuIcons = {
            'saveSession': 'save',
            'restart': 'restart',
            'show': 'show',
            'hide': 'hide',
            'about': 'info',
            'quit': 'quit',
        }
        for key, iconName in menuIcons.items():
            action = getattr(self, 'menuActions', {}).get(key)
            if action is not None:
                action.setIcon(actionIcon(iconName, size=18))

        trayIcons = {
            'showMain': 'show',
            'new': 'add',
            'about': 'info',
            'trayQuit': 'quit',
        }
        for key, iconName in trayIcons.items():
            action = getattr(self, 'trayActions', {}).get(key)
            if action is not None:
                action.setIcon(actionIcon(iconName, size=18))

        self.refreshNavigationIcons()


    def refreshNavigationIcons(self):
        if not hasattr(self, 'tabDownloading'):
            return
        normalColor = self.palette().color(
            QPalette.ColorRole.PlaceholderText)
        selectedColor = self.palette().color(
            QPalette.ColorRole.Highlight)
        items = (
            (self.tabDownloading, 'download', 32),
            (self.tabDownloaded, 'completed', 32),
            (self.tabSetting, 'settings', 28),
        )
        for button, iconName, size in items:
            color = selectedColor if button.isChecked() else normalColor
            button.setIcon(actionIcon(iconName, color=color, size=size))
            button.setIconSize(QSize(size, size))
    def createTrayIcon(self) -> None:
        showWindowAction = QAction(self.tr('showMain'), self)
        newAction = QAction(self.tr('new'), self)
        aboutInfoAction = QAction(self.tr('about'), self)
        quitAction = QAction(self.tr('trayQuit'), self)
        self.trayMenu = QMenu()
        self.trayMenu.addAction(showWindowAction)
        self.trayMenu.addAction(newAction)
        self.trayMenu.addSeparator()
        self.trayMenu.addAction(aboutInfoAction)
        self.trayMenu.addAction(quitAction)
        self.connectTrayAction(showWindowAction, self.slotShowWindow)
        self.connectTrayAction(newAction, self.slotAdd)
        self.connectTrayAction(aboutInfoAction, self.slotAbout)
        self.connectTrayAction(quitAction, self.requestTrayQuit)
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setContextMenu(self.trayMenu)
        self.trayIcon.setToolTip('Ashore')
        self.applyTrayIconStyle(self.trayIconStyle)
        self.notificationManager = NotificationManager(
            self.trayIcon, self)
        self.notificationManager.activated.connect(
            self.slotNotificationClicked)
        self.trayActions = {'showMain': showWindowAction, 'new': newAction,
                            'about': aboutInfoAction, 'trayQuit': quitAction}

    def connectTrayAction(self, action, callback):
        action.triggered.connect(
            lambda _checked=False, callback=callback: self.deferTrayAction(callback))

    def deferTrayAction(self, callback):
        """Run a tray action after its popup closes."""
        self.trayMenu.close()
        QTimer.singleShot(0, callback)

    def applyTrayIconStyle(self, style):
        source = QPixmap(self.resourcePath + 'static/icon/functionIcons/trayIcon.png')
        if style == 'gray' and not source.isNull():
            grayIcon = QPixmap(source.size())
            grayIcon.fill(Qt.GlobalColor.transparent)
            painter = QPainter(grayIcon)
            painter.drawPixmap(0, 0, source)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(grayIcon.rect(), TRAY_GRAY)
            painter.end()
            self.trayIcon.setIcon(QIcon(grayIcon))
            style = 'gray'
        else:
            self.trayIcon.setIcon(QIcon(source))
        self.trayIconStyle = style

    def tr(self, key):
        return translate(self.language, key)



    def applyLanguage(self):
        for key, action in self.menuActions.items():
            action.setText(self.tr(key))
        for key, action in self.trayActions.items():
            action.setText(self.tr(key))
        self.addBtn.setText(self.tr('new'))
        self.unpauseAllBtn.setText(self.tr('startAll'))
        self.pauseAllBtn.setText(self.tr('pauseAll'))
        self.moreBtn.setToolTip(self.tr('more'))
        self.tabDownloading.setToolTip(self.tr('downloading'))
        self.tabDownloaded.setToolTip(self.tr('downloaded'))
        self.tabSetting.setToolTip(self.tr('settings'))
        self.menuActions['saveSession'].setStatusTip(
            self.tr('saveSessionTip'))
        self.menuActions['restart'].setStatusTip(
            self.tr('restartAria2Tip'))
        self.addBtn.setStatusTip(self.tr('newDownloadTip'))
        self.unpauseAllBtn.setStatusTip(self.tr('resumeAllTip'))
        self.pauseAllBtn.setStatusTip(self.tr('pauseAllTip'))
        self.downSpeedIcon.setToolTip(self.tr('downloadSpeed'))
        self.downSpeedLabel.setToolTip(self.tr('globalDownloadSpeed'))
        self.upSpeedIcon.setToolTip(self.tr('uploadSpeed'))
        self.upSpeedLabel.setToolTip(self.tr('globalUploadSpeed'))
        self.pageSetting.setLanguage(self.language)
        self.pageDownloading.setLanguage(self.language)
        self.pageDownloaded.setLanguage(self.language)
        self.refreshActionIcons()



    def createStatusStrip(self) -> None:
        self.statusStrip = QWidget()
        self.statusStrip.setProperty('statusStrip', True)
        self.statusStrip.setFixedHeight(30)

        self.statusMessageLabel = QLabel()
        self.statusMessageLabel.setProperty('statusMessage', True)

        self.aria2State = 'connecting'
        self.aria2StateDot = QLabel('●')
        self.aria2StateDot.setProperty('mainConnectionDot', True)
        self.aria2StateText = QLabel()
        self.aria2StateText.setProperty('statusMetricText', True)

        self.aria2StateWidget = QWidget(self.statusStrip)
        aria2Layout = QHBoxLayout(self.aria2StateWidget)
        aria2Layout.setContentsMargins(0, 0, 2, 0)
        aria2Layout.setSpacing(4)
        aria2Layout.addWidget(self.aria2StateDot)
        aria2Layout.addWidget(self.aria2StateText)
        self.setMainAria2State('connecting')

        self.downSpeedIcon = QLabel()
        self.downSpeedIcon.setFixedSize(20, 20)
        self.downSpeedIcon.setScaledContents(True)
        self.downSpeedIcon.setPixmap(QPixmap(
            self.resourcePath
            + 'static/icon/functionIcons/downloadSpeed.png'))
        self.downSpeedIcon.setToolTip(self.tr('downloadSpeed'))

        self.downSpeedLabel = QLabel('0B/s')
        self.downSpeedLabel.setProperty('statusMetricText', True)
        self.downSpeedLabel.setMinimumWidth(80)
        self.downSpeedLabel.setToolTip(self.tr('globalDownloadSpeed'))

        self.upSpeedIcon = QLabel()
        self.upSpeedIcon.setFixedSize(20, 20)
        self.upSpeedIcon.setScaledContents(True)
        self.upSpeedIcon.setPixmap(QPixmap(
            self.resourcePath
            + 'static/icon/functionIcons/uploadSpeed.png'))
        self.upSpeedIcon.setToolTip(self.tr('uploadSpeed'))

        self.upSpeedLabel = QLabel('0B/s')
        self.upSpeedLabel.setProperty('statusMetricText', True)
        self.upSpeedLabel.setMinimumWidth(80)
        self.upSpeedLabel.setToolTip(self.tr('globalUploadSpeed'))

        layout = QHBoxLayout(self.statusStrip)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(4)
        layout.addWidget(self.statusMessageLabel, 1)
        layout.addWidget(self.aria2StateWidget)
        layout.addWidget(self.downSpeedIcon)
        layout.addWidget(self.downSpeedLabel)
        layout.addWidget(self.upSpeedIcon)
        layout.addWidget(self.upSpeedLabel)

        self.aria2StateWidget.setVisible(self.showAria2Status)

        self.statusMessageTimer = QTimer(self.statusStrip)
        self.statusMessageTimer.setSingleShot(True)
        self.statusMessageTimer.timeout.connect(
            self.statusMessageLabel.clear)

    def setMainAria2State(self, state):
        if state not in ('connected', 'disconnected', 'connecting'):
            state = 'connecting'
        self.aria2State = state
        textKey = {
            'connected': 'connected',
            'disconnected': 'disconnected',
            'connecting': 'connecting',
        }[state]
        self.aria2StateText.setText(f'aria2 {self.tr(textKey)}')

        colors = {
            'connected': QColor('#69ad78'),
            'disconnected': QColor('#d46b6b'),
            'connecting': self.palette().color(
                QPalette.ColorRole.PlaceholderText),
        }
        palette = self.aria2StateDot.palette()
        palette.setColor(
            QPalette.ColorRole.WindowText, colors[state])
        self.aria2StateDot.setPalette(palette)

    def initUI(self) -> None:
        self.setWindowTitle('Ashore')
        self.setWindowIcon(
            QIcon(self.resourcePath + 'static/icon/functionIcons/appIcon.png'))
        self.createCommandActions()

        self.addBtn = QPushButton(self.tr('new'))
        self.addBtn.setToolTip(self.tr('new'))
        self.addBtn.setStatusTip(self.tr('newDownloadTip'))
        self.addBtn.setShortcut('Ctrl+N')
        self.addBtn.setProperty('commandPrimary', True)

        self.unpauseAllBtn = QPushButton(self.tr('startAll'))
        self.unpauseAllBtn.setToolTip(self.tr('startAll'))
        self.unpauseAllBtn.setStatusTip(self.tr('resumeAllTip'))
        self.unpauseAllBtn.setProperty('commandSecondary', True)

        self.pauseAllBtn = QPushButton(self.tr('pauseAll'))
        self.pauseAllBtn.setToolTip(self.tr('pauseAll'))
        self.pauseAllBtn.setStatusTip(self.tr('pauseAllTip'))
        self.pauseAllBtn.setProperty('commandSecondary', True)

        self.moreBtn = QPushButton()
        self.moreBtn.setToolTip(self.tr('more'))
        self.moreBtn.setProperty('overflowButton', True)
        self.moreBtn.setMenu(self.moreMenu)

        self.titleBar = TitleBar(
            self,
            (self.addBtn, self.unpauseAllBtn, self.pauseAllBtn),
            self.moreBtn,
        )

        self.tabDownloading = QPushButton()
        self.tabDownloaded = QPushButton()
        self.tabSetting = QPushButton()
        self.tabSetting.setShortcut('Ctrl+,')

        self.navigationTabs = QButtonGroup(self)
        self.navigationTabs.setExclusive(True)
        for button in (
                self.tabDownloading, self.tabDownloaded, self.tabSetting):
            button.setCheckable(True)
            button.setProperty('navigationTab', True)
            button.setFixedHeight(52)
            self.navigationTabs.addButton(button)

        self.tabDownloading.setChecked(True)
        self.tabDownloading.setToolTip(self.tr('downloading'))
        self.tabDownloaded.setToolTip(self.tr('downloaded'))
        self.tabSetting.setToolTip(self.tr('settings'))

        self.navigationRail = QWidget()
        self.navigationRail.setProperty('navigationRail', True)
        self.navigationRail.setFixedWidth(46)
        navigationLayout = QVBoxLayout(self.navigationRail)
        navigationLayout.setContentsMargins(4, 0, 0, 0)
        navigationLayout.setSpacing(4)
        navigationLayout.addWidget(self.tabDownloading)
        navigationLayout.addWidget(self.tabDownloaded)
        navigationLayout.addStretch(1)
        navigationLayout.addWidget(self.tabSetting)

        self.pageDownloading = Page(self.language)
        self.pageDownloaded = Page(self.language)
        self.pageStack = QStackedWidget()
        self.pageStack.setProperty('pageStack', True)
        self.pageStack.addWidget(self.pageDownloading)
        self.pageStack.addWidget(self.pageDownloaded)
        self.pageStack.addWidget(self.pageSetting)

        self.pageSurface = QWidget()
        self.pageSurface.setProperty('pageSurface', True)
        pageSurfaceLayout = QVBoxLayout(self.pageSurface)
        pageSurfaceLayout.setContentsMargins(0, 0, 0, 0)
        pageSurfaceLayout.setSpacing(0)
        pageSurfaceLayout.addWidget(self.pageStack)

        bodyWidget = QWidget()
        bodyWidget.setProperty('contentBody', True)
        bodyLayout = QHBoxLayout(bodyWidget)
        bodyLayout.setContentsMargins(0, 0, 12, 0)
        bodyLayout.setSpacing(0)
        bodyLayout.addWidget(self.navigationRail)
        bodyLayout.addWidget(self.pageSurface, 1)

        self.createStatusStrip()

        mainWidget = QWidget()
        mainWidget.setObjectName('mainRoot')

        self.windowSurface = QWidget()
        self.windowSurface.setProperty('windowSurface', True)
        surfaceLayout = QVBoxLayout(self.windowSurface)
        surfaceLayout.setContentsMargins(0, 0, 0, 0)
        surfaceLayout.setSpacing(0)
        surfaceLayout.addWidget(self.titleBar)
        surfaceLayout.addSpacing(4)
        surfaceLayout.addWidget(bodyWidget, 1)
        surfaceLayout.addSpacing(8)
        surfaceLayout.addWidget(self.statusStrip)

        mainLayout = QVBoxLayout(mainWidget)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        mainLayout.addWidget(self.windowSurface)
        self.setCentralWidget(mainWidget)
        self.syncWindowSurfaceState()

        self.setMinimumSize(920, 520)
        self.createTrayIcon()
        self.refreshActionIcons()

    def connectSignals(self) -> None:
        self.addBtn.clicked.connect(self.slotAdd)
        self.unpauseAllBtn.clicked.connect(self.slotUnpauseAll)
        self.pauseAllBtn.clicked.connect(self.slotPauseAll)
        self.tabDownloading.clicked.connect(self.showDownloading)
        self.tabDownloaded.clicked.connect(self.showCompleted)
        self.tabSetting.clicked.connect(self.showSettings)
        self.pageSetting.aria2ConfigChanged.connect(self.applyAria2Config)
        self.pageSetting.ashoreConfigChanged.connect(self.applyAshoreConfig)
        self.pageSetting.trackerRuntimeChanged.connect(self.slotApplyTracker)
        self.pageSetting.themePreview.connect(self.themeManager.apply)
        self.pageDownloading.sectionAdded.connect(self.connectSection)
        self.pageDownloaded.sectionAdded.connect(self.connectSection)

    def updatePage(self, snapshot: dict) -> None:
        missions = snapshot['missions']
        globalStatus = snapshot['globalStatus']
        if 'ResultError' in globalStatus:
            self.setMainAria2State('disconnected')
            self.aria2StateWidget.setToolTip(
                str(globalStatus['ResultError']))
            self.downSpeedLabel.setText('—')
            self.upSpeedLabel.setText('—')
            self.updateConnection('disconnected')
            return
        if 'ResultError' in missions:
            self.setMainAria2State('disconnected')
            self.aria2StateWidget.setToolTip(
                str(missions['ResultError']))
            return
        self.setMainAria2State('connected')
        self.aria2Version = snapshot.get('aria2Version') or self.aria2Version
        self.updateConnection('connected')
        self.pageDownloading.updateSections({status: missions[status] for status in ('active', 'waiting', 'paused')})
        self.pageDownloaded.updateSections({status: missions[status] for status in ('completed', 'error')})
        self.downSpeedLabel.setText(formatSpeed(globalStatus['downloadSpeed']))
        self.upSpeedLabel.setText(formatSpeed(globalStatus['uploadSpeed']))
        current = {gid: status for status, group in missions.items() for gid in group}
        self.notifiedDownloads.intersection_update({(gid, status) for gid in current for status in ('completed', 'error')})
        if self.knownStatuses is not None:
            for gid, status in current.items():
                previous = self.knownStatuses.get(gid)
                event = self.pendingNotifications.get(gid)
                complete = status == 'completed' and (previous in ('active', 'waiting', 'paused') or event == 'aria2.onDownloadComplete')
                btComplete = event == 'aria2.onBtDownloadComplete' and status == 'active'
                failed = status == 'error' and (previous in ('active', 'waiting', 'paused') or event == 'aria2.onDownloadError')
                outcome = 'error' if failed else 'completed' if complete or btComplete else None
                if outcome and (gid, outcome) not in self.notifiedDownloads:
                    name = missions[status][gid]['filename']
                    self.notifyDownload(gid, name, outcome)
                    self.notifiedDownloads.add((gid, outcome))
        self.knownStatuses = current
        self.pendingNotifications.clear()

    def connectSection(self, item):
        item.actionRequested.connect(self.slotTaskAction)
        item.openFolderRequested.connect(self.slotOpenFolder)
        item.copyUrlRequested.connect(self.slotCopyUrl)
        item.removeRequested.connect(self.slotRemoveTask)

    def slotAria2Notification(self, method, gid):
        if method in ('aria2.onDownloadComplete', 'aria2.onBtDownloadComplete', 'aria2.onDownloadError'):
            self.pendingNotifications[gid] = method
        self.aria2Poller.poll()

    def slotApplyTracker(self, options):
        result = self.aria2Client.setGlobalConfig(options)
        if 'ResultError' in result:
            self.showStatus(self.tr('trackerApplyDeferred').format(
                error=result['ResultError']))

    def slotWebSocketStateChanged(self, state):
        self.websocketState = state
        self.updateConnection(
            'connected' if self.aria2Version else 'waitingCheck')

    def updateConnection(self, httpState):
        self.pendingConnectionState = httpState
        if not self.hasPainted:
            return
        self.flushConnectionStatus()

    def flushConnectionStatus(self):
        httpState = self.pendingConnectionState
        websocketState = getattr(
            self, 'websocketState', 'unavailable')
        websocketKey = {
            'unavailable': 'unavailable',
            'connecting': 'connecting',
            'connected': 'connected',
            'disconnected': 'retrying',
            'stopped': 'stopped',
        }.get(websocketState, 'unknown')
        httpText = self.tr(httpState)
        websocketText = self.tr(websocketKey)
        endpoint = f'http://127.0.0.1:{self.aria2Client.rpcPort}/jsonrpc'
        self.aria2StateWidget.setToolTip(
            f'HTTP: {httpText}\nWebSocket: {websocketText}\n{endpoint}')
        self.pageSetting.setConnectionStatus(
            httpState, websocketState, self.aria2Version)


    def notifyDownload(self, gid, name, status):
        self.notificationTarget = gid
        title = self.tr(
            'downloadComplete' if status == 'completed' else 'downloadFailed')
        if not self.notificationManager.show(gid, title, name):
            self.showStatus(f'{title}：{name}')

    def slotNotificationClicked(self, gid=None):
        self.slotShowWindow()
        gid = gid or self.notificationTarget
        if not gid:
            return
        if self.pageDownloaded.focusSection(gid):
            self.showCompleted()
        elif self.pageDownloading.focusSection(gid):
            self.showDownloading()
    def showDownloading(self) -> None:
        self.tabDownloading.setChecked(True)
        self.pageStack.setCurrentIndex(0)
        self.refreshNavigationIcons()

    def showCompleted(self) -> None:
        self.tabDownloaded.setChecked(True)
        self.pageStack.setCurrentIndex(1)
        self.refreshNavigationIcons()

    def showSettings(self) -> None:
        config = self.aria2Client.getGlobalConfig()
        if 'ResultError' in config:
            self.showStatus(
                'aria2 未连接，设置页显示本地配置：'
                + str(config['ResultError']))
            config = self.pageSetting.readAria2Config()
        self.tabSetting.setChecked(True)
        self.pageSetting.loadSettings(config)
        self.pageStack.setCurrentIndex(2)
        self.refreshNavigationIcons()
    def offerDownloadMigration(self) -> None:
        if self.pageSetting.ashoreConfig.get('legacy_download_path_handled'):
            return
        migration = legacyDownloadDirectoryMigration(self.pageSetting.aria2ConfPath)
        if migration is None:
            return
        oldPath, newPath = migration
        answer = QMessageBox.question(
            self,
            '更新默认下载目录',
            self.tr('migrationQuestion').format(
                oldPath=oldPath, newPath=newPath),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if answer == QMessageBox.StandardButton.Yes:
            if self.pageSetting.saveAria2Conf({'dir': str(newPath)}) == 0:
                self.pageSetting.pathLineEdit.setText(str(newPath))
                result = self.aria2Client.setGlobalConfig({'dir': str(newPath)})
                if isinstance(result, dict) and 'ResultError' in result:
                    self.showStatus(self.tr('migrationApplyDeferred').format(
                        error=result['ResultError']))
            else:
                QMessageBox.warning(
                    self, self.tr('updateFailedTitle'),
                    self.tr('configWriteFailed'))
                return
        self.pageSetting.saveAshoreConf({'legacy_download_path_handled': 'true'})



    def addNew(self, urlList: list | None = None) -> None:
        """Open the unified confirmation dialog for manual or external input."""
        config = self.aria2Client.getGlobalConfig()
        if 'ResultError' in config:
            self.showStatus(config['ResultError'])
            return
        form = AddNewDialog(
            config['dir'], urlList, self, language=self.language)
        form.submitted.connect(self.addUrls)
        form.exec()
        self.aria2Poller.poll()
    def addUrls(self, request):
        result = self.aria2Client.addUrls(request)
        if 'ResultError' in result:
            QMessageBox.warning(
                self, self.tr('addTaskFailedTitle'),
                str(result['ResultError']))
    def slotAdd(self) -> None:
        """用户通过按钮触发的添加新任务,无参数
        """
        self.addNew()

    def slotUnpauseAll(self):
        unpauseAllResult = self.aria2Client.unpauseAll()
        if 'ResultError' in unpauseAllResult:
            self.showStatus(unpauseAllResult['ResultError'])

    def slotPauseAll(self):
        pauseAllResult = self.aria2Client.pauseAll()
        if 'ResultError' in pauseAllResult:
            self.showStatus(pauseAllResult['ResultError'])

    def slotAbout(self):
        aboutTitle = QLabel('<h1 style="Text-align: center;">Ashore</h1>')
        aboutTitle.setFixedHeight(30)
        infoLIcon = QLabel()
        infoLIcon.setPixmap(QPixmap(self.resourcePath + 'static/icon/functionIcons/appIcon.png'))
        infoLIcon.setScaledContents(True)
        infoLIcon.setFixedSize(180, 180)
        aria2Version = self.aria2Client.getAria2Version()
        aboutText = QLabel(
            self.tr('aboutDescription')
            + '<br>' + self.tr('aboutAuthor') + ': ' + APP_AUTHOR
            + '<br>' + self.tr('aboutProject')
            + ': <a href="' + PROJECT_URL + '">GitHub/Ashore</a>'
            + '<br>' + self.tr('aboutPythonVersion')
            + ': ' + platform.python_version()
            + '<br>' + self.tr('aboutAshoreVersion') + ': ' + APP_VERSION
            + '<br>' + self.tr('aboutAria2Version') + ': ' + aria2Version)
        aboutText.setOpenExternalLinks(True)
        aboutText.setFixedWidth(300)
        aboutText.setMargin(30)
        aboutLayout = QHBoxLayout()
        aboutLayout.addWidget(infoLIcon)
        aboutLayout.addWidget(aboutText)
        aboutLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        aboutInfoLayout = QVBoxLayout()
        aboutInfoLayout.addWidget(aboutTitle)
        aboutInfoLayout.addLayout(aboutLayout)
        aboutInfoLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.aboutInfo = QWidget()
        self.aboutInfo.setFixedSize(600, 320)
        self.aboutInfo.setLayout(aboutInfoLayout)
        self.aboutInfo.show()


    def slotShowWindow(self):
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        handle = self.windowHandle()
        if handle is not None:
            handle.requestActivate()
    def requestTrayQuit(self):
        if self.quitting or self.exitWindow is not None:
            return
        iconPath = self.resourcePath + 'static/icon/functionIcons/appIcon.png'
        self.exitWindow = ExitWindow(iconPath, self.tr('exiting'))
        self.exitWindow.ready.connect(self.slotQuit)
        self.exitWindow.showActive()

    def slotSaveSession(self):
        saveResult = self.aria2Client.saveSession()
        if 'ResultError' in saveResult:
            self.showStatus(saveResult['ResultError'])

    def slotQuit(self):
        if self.quitting:
            return
        self.quitting = True
        self.aria2Poller.timer.stop()
        self.aria2Events.stop()
        self.hide()
        self.trayIcon.hide()
        self.shutdown = Aria2Shutdown(
            self.aria2Service, self.aria2Poller, QApplication.instance())
        self.shutdown.failed.connect(
            lambda message: print(
                f'Ashore shutdown cleanup failed: {message}', file=sys.stderr))
        self.shutdown.finished.connect(QApplication.instance().quit)
        self.shutdown.start()

    def slotRestartAria2(self):
        self.aria2Poller.timer.stop()
        self.aria2Poller.wait()
        try:
            self.aria2Service.restart()
        except RuntimeError as exc:
            QMessageBox.warning(
                self, self.tr('restartAria2FailedTitle'), str(exc))
        finally:
            self.aria2Events.setPort(self.aria2Client.rpcPort)
            self.aria2Poller.timer.start()
            self.aria2Poller.poll()


    def slotTaskAction(self, gid: str, action: str) -> None:
        if action == 'pause':
            self.aria2Client.pause(gid)
        elif action == 'unpause':
            self.aria2Client.unpause(gid)
        elif action == 'open-file':
            result = self.aria2Client.getFilePath(gid)
            if 'ResultError' in result:
                self.showStatus(result['ResultError'])
            else:
                QDesktopServices.openUrl(
                    QUrl.fromLocalFile(result['filePath']))
        elif action == 'open-folder':
            self.slotOpenFolder(gid)
        elif action == 'retry':
            self.aria2Client.retry(gid)
        self.aria2Poller.poll()
    def slotOpenFolder(self, gid: str) -> None:
        mission = self.aria2Client.getMission(gid)
        if 'ResultError' in mission:
            self.showStatus(mission['ResultError'])
            return
        openResult = revealDownloadedFile(mission)
        if 'dir' in openResult:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(openResult['dir']))

    def slotCopyUrl(self, gid: str) -> None:
        urlResult = self.aria2Client.getUrl(gid)
        if 'ResultError' in urlResult:
            self.showStatus(urlResult['ResultError'])
        else:
            clipboard = QApplication.clipboard()
            clipboard.setText(urlResult['url'])
            self.showStatus(self.tr('copiedToClipboard'))


    def slotRemoveTask(self, data: tuple) -> None:
        gid, deleteFiles = data
        if gid in self.removalWorkers:
            return
        worker = Aria2Removal(
            self.aria2Client, gid, deleteFiles, self)
        self.removalWorkers[gid] = worker
        worker.resultReady.connect(self.finishRemoveTask)
        worker.finished.connect(
            lambda gid=gid: self.removalWorkers.pop(gid, None))
        worker.start()

    def finishRemoveTask(self, gid, result):
        if 'ResultError' in result:
            self.showStatus(str(result['ResultError']))
        else:
            self.showStatus(self.tr('deleteSuccess'))
        self.aria2Poller.poll()
    def applyAria2Config(self, conf: dict) -> None:
        if 'ResultError' in conf:
            result = conf
        else:
            runtime = conf.get('runtime', conf)
            result = self.aria2Client.setGlobalConfig(runtime) if runtime else {}
            if 'ResultError' not in result and conf.get('rpcChanged'):
                try:
                    self.aria2Poller.timer.stop()
                    self.aria2Poller.wait()
                    self.aria2Service.restart()
                    self.aria2Events.setPort(self.aria2Client.rpcPort)
                    self.aria2Version = ''
                    self.aria2Poller.version = ''
                except RuntimeError as exc:
                    result = {'ResultError': self.tr(
                        'manualRestartRequired').format(error=exc)}
                finally:
                    self.aria2Poller.timer.start()
                    self.aria2Poller.poll()
        self.aria2ConfigError = result.get('ResultError') if isinstance(result, dict) else str(result)


    def applyAshoreConfig(self, conf: dict) -> None:
        self.aria2Service.quitWithAshore = conf['quit_with_aria2'] == 'true'
        self.aria2Poller.timer.setInterval(
            max(500, int(conf['update_interval'])))

        configuredLanguage = resolveLanguage(conf.get('language'))
        if configuredLanguage != self.language:
            self.language = configuredLanguage
            self.applyLanguage()

        if conf.get('tray_icon_style'):
            self.applyTrayIconStyle(conf['tray_icon_style'])

        if 'show_aria2_status' in conf:
            value = conf['show_aria2_status']
            self.showAria2Status = boolValue(value)
            self.aria2StateWidget.setVisible(self.showAria2Status)

        if conf.get('theme_mode'):
            self.themeManager.apply(
                conf['theme_mode'], conf.get('accent_color'))

        if getattr(self, 'aria2ConfigError', None):
            self.showStatus(
                '配置已保存，但运行中 aria2 未能应用设置：'
                + str(self.aria2ConfigError))
        else:
            self.showStatus(conf['isSaved'])

    def showStatus(self, data, end=None):
        if isinstance(data, int):
            message = ERROR_MESSAGES[data]
        else:
            message = str(data)

        self.statusMessageLabel.setText(message)
        self.statusMessageTimer.start(3000)

        if not self.isRelease and not isinstance(data, int):
            print(data, end=end)
