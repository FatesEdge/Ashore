#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Time    :   2023/03/20 20:12:13
@File    :   Ashore.py
@Software:   VSCode
@Author  :   PPPPAN 
@Version :   0.7.66
@Contact :   for_freedom_x64@live.com
'''

import sys, os, platform, json, copy, signal
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QStackedLayout, QSplashScreen, QMenu, QLabel, QStatusBar, QSystemTrayIcon, QMessageBox
from PyQt6.QtGui import QIcon, QPixmap, QAction, QDesktopServices, QFont
from PyQt6.QtCore import QTimer, QSize, QEvent, QUrl, pyqtSignal, QObject, QThread, Qt
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from interface.page import Page
from core.aria2Operate import Aria2Operate
from interface.addNewDialog import AddNewDialog
from interface.settingPage import SettingPage
from paths import RESOURCE_DIR
from core.aria2Events import Aria2Events

DEFAULTPATH = os.path.expanduser('~/Downloads')
APP_VERSION = '0.7.66'
class Aria2Thread(Aria2Operate, QThread):

    updatedSignal = pyqtSignal(dict)

    def __init__(self, BASEPATH:str=None, QuitWithAria2:bool=False, UpdateInterval:int=2000):
        QThread.__init__(self)
        Aria2Operate.__init__(self, BASEPATH=BASEPATH, QuitWithAria2=QuitWithAria2)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(max(500, UpdateInterval))

    def poll(self):
        if not self.isRunning():
            self.start()

    def run(self):
        missions = self.getMissions()
        status = self.lastPollGlobalStatus
        self.updatedSignal.emit({'missions': copy.deepcopy(missions), 'globalStatus': dict(status)})

class Ashore(QMainWindow):
    def __init__(self):
        super().__init__()
        # Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
        #生成资源文件目录访问路径
        #上限2000个任务
        #说明： pyinstaller工具打包的可执行文件，运行时sys。frozen会被设置成True
        #      因此可以通过sys.frozen的值区分是开发环境还是打包后的生成环境
        #
        #      打包后的生产环境，资源文件都放在sys._MEIPASS目录下
        #      修改main.spec中的datas，
        #      如datas=[('res', 'res')]，意思是当前目录下的res目录加入目标exe中，在运行时放在零时文件的根目录下，名称为res
        self.isRelease = False
        self.BASEPATH = str(RESOURCE_DIR) + '/'
        # getattr 函数判断第一参数中是否含有第二参数这个属性：有则返回True，若没有：当第三参数为空时返回error，第三参数存在则返回第三参数
        if getattr(sys, 'frozen', False):
            self.isRelease = True
            #判断是否为发布状态，利用系统方法找到运行目录
            self.BASEPATH = sys._MEIPASS + '/'
        self.pageSetting = SettingPage()
        #获取ashore配置信息
        ashoreConfig = self.pageSetting.getAshoreConfig()
        self.aria2Operate = Aria2Thread(
            BASEPATH=self.BASEPATH,
            QuitWithAria2=ashoreConfig['quit_with_aria2'],
            UpdateInterval=int(ashoreConfig['update_interval'])
            )

        self.initUI()
        self.setConnect()
        self.aria2Operate.updatedSignal.connect(self.updatePage)
        self.knownStatuses = None
        self.pendingNotifications = {}
        self.notifiedDownloads = set()
        self.aria2ConfigError = None
        self.quitting = False
        self.aria2Events = Aria2Events(self.aria2Operate.rpc_port, self)
        self.aria2Events.notification.connect(self.slotAria2Notification)
        self.aria2Operate.poll()

    def createMenuBar(self) -> None:
        menuBar = self.menuBar()
        newAction = QAction('新建下载',self, triggered=self.slotClickBtnAddNew)
        newAction.setStatusTip('新建下载任务')
        newAction.setShortcut('Ctrl+N')
        saveAction = QAction('保存会话',self, triggered=self.slotSaveSession)
        saveAction.setStatusTip('保存下载任务')
        saveAction.setShortcut('Ctrl+S')
        restartAction = QAction('重启Aria2',self, triggered=self.slotRestartAria2)
        restartAction.setStatusTip('重新启动Aria2,可能导致程序短暂卡顿')
        quitAction = QAction('退出程序',self, triggered=self.slotQuit)
        quitAction.setStatusTip('彻底退出程序')
        quitAction.setShortcut('Ctrl+Q')
        fileMenu = menuBar.addMenu("文件")
        fileMenu.addAction(newAction)
        fileMenu.addAction(saveAction)
        fileMenu.addSeparator()
        fileMenu.addAction(restartAction)
        fileMenu.addAction(quitAction)
        unpauseAllAction = QAction('开始全部',self, triggered=self.slotUnpauseAll)
        unpauseAllAction.setStatusTip('开始全部任务')
        pauseAllAction = QAction('暂停全部',self, triggered=self.slotPauseAll)
        pauseAllAction.setStatusTip('逐步暂停全部任务')
        editMenu = menuBar.addMenu("编辑")
        editMenu.addAction(unpauseAllAction)
        editMenu.addAction(pauseAllAction)
        showAction = QAction('显示窗口',self, triggered=self.show)
        showAction.setShortcut('Ctrl+R')
        hideAction = QAction('关闭窗口',self, triggered=self.hide)
        hideAction.setStatusTip('退出当前应用')
        hideAction.setShortcut('Ctrl+W')
        windowMenu = menuBar.addMenu("窗口")
        windowMenu.addAction(showAction)
        windowMenu.addAction(hideAction)
        aboutInfoAction = QAction("关于Ashore", self, triggered=self.slotAbout)
        aboutInfoAction.setStatusTip('关于Ashore')
        helpMenu = menuBar.addMenu("帮助")
        helpMenu.addAction(aboutInfoAction)
        self.setMenuBar(menuBar)

    def createTrayIcon(self) -> None:   #设置菜单栏程序图标及功能
        showWindowAction = QAction("显示主窗口", self, triggered=self.slotShowWindow)
        newAction = QAction('新建下载',self, triggered=self.slotClickBtnAddNew)
        aboutInfoAction = QAction("关于Ashore", self, triggered=self.slotAbout)
        quitAction = QAction("退出", self, triggered=self.slotQuit)
        trayMenu = QMenu()
        trayMenu.addAction(showWindowAction)
        trayMenu.addAction(newAction)
        trayMenu.addSeparator()
        trayMenu.addAction(aboutInfoAction)
        trayMenu.addAction(quitAction)
        self.TrayIcon = QSystemTrayIcon(self)
        self.TrayIcon.setContextMenu(trayMenu)
        self.TrayIcon.setToolTip('Ashore')
        self.TrayIcon.setIcon(QIcon(self.BASEPATH + "static/icon/icon.funtion/trayIcon.png"))
        self.TrayIcon.show()


    def createStatusBar(self) -> None:   #设置状态栏
        self.downSpeedIcon = QLabel('upSpeedIcon')
        self.downSpeedIcon.setFixedSize(20,20)
        self.downSpeedIcon.setScaledContents(True)
        self.downSpeedIcon.setPixmap(QPixmap(self.BASEPATH + 'static/icon/icon.funtion/downloadSpeed.png'))
        self.downSpeedIcon.setToolTip('下载速度')
        self.downSpeedIcon.setStatusTip('全局实时下载速度')
        self.downSpeedLabel = QLabel('下载速度')
        self.downSpeedLabel.setMinimumWidth(80)
        self.downSpeedLabel.setToolTip('下载速度')
        self.downSpeedLabel.setStatusTip('全局实时下载速度')
        self.upSpeedIcon = QLabel('upSpeedIcon')
        self.upSpeedIcon.setFixedSize(20,20)
        self.upSpeedIcon.setScaledContents(True)
        self.upSpeedIcon.setPixmap(QPixmap(self.BASEPATH + 'static/icon/icon.funtion/uploadSpeed.png'))
        self.upSpeedIcon.setToolTip('上传速度')
        self.upSpeedIcon.setStatusTip('全局BT、磁链上传速度')
        self.upSpeedLabel = QLabel('上传速度')
        self.upSpeedLabel.setMinimumWidth(80)
        self.upSpeedLabel.setToolTip('上传速度')
        self.upSpeedLabel.setStatusTip('全局BT、磁链上传速度')
        self.statusBar = QStatusBar()
        self.statusBar.setContentsMargins(0,1,10,2)
        self.statusBar.addPermanentWidget(self.downSpeedIcon)
        self.statusBar.addPermanentWidget(self.downSpeedLabel)
        self.statusBar.addPermanentWidget(self.upSpeedIcon)
        self.statusBar.addPermanentWidget(self.upSpeedLabel)
        self.aria2StateLabel = QLabel('aria2：连接中')
        self.statusBar.addPermanentWidget(self.aria2StateLabel)
        self.setStatusBar(self.statusBar)

    def initUI(self) -> None:
        self.tabDownloading = QPushButton(QIcon(self.BASEPATH + 'static/icon/icon.funtion/download.png'),'')
        self.tabDownloading.setFlat(True)
        self.tabDownloading.setIconSize(QSize(23,23))
        self.tabDownloading.setToolTip('下载中')
        self.tabDownloading.setStatusTip('显示所有下载、等待、暂停中的任务')
        self.tabDownloading.setEnabled(False)
        self.tabDownloaded = QPushButton(QIcon(self.BASEPATH + 'static/icon/icon.funtion/completed.png'),'')
        self.tabDownloaded.setFlat(True)
        self.tabDownloaded.setIconSize(QSize(23,23))
        self.tabDownloaded.setToolTip('已完成')
        self.tabDownloaded.setStatusTip('显示所有已完成、错误的任务')
        self.tabSetting = QPushButton(QIcon(self.BASEPATH + 'static/icon/icon.funtion/setting.png'),'')
        self.tabSetting.setFlat(True)
        self.tabSetting.setIconSize(QSize(23,23))
        self.tabSetting.setToolTip('设置')
        self.tabSetting.setStatusTip('Ashore及aria2相关设置')
        self.tabSetting.setShortcut("Ctrl+,")
        tabLayout = QVBoxLayout()
        tabLayout.addWidget(self.tabDownloading)
        tabLayout.addWidget(self.tabDownloaded)
        tabLayout.addStretch(10)
        tabLayout.addWidget(self.tabSetting)
        self.addBtn = QPushButton(QIcon(self.BASEPATH + 'static/icon/icon.funtion/add.png'),'')
        self.addBtn.setFlat(True)
        self.addBtn.setIconSize(QSize(20,20))
        self.addBtn.setToolTip('新建下载')
        self.addBtn.setStatusTip('新建下载任务')
        self.addBtn.setShortcut("Ctrl+N")
        self.unpauseAllBtn = QPushButton(QIcon(self.BASEPATH + 'static/icon/icon.funtion/play.png'),'')
        self.unpauseAllBtn.setFlat(True)
        self.unpauseAllBtn.setIconSize(QSize(20,20))
        self.unpauseAllBtn.setToolTip('开始全部')
        self.unpauseAllBtn.setStatusTip('恢复所有暂停的任务')
        self.pauseAllBtn = QPushButton(QIcon(self.BASEPATH + 'static/icon/icon.funtion/pause.png'),'')
        self.pauseAllBtn.setFlat(True)
        self.pauseAllBtn.setIconSize(QSize(20,20))
        self.pauseAllBtn.setToolTip('暂停全部')
        self.pauseAllBtn.setStatusTip('暂停所有下载中的任务')
        btnLayout = QHBoxLayout()
        btnLayout.addWidget(self.addBtn)
        btnLayout.addWidget(self.unpauseAllBtn)
        btnLayout.addWidget(self.pauseAllBtn)
        #添加弹簧
        btnLayout.addStretch(10)
        self.pageDownloading = Page()
        self.pageDownloaded = Page()
        #pageSetting在程序初始运行时为加载配置已生成
        # self.pageSetting = SettingPage()
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
        # self.mainLayout.setMinimumSize(1000,500)
        self.setMinimumSize(1000,520)
        #创建窗口标题
        self.setWindowTitle('Ashore')
        self.setWindowIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/icon.png'))
        self.setStyleSheet('''
            Ashore QPushButton{width:40;height:40;border-radius:8;}
            Ashore QPushButton:hover{background-color:#5f5f5f;border: 1 solid #bababa;}
            Ashore QPushButton:pressed{background-color:#363636;border: 1 solid #919191;}
            Ashore Section QPushButton{width:23;height:23;border-radius:3;}
            SettingPage QPushButton{width:23;height:23;border-radius:3;background-color:#5d795f}
        ''')
        self.createMenuBar()
        self.createStatusBar()
        self.createTrayIcon()

    def setConnect(self) -> None:
        self.addBtn.clicked.connect(self.slotClickBtnAddNew)
        self.unpauseAllBtn.clicked.connect(self.slotUnpauseAll)
        self.pauseAllBtn.clicked.connect(self.slotPauseAll)
        self.tabDownloading.clicked.connect(self.slotSwitchDownloading)
        self.tabDownloaded.clicked.connect(self.slotSwitchDownloaded)
        self.tabSetting.clicked.connect(self.slotSwitchSetting)
        self.pageSetting.aria2ConfSinOut.connect(self.slotUpdateRunningAria2Config)
        self.pageSetting.ashoreConfigSinOut.connect(self.slotUpdateRunningAshoreConfig)
        self.pageDownloading.sectionAdded.connect(self.connectSection)
        self.pageDownloaded.sectionAdded.connect(self.connectSection)

    def updatePage(self, snapshot:dict) -> None:
        missions = snapshot['missions']
        globalStatus = snapshot['globalStatus']
        if 'ResultError' in globalStatus:
            self.aria2StateLabel.setText('aria2：未连接')
            self.aria2StateLabel.setToolTip(str(globalStatus['ResultError']))
            self.downSpeedLabel.setText('—')
            self.upSpeedLabel.setText('—')
            return
        if 'ResultError' in missions:
            self.aria2StateLabel.setText('aria2：查询失败')
            self.aria2StateLabel.setToolTip(str(missions['ResultError']))
            return
        self.aria2StateLabel.setText('aria2：已连接')
        self.aria2StateLabel.setToolTip(f'127.0.0.1:{self.aria2Operate.rpc_port}')
        self.pageDownloading.updateSections({status: missions[status] for status in ('active', 'waiting', 'paused')})
        self.pageDownloaded.updateSections({status: missions[status] for status in ('completed', 'error')})
        self.downSpeedLabel.setText(self.getSpeedStr(int(globalStatus['downloadSpeed'])))
        self.upSpeedLabel.setText(self.getSpeedStr(int(globalStatus['uploadSpeed'])))
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
                    self.showDownloadNotification(name, outcome)
                    self.notifiedDownloads.add((gid, outcome))
        self.knownStatuses = current
        self.pendingNotifications.clear()

    def connectSection(self, item):
        item.doubleClickOut.connect(self.slotDoubleClick)
        item.openDirOut.connect(self.slotOpenFolder)
        item.cpUrlOut.connect(self.slotcpUrl)
        item.removeDelOut.connect(self.slotRemoveDel)

    def slotAria2Notification(self, method, gid):
        if method in ('aria2.onDownloadComplete', 'aria2.onBtDownloadComplete', 'aria2.onDownloadError'):
            self.pendingNotifications[gid] = method
        self.aria2Operate.poll()

    def showDownloadNotification(self, name, status):
        if QSystemTrayIcon.isSystemTrayAvailable() and QSystemTrayIcon.supportsMessages():
            title = '下载完成' if status == 'completed' else '下载失败'
            self.TrayIcon.showMessage(title, name)

    def bytesInt2Str(self, b:int) -> str:
        if b < 1024:
            s = str(b) + 'B'
        elif b < 1048576:
            s = '{:.2f}KB'.format(b/1024)
        elif b < 1073741824:
            s = '{:.2f}MB'.format(b/1048576)
        elif b < 1099511627776:
            s = '{:.2f}GB'.format(b/1073741824)
        else:
            s = '{:.2f}TB'.format(b/1099511627776)
        return s

    def getSpeedStr(self, speed:int) -> str:
        s = self.bytesInt2Str(speed) + '/s'
        return s

    def slotSwitchDownloading(self) -> None:
        self.tabDownloading.setEnabled(False)
        self.tabDownloaded.setEnabled(True)
        self.tabSetting.setEnabled(True)
        self.pageStack.setCurrentIndex(0)

    def slotSwitchDownloaded(self) -> None:
        self.tabDownloading.setEnabled(True)
        self.tabDownloaded.setEnabled(False)
        self.tabSetting.setEnabled(True)
        self.pageStack.setCurrentIndex(1)

    def slotSwitchSetting(self) -> None:
        config = self.aria2Operate.getGlobalConfig()
        if 'ResultError' in config:
            self.myPrint(config['ResultError'])
            return
        else:
            self.tabDownloading.setEnabled(True)
            self.tabDownloaded.setEnabled(True)
            self.tabSetting.setEnabled(False)
            self.pageSetting.updateSettingPage(config)
            self.pageStack.setCurrentIndex(2)

    def addNew(self, urlList:list=None) -> None:
        """通过命令行参数或系统接口参数运行程序、添加新任务
        :param urlList: list类型的下载地址url
        """
        config = {'ResultError' : 0}
        config = self.aria2Operate.getGlobalConfig()
        if 'ResultError' in config:
            self.myPrint(config['ResultError'])
            return
        else:
            form = AddNewDialog(config['dir'], urlList)
            form.sinOut.connect(self.addUrls)
            form.show()
            form.exec()
            self.aria2Operate.poll()

    def addUrls(self, data):
        result = self.aria2Operate.addUrls(data)
        if 'ResultError' in result:
            QMessageBox.warning(self, '添加任务失败', str(result['ResultError']))

    def slotClickBtnAddNew(self) -> None:
        """用户通过按钮触发的添加新任务,无参数
        """
        self.addNew()

    def slotUnpauseAll(self):
        unpauseAllResult = self.aria2Operate.unpauseAll()
        if 'ResultError' in unpauseAllResult:
            self.myPrint(unpauseAllResult['ResultError'])

    def slotPauseAll(self):
        pauseAllResult = self.aria2Operate.pauseAll()
        if 'ResultError' in pauseAllResult:
            self.myPrint(pauseAllResult['ResultError'])

    def slotAbout(self):
        aboutTitle = QLabel('<h1 style="Text-align: center;">Ashore</h1>')
        aboutTitle.setFixedHeight(30)
        infoLIcon = QLabel()
        infoLIcon.setPixmap(QPixmap(self.BASEPATH + 'static/icon/icon.funtion/icon0.png'))
        infoLIcon.setScaledContents(True)
        infoLIcon.setFixedSize(180, 180)
        aria2Version = self.aria2Operate.getAria2Version()
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
        saveResult = self.aria2Operate.saveSession()
        if 'ResultError' in saveResult:
            self.myPrint(saveResult['ResultError'])

    def slotQuit(self):
        if self.quitting:
            return
        self.quitting = True
        self.aria2Operate.timer.stop()
        self.aria2Events.stop()
        self.aria2Operate.wait()
        self.aria2Operate.saveSession()
        if self.aria2Operate.mainKillAria2():
            QApplication.instance().quit()

    def slotRestartAria2(self):
        self.aria2Operate.timer.stop()
        self.aria2Operate.wait()
        try:
            self.aria2Operate.restartAria2(self.BASEPATH)
        except RuntimeError as exc:
            QMessageBox.warning(self, '无法重启 aria2', str(exc))
        finally:
            self.aria2Events.setPort(self.aria2Operate.rpc_port)
            self.aria2Operate.timer.start()
            self.aria2Operate.poll()

    def slotDoubleClick(self, data:tuple) -> None:
        gid = data[0]
        status = data[1]
        #根据section状态判定双击的作用是开始或暂停
        if status == 'active' or status == 'waiting' :
            self.aria2Operate.pause(gid)
        elif status == 'paused':
            self.aria2Operate.unpause(gid)
        elif status == 'completed':
            filePathResult = self.aria2Operate.getFilePath(gid)
            if 'ResultError' in filePathResult:
                self.myPrint(filePathResult['ResultError'])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(filePathResult['filePath']))
        elif status == 'error':
            self.aria2Operate.retry(gid)
        self.aria2Operate.poll()

    def slotOpenFolder(self, gid:str) -> None:
        OpenResult = self.aria2Operate.openFileDir(gid)
        if 'ResultError' in OpenResult:
            self.myPrint(OpenResult['ResultError'])
        elif 'dir' in OpenResult:
            #返回非空,含有目录地址，代表使用不同系统特色方法调用失败,使用通用办法
            QDesktopServices.openUrl(QUrl.fromLocalFile(OpenResult['dir']))

    def slotcpUrl(self, gid:str) -> None:
        urlResult = self.aria2Operate.getUrl(gid)
        if 'ResultError' in urlResult:
            self.myPrint(urlResult['ResultError'])
        else:
            clipboard = QApplication.clipboard()
            clipboard.setText(urlResult['url'])
            self.myPrint('已复制到剪贴板')        

    def slotRemoveDel(self, data:tuple) -> None:
        gid = data[0]
        delFile = data[1]
        result = self.aria2Operate.delRemoveMission(gid=gid, delFile=delFile)
        if 'ResultError' in result:
            self.myPrint(result['ResultError'])
        else:
            self.myPrint('删除成功')
        self.aria2Operate.poll()

    def slotUpdateRunningAria2Config(self, conf:dict) -> None:
        # 将setting页面的设置信息更新到运行的aria2程序中
        result = conf if 'ResultError' in conf else self.aria2Operate.setGlobalConfig(conf)
        self.aria2ConfigError = result.get('ResultError') if isinstance(result, dict) else str(result)

    def slotUpdateRunningAshoreConfig(self, conf:dict) -> None:
        # 将setting页面的设置信息更新到运行的ashore程序中
        if conf['quit_with_aria2'] == 'false':
            self.aria2Operate.QuitWithAria2 = False
        elif conf['quit_with_aria2'] == 'true':
            self.aria2Operate.QuitWithAria2 = True
        self.aria2Operate.timer.setInterval(max(500, int(conf['update_interval'])))
        if getattr(self, 'aria2ConfigError', None):
            self.myPrint('配置已保存，但运行中 aria2 未能应用设置：' + str(self.aria2ConfigError))
        else:
            self.myPrint(conf['isSaved'])

    def myPrint(self, data, end=None):
        if type(data) == int:
            #是int的错误代码
            # self.aria2Operate.ERRORLIST[data]
            self.statusBar.showMessage(self.aria2Operate.ERRORLIST[data], 3000)
        else:
            #将提示信息显示在状态栏中showMessage（‘提示信息’，显示时间（单位毫秒））
            self.statusBar.showMessage(data, 3000)
            if not self.isRelease:
                #当程序处于coding阶段时允许输出，当为release时禁止输出
                print(data, end=end)

class MyApplication(QApplication):

    fileOpenSignal = pyqtSignal(list)
    instanceMessage = pyqtSignal(list)

    def __init__(self, arguments):
        super().__init__(arguments)
        self.setQuitOnLastWindowClosed(False)    #设置关闭窗口后最小化
        self.setApplicationVersion(APP_VERSION)
        self.setOrganizationName('PanZK')
        self.setApplicationName("Ashore")

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

if __name__ == '__main__':
    BASEPATH = str(RESOURCE_DIR) + '/'
    if getattr(sys, 'frozen', False):
        BASEPATH = sys._MEIPASS + '/'
    app = MyApplication(sys.argv)
    try:
        if app.forwardToExisting(sys.argv[1:]):
            sys.exit(0)
    except RuntimeError as exc:
        QMessageBox.critical(None, 'Ashore 启动失败', str(exc))
        sys.exit(1)
    splash = QSplashScreen(QPixmap(BASEPATH + 'static/img/cover.png'))
    splash.show()                               #展示启动图片
    app.processEvents()                         #防止进程卡死
    if platform.system() == 'Darwin':
        app.setFont(QFont('Hiragino Sans GB'))  #防止mac系统上运行速度受阻，选用“冬青黑体简体中文”为默认字体
        app.setWindowIcon(QIcon(BASEPATH + 'static/icon/icon.funtion/icon.icns'))
    elif platform.system() == 'Linux' or platform.system() == 'Windows':
        app.setWindowIcon(QIcon(BASEPATH + 'static/icon/icon.funtion/icon0.png'))
    try:
        exe = Ashore()
    except (RuntimeError, OSError, ValueError) as exc:
        splash.close()
        QMessageBox.critical(None, 'Ashore 启动失败', str(exc))
        sys.exit(1)
    exe.show()
    splash.finish(exe)                  #关闭启动界面
    if len(sys.argv) != 1:
        exe.addNew(sys.argv[1:])
    app.fileOpenSignal.connect(exe.addNew)
    def handleInstance(urls):
        exe.show()
        exe.raise_()
        exe.activateWindow()
        if urls:
            exe.addNew(urls)
    app.instanceMessage.connect(handleInstance)
    signal.signal(signal.SIGINT, lambda *_: exe.slotQuit())
    signalTimer = QTimer()
    signalTimer.timeout.connect(lambda: None)
    signalTimer.start(250)
    app.exec()
    del exe
    sys.exit()
