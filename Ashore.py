"""Ashore application entry point and main window."""

import platform
import signal
import sys

from PyQt6.QtCore import (
    QElapsedTimer,
    QEvent,
    QObject,
    QSize,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPainter, QPalette, QPixmap
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

from core.applicationInfo import APP_VERSION, configureApplication
from core.aria2Client import ERROR_MESSAGES
from core.aria2Events import Aria2Events
from core.aria2Service import Aria2Poller, Aria2Removal, Aria2Shutdown, Aria2Startup
from core.configStore import boolValue, readAshore, writeAshore
from core.formatters import formatSpeed
from core.singleInstance import SingleInstanceCoordinator
from interface.actionIcons import actionIcon
from interface.addNewDialog import AddNewDialog
from interface.languageManager import translate
from interface.page import Page
from interface.settingPage import SettingPage
from interface.startupWindow import ExitWindow, RecoveryWindow, StartupWindow
from interface.windowChrome import createWindowChrome
from interface.themeManager import TRAY_GRAY, ThemeManager
from paths import (
    CONFIG_DIR,
    RESOURCE_DIR,
    ensureConfig,
    legacyDownloadDirectoryMigration,
)


class Ashore(QMainWindow):
    firstPainted = pyqtSignal()


    def __init__(self, aria2Service, themeManager):
        super().__init__()
        self.windowChrome = createWindowChrome(self)
        self.windowChrome.install()
        self.hasPainted = False
        self.isRelease = bool(getattr(sys, 'frozen', False))
        self.resourcePath = str(RESOURCE_DIR) + '/'

        self.pageSetting = SettingPage()
        ashoreConfig = self.pageSetting.loadAshoreConfig()
        self.language = ashoreConfig.get('language', 'zh_CN')
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
        self.pendingConnectionStatus = '等待检测'

        self.initUI()
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


    def createCommandActions(self) -> None:
        """Create low-frequency actions for the command-bar overflow menu."""
        self.menuActions = {}
        saveAction = QAction(self.tr('saveSession'), self, triggered=self.slotSaveSession)
        saveAction.setStatusTip('保存下载任务')
        saveAction.setShortcut('Ctrl+S')
        restartAction = QAction(self.tr('restart'), self, triggered=self.slotRestartAria2)
        restartAction.setStatusTip('重新启动 Aria2，运行中的任务会短暂刷新')
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
    def createTrayIcon(self) -> None:   #设置菜单栏程序图标及功能
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
        self.trayIcon.messageClicked.connect(self.slotNotificationClicked)
        self.applyTrayIconStyle(self.trayIconStyle)
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
        self.downSpeedIcon.setToolTip('下载速度')

        self.downSpeedLabel = QLabel('0B/s')
        self.downSpeedLabel.setProperty('statusMetricText', True)
        self.downSpeedLabel.setMinimumWidth(80)
        self.downSpeedLabel.setToolTip('全局实时下载速度')

        self.upSpeedIcon = QLabel()
        self.upSpeedIcon.setFixedSize(20, 20)
        self.upSpeedIcon.setScaledContents(True)
        self.upSpeedIcon.setPixmap(QPixmap(
            self.resourcePath
            + 'static/icon/functionIcons/uploadSpeed.png'))
        self.upSpeedIcon.setToolTip('上传速度')

        self.upSpeedLabel = QLabel('0B/s')
        self.upSpeedLabel.setProperty('statusMetricText', True)
        self.upSpeedLabel.setMinimumWidth(80)
        self.upSpeedLabel.setToolTip('全局 BT / Magnet 上传速度')

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
        self.createCommandActions()

        self.addBtn = QPushButton(self.tr('new'))
        self.addBtn.setToolTip(self.tr('new'))
        self.addBtn.setStatusTip('新建下载任务')
        self.addBtn.setShortcut('Ctrl+N')
        self.addBtn.setProperty('commandPrimary', True)

        self.unpauseAllBtn = QPushButton(self.tr('startAll'))
        self.unpauseAllBtn.setToolTip(self.tr('startAll'))
        self.unpauseAllBtn.setStatusTip('恢复所有暂停的任务')
        self.unpauseAllBtn.setProperty('commandSecondary', True)

        self.pauseAllBtn = QPushButton(self.tr('pauseAll'))
        self.pauseAllBtn.setToolTip(self.tr('pauseAll'))
        self.pauseAllBtn.setStatusTip('暂停所有下载中的任务')
        self.pauseAllBtn.setProperty('commandSecondary', True)

        self.moreBtn = QPushButton()
        self.moreBtn.setToolTip(self.tr('more'))
        self.moreBtn.setProperty('overflowButton', True)
        self.moreBtn.setMenu(self.moreMenu)

        self.commandBar = QWidget()
        self.commandBar.setProperty('commandBar', True)
        self.commandBar.setFixedHeight(40)
        commandLayout = QHBoxLayout(self.commandBar)
        commandLayout.setContentsMargins(8, 5, 8, 5)
        commandLayout.setSpacing(4)
        commandLayout.addWidget(self.addBtn)
        commandLayout.addWidget(self.unpauseAllBtn)
        commandLayout.addWidget(self.pauseAllBtn)
        commandLayout.addStretch(1)
        commandLayout.addWidget(self.moreBtn)

        commandHost = QWidget()
        commandHostLayout = QHBoxLayout(commandHost)
        commandHostLayout.setContentsMargins(12, 0, 12, 10)
        commandHostLayout.addWidget(self.commandBar)

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
        self.pageStack.setProperty('pageSurface', True)
        self.pageStack.addWidget(self.pageDownloading)
        self.pageStack.addWidget(self.pageDownloaded)
        self.pageStack.addWidget(self.pageSetting)

        bodyWidget = QWidget()
        bodyWidget.setProperty('contentBody', True)
        bodyLayout = QHBoxLayout(bodyWidget)
        bodyLayout.setContentsMargins(0, 0, 12, 0)
        bodyLayout.setSpacing(0)
        bodyLayout.addWidget(self.navigationRail)
        bodyLayout.addWidget(self.pageStack, 1)

        self.createStatusStrip()

        self.setWindowTitle('Ashore')
        mainWidget = QWidget()
        mainWidget.setObjectName('mainRoot')

        mainLayout = QVBoxLayout(mainWidget)
        mainLayout.setContentsMargins(0, 10, 0, 0)
        mainLayout.setSpacing(0)
        mainLayout.addWidget(commandHost)
        mainLayout.addWidget(bodyWidget, 1)
        mainLayout.addSpacing(8)
        mainLayout.addWidget(self.statusStrip)
        self.setCentralWidget(mainWidget)

        self.setMinimumSize(920, 520)
        self.setWindowIcon(
            QIcon(self.resourcePath + 'static/icon/functionIcons/icon.png'))
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

    def updatePage(self, snapshot:dict) -> None:
        missions = snapshot['missions']
        globalStatus = snapshot['globalStatus']
        if 'ResultError' in globalStatus:
            self.setMainAria2State('disconnected')
            self.aria2StateWidget.setToolTip(
                str(globalStatus['ResultError']))
            self.downSpeedLabel.setText('—')
            self.upSpeedLabel.setText('—')
            self.updateConnection('未连接')
            return
        if 'ResultError' in missions:
            self.setMainAria2State('disconnected')
            self.aria2StateWidget.setToolTip(
                str(missions['ResultError']))
            return
        self.setMainAria2State('connected')
        self.aria2Version = snapshot.get('aria2Version') or self.aria2Version
        self.updateConnection('已连接')
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
            self.showStatus('Tracker 已保存，将在 aria2 下次启动时生效：' + str(result['ResultError']))

    def slotWebSocketStateChanged(self, state):
        self.websocketState = state
        self.updateConnection('已连接' if self.aria2Version else '等待检测')

    def updateConnection(self, httpStatus):
        self.pendingConnectionStatus = httpStatus
        if not self.hasPainted:
            return
        self.flushConnectionStatus()

    def flushConnectionStatus(self):
        httpStatus = self.pendingConnectionStatus
        websocketText = {
            'unavailable': '不可用',
            'connecting': '连接中',
            'connected': '已连接',
            'disconnected': '已断开，正在重试',
            'stopped': '已停止',
        }.get(getattr(self, 'websocketState', 'unavailable'), '未知')
        endpoint = f'http://127.0.0.1:{self.aria2Client.rpcPort}/jsonrpc'
        self.aria2StateWidget.setToolTip(
            f'HTTP：{httpStatus}\nWebSocket：{websocketText}\n{endpoint}')
        self.pageSetting.setConnectionStatus(
            httpStatus, websocketText, self.aria2Version)


    def notifyDownload(self, gid, name, status):
        self.notificationTarget = gid
        if (QSystemTrayIcon.isSystemTrayAvailable()
                and QSystemTrayIcon.supportsMessages()):
            title = '下载完成' if status == 'completed' else '下载失败'
            self.trayIcon.showMessage(title, name)

    def slotNotificationClicked(self):
        self.slotShowWindow()
        gid = self.notificationTarget
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
            f'检测到旧版默认下载目录：\n{oldPath}\n\n'
            f'系统当前提供的下载目录是：\n{newPath}\n\n是否切换？\n'
            '只有旧版默认值会触发此提示，用户自定义目录不会被覆盖。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if answer == QMessageBox.StandardButton.Yes:
            if self.pageSetting.saveAria2Conf({'dir': str(newPath)}) == 0:
                self.pageSetting.pathLineEdit.setText(str(newPath))
                result = self.aria2Client.setGlobalConfig({'dir': str(newPath)})
                if isinstance(result, dict) and 'ResultError' in result:
                    self.showStatus('目录已保存，运行中的 aria2 未能立即应用：' + str(result['ResultError']))
            else:
                QMessageBox.warning(self, '更新失败', '无法写入 aria2 配置文件。')
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
                self, '添加任务失败', str(result['ResultError']))
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
        infoLIcon.setPixmap(QPixmap(self.resourcePath + 'static/icon/functionIcons/icon0.png'))
        infoLIcon.setScaledContents(True)
        infoLIcon.setFixedSize(180, 180)
        aria2Version = self.aria2Client.getAria2Version()
        aboutText = QLabel('由 Python 编写的 aria2 可视化程序<br>作者: PPPPAN<br>项目地址: <a href="https://github.com/FatesEdge/Ashore">GitHub/Ashore</a><br>Python version: ' + platform.python_version() + '<br>Ashore version: ' + APP_VERSION + '<br>aria2 version: ' + aria2Version)
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
        iconPath = self.resourcePath + 'static/icon/functionIcons/icon0.png'
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
            lambda message: print(f'Ashore 退出清理失败：{message}', file=sys.stderr))
        self.shutdown.finished.connect(QApplication.instance().quit)
        self.shutdown.start()

    def slotRestartAria2(self):
        self.aria2Poller.timer.stop()
        self.aria2Poller.wait()
        try:
            self.aria2Service.restart()
        except RuntimeError as exc:
            QMessageBox.warning(self, '无法重启 aria2', str(exc))
        finally:
            self.aria2Events.setPort(self.aria2Client.rpcPort)
            self.aria2Poller.timer.start()
            self.aria2Poller.poll()


    def slotTaskAction(self, gid:str, action:str) -> None:
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
    def slotOpenFolder(self, gid:str) -> None:
        openResult = self.aria2Client.openFileDir(gid)
        if 'ResultError' in openResult:
            self.showStatus(openResult['ResultError'])
        elif 'dir' in openResult:
            #返回非空,含有目录地址，代表使用不同系统特色方法调用失败,使用通用办法
            QDesktopServices.openUrl(QUrl.fromLocalFile(openResult['dir']))

    def slotCopyUrl(self, gid:str) -> None:
        urlResult = self.aria2Client.getUrl(gid)
        if 'ResultError' in urlResult:
            self.showStatus(urlResult['ResultError'])
        else:
            clipboard = QApplication.clipboard()
            clipboard.setText(urlResult['url'])
            self.showStatus('已复制到剪贴板')


    def slotRemoveTask(self, data:tuple) -> None:
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
            self.showStatus('删除成功')
        self.aria2Poller.poll()
    def applyAria2Config(self, conf:dict) -> None:
        # 将setting页面的设置信息更新到运行的aria2程序中
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
                    result = {'ResultError': f'{exc} 配置已保存，请手动重启 aria2 后生效。'}
                finally:
                    self.aria2Poller.timer.start()
                    self.aria2Poller.poll()
        self.aria2ConfigError = result.get('ResultError') if isinstance(result, dict) else str(result)


    def applyAshoreConfig(self, conf:dict) -> None:
        self.aria2Service.quitWithAshore = conf['quit_with_aria2'] == 'true'
        self.aria2Poller.timer.setInterval(
            max(500, int(conf['update_interval'])))

        if conf.get('language') and conf['language'] != self.language:
            self.language = conf['language']
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


