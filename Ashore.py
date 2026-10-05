"""Ashore application entry point and main window."""

import json
import os
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
from PyQt6.QtGui import QAction, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from core.aria2Client import ERROR_MESSAGES
from core.aria2Events import Aria2Events
from core.aria2Service import Aria2Poller, Aria2Shutdown, Aria2Startup
from core.configStore import boolValue, readAshore, writeAshore
from core.desktopIntegration import DesktopIntegration
from core.formatters import formatSpeed
from interface.addNewDialog import AddNewDialog
from interface.languageManager import translate
from interface.page import Page
from interface.settingPage import SettingPage
from interface.startupWindow import StartupWindow
from interface.statusBadge import setConnectionBadge
from interface.themeManager import TRAY_GRAY, ThemeManager
from paths import (
    CONFIG_DIR,
    RESOURCE_DIR,
    ensureConfig,
    legacyDownloadDirectoryMigration,
)

APP_VERSION = '0.7.66'


def configureApplication():
    """Set the stable desktop identity before Qt initializes its platform plugin."""
    QApplication.setApplicationVersion(APP_VERSION)
    QApplication.setOrganizationName('PanZK')
    QApplication.setApplicationName('Ashore')
    QApplication.setDesktopFileName('ashore')


class Ashore(QMainWindow):
    firstPainted = pyqtSignal()

    def __init__(self, aria2Service, themeManager):
        super().__init__()
        self.hasPainted = False
        self.isRelease = False
        self.resourcePath = str(RESOURCE_DIR) + '/'
        if getattr(sys, 'frozen', False):
            self.isRelease = True
        self.pageSetting = SettingPage()
        #获取ashore配置信息
        ashoreConfig = self.pageSetting.loadAshoreConfig()
        self.language = ashoreConfig.get('language', 'zh_CN')
        self.trayIconStyle = ashoreConfig.get('tray_icon_style', 'colorful')
        self.aria2Service = aria2Service
        self.aria2Service.quitWithAshore = ashoreConfig['quit_with_aria2']
        self.aria2Client = aria2Service.client
        self.aria2Poller = Aria2Poller(
            self.aria2Client, int(ashoreConfig['update_interval']), self)
        self.themeManager = themeManager
        self.desktopIntegration = DesktopIntegration(self)

        self.initUI()
        self.connectSignals()
        self.aria2Poller.updated.connect(self.updatePage)
        self.knownStatuses = None
        self.pendingNotifications = {}
        self.notifiedDownloads = set()
        self.aria2ConfigError = None
        self.quitting = False
        self.aria2Events = Aria2Events(self.aria2Client.rpcPort, self)
        self.aria2Events.notification.connect(self.slotAria2Notification)
        self.aria2Events.connectionStateChanged.connect(self.slotWebSocketStateChanged)
        self.websocketState = self.aria2Events.state
        self.aria2Version = ''
        self.updateConnection('等待检测')

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
            QTimer.singleShot(0, self.firstPainted.emit)

    def createMenuBar(self) -> None:
        menuBar = self.menuBar()
        self.menuActions = {}
        newAction = QAction(self.tr('new'),self, triggered=self.slotAdd)
        newAction.setStatusTip('新建下载任务')
        newAction.setShortcut('Ctrl+N')
        saveAction = QAction(self.tr('saveSession'),self, triggered=self.slotSaveSession)
        saveAction.setStatusTip('保存下载任务')
        saveAction.setShortcut('Ctrl+S')
        restartAction = QAction(self.tr('restart'),self, triggered=self.slotRestartAria2)
        restartAction.setStatusTip('重新启动Aria2,可能导致程序短暂卡顿')
        quitAction = QAction(self.tr('quit'),self, triggered=self.slotQuit)
        quitAction.setStatusTip('彻底退出程序')
        quitAction.setShortcut('Ctrl+Q')
        fileMenu = menuBar.addMenu(self.tr('file'))
        fileMenu.addAction(newAction)
        fileMenu.addAction(saveAction)
        fileMenu.addSeparator()
        fileMenu.addAction(restartAction)
        fileMenu.addAction(quitAction)
        unpauseAllAction = QAction(self.tr('startAll'),self, triggered=self.slotUnpauseAll)
        unpauseAllAction.setStatusTip('开始全部任务')
        pauseAllAction = QAction(self.tr('pauseAll'),self, triggered=self.slotPauseAll)
        pauseAllAction.setStatusTip('逐步暂停全部任务')
        editMenu = menuBar.addMenu(self.tr('edit'))
        editMenu.addAction(unpauseAllAction)
        editMenu.addAction(pauseAllAction)
        showAction = QAction(self.tr('show'),self, triggered=self.show)
        showAction.setShortcut('Ctrl+R')
        hideAction = QAction(self.tr('hide'),self, triggered=self.hide)
        hideAction.setStatusTip('退出当前应用')
        hideAction.setShortcut('Ctrl+W')
        windowMenu = menuBar.addMenu(self.tr('window'))
        windowMenu.addAction(showAction)
        windowMenu.addAction(hideAction)
        aboutInfoAction = QAction(self.tr('about'), self, triggered=self.slotAbout)
        aboutInfoAction.setStatusTip('关于Ashore')
        helpMenu = menuBar.addMenu(self.tr('help'))
        helpMenu.addAction(aboutInfoAction)
        self.menuActions.update(new=newAction, saveSession=saveAction, restart=restartAction,
                                quit=quitAction, startAll=unpauseAllAction, pauseAll=pauseAllAction,
                                show=showAction, hide=hideAction, about=aboutInfoAction)
        self.mainMenus = {'file': fileMenu, 'edit': editMenu, 'window': windowMenu, 'help': helpMenu}
        self.setMenuBar(menuBar)

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
        quitAction.triggered.connect(self.deferTrayQuit)
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setContextMenu(self.trayMenu)
        self.trayIcon.setToolTip('Ashore')
        self.applyTrayIconStyle(self.trayIconStyle)
        self.trayActions = {'showMain': showWindowAction, 'new': newAction,
                            'about': aboutInfoAction, 'trayQuit': quitAction}

    def connectTrayAction(self, action, callback):
        action.triggered.connect(
            lambda _checked=False, callback=callback: self.deferTrayAction(callback))

    def deferTrayAction(self, callback):
        """Run a non-destructive tray action after its popup closes."""
        self.trayMenu.close()
        QTimer.singleShot(0, callback)

    def deferTrayQuit(self):
        """Let the desktop acknowledge its tray action before process teardown."""
        self.trayMenu.close()
        self.desktopIntegration.afterTrayEvent(self.slotQuit)

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
        for key, menu in self.mainMenus.items():
            menu.setTitle(self.tr(key))
        for key, action in self.trayActions.items():
            action.setText(self.tr(key))
        self.tabDownloading.setToolTip(self.tr('downloading'))
        self.tabDownloaded.setToolTip(self.tr('downloaded'))
        self.tabSetting.setToolTip(self.tr('settings'))


    def createStatusBar(self) -> None:   #设置状态栏
        self.downSpeedIcon = QLabel('upSpeedIcon')
        self.downSpeedIcon.setFixedSize(20,20)
        self.downSpeedIcon.setScaledContents(True)
        self.downSpeedIcon.setPixmap(QPixmap(self.resourcePath + 'static/icon/functionIcons/downloadSpeed.png'))
        self.downSpeedIcon.setToolTip('下载速度')
        self.downSpeedIcon.setStatusTip('全局实时下载速度')
        self.downSpeedLabel = QLabel('下载速度')
        self.downSpeedLabel.setMinimumWidth(80)
        self.downSpeedLabel.setToolTip('下载速度')
        self.downSpeedLabel.setStatusTip('全局实时下载速度')
        self.upSpeedIcon = QLabel('upSpeedIcon')
        self.upSpeedIcon.setFixedSize(20,20)
        self.upSpeedIcon.setScaledContents(True)
        self.upSpeedIcon.setPixmap(QPixmap(self.resourcePath + 'static/icon/functionIcons/uploadSpeed.png'))
        self.upSpeedIcon.setToolTip('上传速度')
        self.upSpeedIcon.setStatusTip('全局BT、磁链上传速度')
        self.upSpeedLabel = QLabel('上传速度')
        self.upSpeedLabel.setMinimumWidth(80)
        self.upSpeedLabel.setToolTip('上传速度')
        self.upSpeedLabel.setStatusTip('全局BT、磁链上传速度')
        self.statusBar = QStatusBar()
        self.statusBar.setContentsMargins(0,1,10,2)
        self.aria2StateLabel = QLabel('aria2：连接中')
        setConnectionBadge(self.aria2StateLabel, 'aria2：连接中', False)
        self.statusBar.addPermanentWidget(self.aria2StateLabel)
        self.statusBar.addPermanentWidget(self.downSpeedIcon)
        self.statusBar.addPermanentWidget(self.downSpeedLabel)
        self.statusBar.addPermanentWidget(self.upSpeedIcon)
        self.statusBar.addPermanentWidget(self.upSpeedLabel)
        self.setStatusBar(self.statusBar)

    def initUI(self) -> None:
        self.tabDownloading = QPushButton(QIcon(self.resourcePath + 'static/icon/functionIcons/download.png'),'')
        self.tabDownloading.setFlat(True)
        self.tabDownloading.setIconSize(QSize(23,23))
        self.tabDownloading.setToolTip('下载中')
        self.tabDownloading.setStatusTip('显示所有下载、等待、暂停中的任务')
        self.tabDownloaded = QPushButton(QIcon(self.resourcePath + 'static/icon/functionIcons/completed.png'),'')
        self.tabDownloaded.setFlat(True)
        self.tabDownloaded.setIconSize(QSize(23,23))
        self.tabDownloaded.setToolTip('已完成')
        self.tabDownloaded.setStatusTip('显示所有已完成、错误的任务')
        self.tabSetting = QPushButton(QIcon(self.resourcePath + 'static/icon/functionIcons/setting.png'),'')
        self.tabSetting.setFlat(True)
        self.tabSetting.setIconSize(QSize(23,23))
        self.tabSetting.setToolTip('设置')
        self.tabSetting.setStatusTip('Ashore及aria2相关设置')
        self.tabSetting.setShortcut("Ctrl+,")
        self.navigationTabs = QButtonGroup(self)
        self.navigationTabs.setExclusive(True)
        for button in (self.tabDownloading, self.tabDownloaded, self.tabSetting):
            button.setCheckable(True)
            button.setProperty('navigationTab', True)
            button.setProperty('toolbarButton', True)
            self.navigationTabs.addButton(button)
        self.tabDownloading.setChecked(True)
        tabLayout = QVBoxLayout()
        tabLayout.addWidget(self.tabDownloading)
        tabLayout.addWidget(self.tabDownloaded)
        tabLayout.addStretch(10)
        tabLayout.addWidget(self.tabSetting)
        self.addBtn = QPushButton(QIcon(self.resourcePath + 'static/icon/functionIcons/add.png'),'')
        self.addBtn.setFlat(True)
        self.addBtn.setIconSize(QSize(20,20))
        self.addBtn.setToolTip('新建下载')
        self.addBtn.setStatusTip('新建下载任务')
        self.addBtn.setShortcut("Ctrl+N")
        self.unpauseAllBtn = QPushButton(QIcon(self.resourcePath + 'static/icon/functionIcons/play.png'),'')
        self.unpauseAllBtn.setFlat(True)
        self.unpauseAllBtn.setIconSize(QSize(20,20))
        self.unpauseAllBtn.setToolTip('开始全部')
        self.unpauseAllBtn.setStatusTip('恢复所有暂停的任务')
        self.pauseAllBtn = QPushButton(QIcon(self.resourcePath + 'static/icon/functionIcons/pause.png'),'')
        self.pauseAllBtn.setFlat(True)
        self.pauseAllBtn.setIconSize(QSize(20,20))
        self.pauseAllBtn.setToolTip('暂停全部')
        self.pauseAllBtn.setStatusTip('暂停所有下载中的任务')
        for button in (self.addBtn, self.unpauseAllBtn, self.pauseAllBtn):
            button.setProperty('toolbarButton', True)
        btnLayout = QHBoxLayout()
        btnLayout.addWidget(self.addBtn)
        btnLayout.addWidget(self.unpauseAllBtn)
        btnLayout.addWidget(self.pauseAllBtn)
        #添加弹簧
        btnLayout.addStretch(10)
        self.pageDownloading = Page()
        self.pageDownloaded = Page()
        self.pageStack = QStackedLayout()
        self.pageStack.addWidget(self.pageDownloading)
        self.pageStack.addWidget(self.pageDownloaded)
        self.pageStack.addWidget(self.pageSetting)
        pageLayout = QVBoxLayout()
        pageLayout.addLayout(btnLayout)
        pageLayout.addLayout(self.pageStack)
        mainLayout = QHBoxLayout()
        mainLayout.addLayout(tabLayout)
        mainLayout.addLayout(pageLayout)
        mainWidget = QWidget()
        mainWidget.setLayout(mainLayout)
        self.setCentralWidget(mainWidget)
        self.setMinimumSize(1000,520)
        #创建窗口标题
        self.setWindowTitle('Ashore')
        self.setWindowIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/icon.png'))
        self.createMenuBar()
        self.createStatusBar()
        self.createTrayIcon()

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
            setConnectionBadge(self.aria2StateLabel, 'aria2：未连接', False)
            self.aria2StateLabel.setToolTip(str(globalStatus['ResultError']))
            self.downSpeedLabel.setText('—')
            self.upSpeedLabel.setText('—')
            self.updateConnection('未连接')
            return
        if 'ResultError' in missions:
            setConnectionBadge(self.aria2StateLabel, 'aria2：查询失败', False)
            self.aria2StateLabel.setToolTip(str(missions['ResultError']))
            return
        setConnectionBadge(self.aria2StateLabel, 'aria2：已连接', True)
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
                    self.notifyDownload(name, outcome)
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
        websocketText = {
            'unavailable': '不可用',
            'connecting': '连接中',
            'connected': '已连接',
            'disconnected': '已断开，正在重试',
            'stopped': '已停止',
        }.get(getattr(self, 'websocketState', 'unavailable'), '未知')
        endpoint = f'http://127.0.0.1:{self.aria2Client.rpcPort}/jsonrpc'
        self.aria2StateLabel.setToolTip(
            f'HTTP：{httpStatus}\nWebSocket：{websocketText}\n{endpoint}')
        self.pageSetting.setConnectionStatus(httpStatus, websocketText, self.aria2Version)

    def notifyDownload(self, name, status):
        if QSystemTrayIcon.isSystemTrayAvailable() and QSystemTrayIcon.supportsMessages():
            title = '下载完成' if status == 'completed' else '下载失败'
            self.trayIcon.showMessage(title, name)

    def showDownloading(self) -> None:
        self.tabDownloading.setChecked(True)
        self.pageStack.setCurrentIndex(0)

    def showCompleted(self) -> None:
        self.tabDownloaded.setChecked(True)
        self.pageStack.setCurrentIndex(1)

    def showSettings(self) -> None:
        config = self.aria2Client.getGlobalConfig()
        if 'ResultError' in config:
            self.showStatus('aria2 未连接，设置页显示本地配置：' + str(config['ResultError']))
            config = self.pageSetting.readAria2Config()
        self.tabSetting.setChecked(True)
        self.pageSetting.loadSettings(config)
        self.pageStack.setCurrentIndex(2)

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
        """通过命令行参数或系统接口参数运行程序、添加新任务
        :param urlList: list类型的下载地址url
        """
        config = {'ResultError' : 0}
        config = self.aria2Client.getGlobalConfig()
        if 'ResultError' in config:
            self.showStatus(config['ResultError'])
            return
        else:
            form = AddNewDialog(config['dir'], urlList)
            form.submitted.connect(self.addUrls)
            form.show()
            form.exec()
            self.aria2Poller.poll()

    def addUrls(self, data):
        result = self.aria2Client.addUrls(data)
        if 'ResultError' in result:
            QMessageBox.warning(self, '添加任务失败', str(result['ResultError']))

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
        self.show()

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

    def slotTaskAction(self, data:tuple) -> None:
        gid = data[0]
        status = data[1]
        #根据section状态判定双击的作用是开始或暂停
        if status == 'active' or status == 'waiting' :
            self.aria2Client.pause(gid)
        elif status == 'paused':
            self.aria2Client.unpause(gid)
        elif status == 'completed':
            filePathResult = self.aria2Client.getFilePath(gid)
            if 'ResultError' in filePathResult:
                self.showStatus(filePathResult['ResultError'])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(filePathResult['filePath']))
        elif status == 'error':
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
        gid = data[0]
        delFile = data[1]
        result = self.aria2Client.removeMission(gid=gid, delFile=delFile)
        if 'ResultError' in result:
            self.showStatus(result['ResultError'])
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
        # 将setting页面的设置信息更新到运行的ashore程序中
        if conf['quit_with_aria2'] == 'false':
            self.aria2Service.quitWithAshore = False
        elif conf['quit_with_aria2'] == 'true':
            self.aria2Service.quitWithAshore = True
        self.aria2Poller.timer.setInterval(max(500, int(conf['update_interval'])))
        if conf.get('language') and conf['language'] != self.language:
            self.language = conf['language']
            self.applyLanguage()
        if conf.get('tray_icon_style'):
            self.applyTrayIconStyle(conf['tray_icon_style'])
        if conf.get('theme_mode'):
            self.themeManager.apply(conf['theme_mode'], conf.get('accent_color'))
        if getattr(self, 'aria2ConfigError', None):
            self.showStatus('配置已保存，但运行中 aria2 未能应用设置：' + str(self.aria2ConfigError))
        else:
            self.showStatus(conf['isSaved'])

    def showStatus(self, data, end=None):
        if isinstance(data, int):
            self.statusBar.showMessage(ERROR_MESSAGES[data], 3000)
        else:
            #将提示信息显示在状态栏中showMessage（‘提示信息’，显示时间（单位毫秒））
            self.statusBar.showMessage(data, 3000)
            if not self.isRelease:
                #当程序处于coding阶段时允许输出，当为release时禁止输出
                print(data, end=end)

class AshoreApplication(QApplication):

    fileOpenSignal = pyqtSignal(list)
    instanceMessage = pyqtSignal(list)

    def __init__(self, arguments):
        configureApplication()
        super().__init__(arguments)
        self.setQuitOnLastWindowClosed(False)

    def forwardToExisting(self, urls):
        name = 'Ashore-' + str(os.getuid() if hasattr(os, 'getuid') else os.environ.get('USERNAME', 'user'))
        socket = QLocalSocket(self)
        socket.connectToServer(name)
        if socket.waitForConnected(300):
            socket.write(json.dumps(urls).encode('utf-8'))
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            return True
        if socket.error() == QLocalSocket.LocalSocketError.UnsupportedSocketOperationError:
            return False
        if socket.error() not in (QLocalSocket.LocalSocketError.ServerNotFoundError,
                                  QLocalSocket.LocalSocketError.ConnectionRefusedError):
            raise RuntimeError('无法连接正在运行的 Ashore 实例')
        self.localServer = QLocalServer(self)
        QLocalServer.removeServer(name)
        if not self.localServer.listen(name):
            raise RuntimeError('无法建立 Ashore 单实例通信通道')
        self.localServer.newConnection.connect(self.receiveInstanceMessage)
        return False

    def receiveInstanceMessage(self):
        socket = self.localServer.nextPendingConnection()
        if not socket.bytesAvailable():
            socket.waitForReadyRead(1000)
        try:
            urls = json.loads(bytes(socket.readAll()).decode('utf-8'))
            self.instanceMessage.emit(urls)
        except (ValueError, UnicodeDecodeError):
            pass
        socket.disconnectFromServer()

    def event(self, event):
        if event.type() == QEvent.Type.FileOpen:    # 对请求进行判断
            self.fileOpenSignal.emit([event.url().toString()])
        return super().event(event)