class AshoreApplication(QApplication):

    instanceMessage = pyqtSignal(list)

    def __init__(self, arguments):
        configureApplication()
        super().__init__(arguments)
        self.setQuitOnLastWindowClosed(False)
        self.pendingInstanceMessages = []
        self.instanceRoutingReady = False
        self.singleInstance = SingleInstanceCoordinator('Ashore', self)
        self.singleInstance.messageReceived.connect(
            self.routeInstanceMessage)
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

    def __init__(self, app, arguments):
        super().__init__(app)
        self.app = app
        self.arguments = arguments
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
            self.window = Ashore(service, self.themeManager)
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
            QTimer.singleShot(
                self.TRACKER_GRACE_MS, self.trackerFinished)
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
        language = self.settings.get('language', 'zh_CN')
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

if __name__ == '__main__':
    resourcePath = str(RESOURCE_DIR) + '/'
    app = AshoreApplication(sys.argv)
    if platform.system() == 'Darwin':
        app.setFont(QFont('Hiragino Sans GB'))  #防止mac系统上运行速度受阻，选用“冬青黑体简体中文”为默认字体
        app.setWindowIcon(QIcon(resourcePath + 'static/icon/functionIcons/icon.icns'))
    elif platform.system() == 'Linux' or platform.system() == 'Windows':
        app.setWindowIcon(QIcon(resourcePath + 'static/icon/functionIcons/icon0.png'))
    app.startupController = StartupController(app, sys.argv)
    app.startupController.start()
    signal.signal(signal.SIGINT, lambda *_: app.startupController.quit())
    signalTimer = QTimer()
    signalTimer.timeout.connect(lambda: None)
    signalTimer.start(250)
    sys.exit(app.exec())