class StartupController(QObject):
    MIN_VISIBLE_MS = 900
    TRACKER_GRACE_MS = 1000

    def __init__(self, app, arguments):
        super().__init__(app)
        self.app = app
        self.arguments = arguments
        self.window = None
        self.finished = False
        self.finishScheduled = False
        self.firstSnapshotReady = False
        self.trackerReady = False
        self.clock = QElapsedTimer()
        self.themeManager = ThemeManager(app, self)
        self.splash = StartupWindow(RESOURCE_DIR / 'static/img/cover.png')
        self.splash.firstPainted.connect(self.checkInstance)
        self.startup = None

    def start(self):
        self.clock.start()
        self.splash.show()

    def checkInstance(self):
        self.showStage('正在检查运行实例')
        try:
            if self.app.forwardToExisting(self.arguments[1:]):
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
            settings = readAshore(
                CONFIG_DIR / 'ashore.conf', RESOURCE_DIR / 'config/ashore.conf')
            if settings.get('tray_icon_style') == 'monochrome':
                settings['tray_icon_style'] = 'gray'
                writeAshore(CONFIG_DIR / 'ashore.conf', {'tray_icon_style': 'gray'})
            self.themeManager.apply(
                settings.get('theme_mode', 'system'),
                settings.get('accent_color', '#5d795f'))
        except (OSError, ValueError) as exc:
            self.fail(str(exc))
            return
        QTimer.singleShot(0, lambda: self.startAria2(settings))

    def startAria2(self, settings):
        self.startup = Aria2Startup(
            boolValue(settings.get('quit_with_aria2')), self)
        self.startup.statusChanged.connect(self.showStage)
        self.startup.ready.connect(self.buildWindow)
        self.startup.failed.connect(self.fail)
        self.startup.start()

    def buildWindow(self, service):
        self.showStage('正在准备主界面')
        QTimer.singleShot(0, lambda: self.createWindow(service))

    def createWindow(self, service):
        try:
            self.window = Ashore(service, self.themeManager)
        except (RuntimeError, OSError, ValueError) as exc:
            self.fail(str(exc))
            return
        self.app.fileOpenSignal.connect(self.window.addNew)
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

    def mainPainted(self):
        self.traceStage('主界面首帧已完成')
        QTimer.singleShot(0, self.finishRuntime)

    def finishRuntime(self):
        self.traceStage('正在注册系统托盘')
        self.window.showTray()
        self.traceStage('系统托盘已就绪')
        QTimer.singleShot(0, self.finishMigration)

    def finishMigration(self):
        self.traceStage('正在检查下载目录')
        self.window.offerDownloadMigration()
        self.traceStage('启动完成')

    def handleInstance(self, urls):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        if urls:
            self.window.addNew(urls)

    def showStage(self, message):
        self.splash.showStatus(message)
        self.traceStage(message)

    def traceStage(self, message):
        if os.environ.get('ASHORE_STARTUP_TRACE') == '1':
            print(f'[startup {self.clock.elapsed():4d} ms] {message}', flush=True)

    def fail(self, message):
        self.splash.close()
        QMessageBox.critical(None, 'Ashore 启动失败', message)
        self.app.quit()

    def quit(self):
        if self.window:
            self.window.slotQuit()
        else:
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
