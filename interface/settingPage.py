"""Ashore and aria2 settings interface."""

import json
import secrets
import urllib.parse

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFileSystemModel
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QCompleter,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.configStore import readAshore, readOptions, writeAshore, writeOptions
from core.trackerManager import TrackerManager, displayTime
from core.trackerSources import parseTrackers
from interface.languageManager import LANGUAGES
from interface.statusBadge import setConnectionBadge
from interface.themeManager import ACCENT_PRESETS, THEME_MODES, validColor
from paths import CONFIG_DIR, RESOURCE_DIR, ensureConfig, systemDownloadDirectory


class SettingPage(QWidget):

    aria2ConfigChanged = pyqtSignal(dict)
    ashoreConfigChanged = pyqtSignal(dict)
    trackerRuntimeChanged = pyqtSignal(dict)
    themePreview = pyqtSignal(str, str)
    aria2ConfPath = str(CONFIG_DIR / 'aria2.conf')
    ashoreConfDir = str(CONFIG_DIR)

    ashoreKeys = (
        'trackers_list_time', 'trackers_list_source', 'trackers_auto_update',
        'quit_with_aria2', 'update_interval', 'rpc_port_changeable', 'language',
        'legacy_download_path_handled', 'tray_icon_style', 'user_agent_presets',
        'theme_mode', 'accent_color',
    )

    def __init__(self):
        super().__init__()
        self.ashoreConfPath = self.ashoreConfDir + '/ashore.conf'
        ensureConfig('ashore.conf')
        ensureConfig('aria2.conf')
        self.ashoreConfig = self.loadAshoreConfig()
        self.trackerTime = self.ashoreConfig['trackers_list_time']
        self.initUI()
        self.trackerManager = TrackerManager(
            self.ashoreConfPath,
            self.aria2ConfPath,
            RESOURCE_DIR / 'config/ashore.conf',
            self)
        self.trackerManager.statusChanged.connect(self.showTrackerMessage)
        self.trackerManager.updated.connect(self.applyTrackerUpdate)
        self.trackerManager.failed.connect(self.applyTrackerFailure)

    def initUI(self):
        formLayout = QFormLayout()
        formLayout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        formLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        # Aira2设置控件 开始
        self.aria2SettingLabel = QLabel('<h3>Aira2 设置</h3>')
        self.aria2SettingLabel.setFixedHeight(50)
        self.aria2SettingLabel.setMargin(10)
        formLayout.addRow(self.aria2SettingLabel)
        formLayout.addWidget(QLabel('基本设置'))
        #设置目录补全
        completer = QCompleter()
        model = QFileSystemModel()
        model.setRootPath(str(systemDownloadDirectory()))
        completer.setModel(model)
        self.pathLineEdit = QLineEdit(str(systemDownloadDirectory()))
        self.pathLineEdit.setCompleter(completer)
        self.pathLineEdit.setMinimumWidth(260)
        self.pathLineEdit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        pathBtn = QPushButton('选择目录')
        pathLayout = QHBoxLayout()
        pathLayout.addWidget(self.pathLineEdit, 1)
        pathLayout.addWidget(pathBtn)
        formLayout.addRow('默认下载目录:', pathLayout)
        self.maxDownloadsSpin = QSpinBox()
        self.maxDownloadsSpin.setRange(1, 100)
        self.maxDownloadsSpin.setMaximumWidth(100)
        formLayout.addRow('同时最大下载数:', self.maxDownloadsSpin)
        self.maxConnectionSpin = QSpinBox()
        self.maxConnectionSpin.setRange(1, 16)
        self.maxConnectionSpin.setMaximumWidth(100)
        formLayout.addRow('同一服务器连接数:', self.maxConnectionSpin)
        self.userAgentComboBox = QComboBox()
        self.userAgentComboBox.setEditable(True)
        self.userAgentComboBox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.userAgentComboBox.addItems(self.ashoreConfig['user_agent_presets'])
        self.userAgentComboBox.setMinimumWidth(260)
        self.userAgentComboBox.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        formLayout.addRow('User Agent:', self.userAgentComboBox)
        uploadLimitLabel = QLabel('上传限速')
        self.uploadLimitSpin = QSpinBox()
        self.uploadLimitSpin.setRange(0, 1024)
        self.uploadLimitSpin.setSpecialValueText('不限速') 
        self.uploadLimitSpin.setMinimumWidth(150)
        self.uploadLimitComboBox = QComboBox()
        self.uploadLimitComboBox.addItems(['B/s', 'KB/s', 'MB/s', 'GB/s'])
        downloadLimitLabel = QLabel('下载限速')
        self.downloadLimitSpin = QSpinBox()
        self.downloadLimitSpin.setRange(0, 1024)
        self.downloadLimitSpin.setSpecialValueText('不限速') 
        self.downloadLimitSpin.setMinimumWidth(150)
        self.downloadLimitComboBox = QComboBox()
        self.downloadLimitComboBox.addItems(['B/s', 'KB/s', 'MB/s', 'GB/s'])
        transLayout = QGridLayout()
        transLayout.addWidget(uploadLimitLabel,0,0,1,1)
        transLayout.addWidget(self.uploadLimitSpin,0,1,1,1)
        transLayout.addWidget(self.uploadLimitComboBox,0,2,1,1)
        transLayout.addWidget(downloadLimitLabel,1,0,1,1)
        transLayout.addWidget(self.downloadLimitSpin,1,1,1,1)
        transLayout.addWidget(self.downloadLimitComboBox,1,2,1,1)
        transLayout.setColumnStretch(3, 1)
        formLayout.addRow('限速设置:', transLayout)
        self.rpcPortLineEdit = QLineEdit()
        self.rpcPortLineEdit.setMaximumWidth(200)
        self.rpcPortLineEdit.setToolTip('Ashore默认端口为6801')
        self.rpcPortLineEdit.setPlaceholderText('Ashore默认端口为6801')
        formLayout.addRow('rpc监听端口:', self.rpcPortLineEdit)
        self.httpEndpointLabel = QLabel()
        self.httpEndpointLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.httpStatusLabel = QLabel()
        httpLayout = QHBoxLayout()
        httpLayout.addWidget(self.httpEndpointLabel)
        httpLayout.addWidget(self.httpStatusLabel)
        httpLayout.addStretch(10)
        formLayout.addRow('HTTP 轮询:', httpLayout)
        self.websocketEndpointLabel = QLabel()
        self.websocketEndpointLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.websocketStatusLabel = QLabel()
        websocketLayout = QHBoxLayout()
        websocketLayout.addWidget(self.websocketEndpointLabel)
        websocketLayout.addWidget(self.websocketStatusLabel)
        websocketLayout.addStretch(10)
        formLayout.addRow('WebSocket 通知:', websocketLayout)
        self.aria2VersionLabel = QLabel('—')
        formLayout.addRow('aria2 版本:', self.aria2VersionLabel)
        setConnectionBadge(self.httpStatusLabel, '等待检测', False)
        setConnectionBadge(self.websocketStatusLabel, '等待检测', False)
        self.rpcListenAllComboBox = QComboBox()
        self.rpcListenAllComboBox.addItems(['是', '否'])
        self.rpcListenAllComboBox.setCurrentIndex(1)
        self.rpcListenAllComboBox.setToolTip('开启后 aria2 RPC 会监听所有网络接口，而不仅是本机。')
        listenAllLayout = QHBoxLayout()
        listenAllLayout.addWidget(self.rpcListenAllComboBox)
        listenAllLayout.addStretch(10)
        formLayout.addRow('允许外部访问 RPC:', listenAllLayout)
        self.rpcSecretLineEdit = QLineEdit()
        self.rpcSecretLineEdit.setReadOnly(True)
        self.rpcSecretLineEdit.setMinimumWidth(220)
        self.rpcSecretLineEdit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.rpcSecret = ''
        self.rpcSecretVisible = False
        self.rpcSecretRevealBtn = QPushButton('显示')
        self.rpcSecretCopyBtn = QPushButton('复制')
        tokenLayout = QHBoxLayout()
        tokenLayout.addWidget(self.rpcSecretLineEdit, 1)
        tokenLayout.addWidget(self.rpcSecretRevealBtn)
        tokenLayout.addWidget(self.rpcSecretCopyBtn)
        self.rpcSecretLabel = QLabel('RPC 授权令牌:')
        formLayout.addRow(self.rpcSecretLabel, tokenLayout)
        formLayout.addWidget(QLabel('BT设置'))
        self.btTracker = QTextEdit()
        self.btTracker.setMinimumWidth(260)
        self.btTracker.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.trackerBtn = QPushButton('更新Tracker')
        self.trackerInfo = QLabel('1')
        self.trackerStatus = QLabel('')
        self.trackerSource = self.ashoreConfig['trackers_list_source']
        trackerLayout = QGridLayout()
        trackerLayout.addWidget(self.btTracker, 0, 0, 1, 2)
        trackerLayout.addWidget(self.trackerInfo, 1, 0, 1, 1)
        trackerLayout.addWidget(self.trackerBtn, 1, 1, 1, 1)
        trackerLayout.addWidget(self.trackerStatus, 2, 0, 1, 2)
        trackerLayout.setColumnStretch(0, 1)
        formLayout.addRow('btTracker:', trackerLayout)

        self.autoTrackerComboBox = QComboBox()
        self.autoTrackerComboBox.addItems(['是', '否'])
        autoTrackerLayout = QHBoxLayout()
        autoTrackerLayout.addWidget(self.autoTrackerComboBox)
        autoTrackerLayout.addWidget(QLabel('仅在上次成功更新超过 24 小时后执行'))
        autoTrackerLayout.addStretch(1)
        formLayout.addRow('启动时自动更新 Tracker:', autoTrackerLayout)

        # Ashore设置控件 开始
        self.ashoreSettingLabel = QLabel('<h3>Ashore 设置</h3>')
        self.ashoreSettingLabel.setFixedHeight(50)
        self.ashoreSettingLabel.setMargin(10)
        formLayout.addRow(self.ashoreSettingLabel)
        self.withAria2QuitComboBox = QComboBox()
        self.withAria2QuitComboBox.addItems(['是', '否'])
        quitWithAria2Layout = QHBoxLayout()
        quitWithAria2Layout.addWidget(self.withAria2QuitComboBox)
        quitWithAria2Layout.addStretch(10)
        formLayout.addRow('aria2随程序关闭:', quitWithAria2Layout)
        self.updateIntervalSpin = QSpinBox()
        self.updateIntervalSpin.setRange(500, 10000)
        self.updateIntervalSpin.setSingleStep(100)
        self.updateIntervalSpin.setMaximumWidth(100)
        updateIntervalLabel = QLabel('毫秒')
        updateIntervalLayout = QHBoxLayout()
        updateIntervalLayout.addWidget(self.updateIntervalSpin)
        updateIntervalLayout.addWidget(updateIntervalLabel)
        formLayout.addRow('界面刷新间隔:', updateIntervalLayout)
        self.rpcPortChangeableComboBox = QComboBox()
        self.rpcPortChangeableComboBox.addItems(['是', '否'])
        rpcPortChangeableLayout = QHBoxLayout()
        rpcPortChangeableLayout.addWidget(self.rpcPortChangeableComboBox)
        rpcPortChangeableLayout.addStretch(10)
        formLayout.addRow('允许修改rpc接口:', rpcPortChangeableLayout)
        self.languageComboBox = QComboBox()
        for code, name in LANGUAGES.items():
            self.languageComboBox.addItem(name, code)
        languageLayout = QHBoxLayout()
        languageLayout.addWidget(self.languageComboBox)
        languageLayout.addStretch(10)
        formLayout.addRow('界面语言:', languageLayout)
        self.trayIconStyleComboBox = QComboBox()
        self.trayIconStyleComboBox.addItem('彩色', 'colorful')
        self.trayIconStyleComboBox.addItem('灰色', 'gray')
        trayIconLayout = QHBoxLayout()
        trayIconLayout.addWidget(self.trayIconStyleComboBox)
        trayIconLayout.addStretch(10)
        formLayout.addRow('托盘图标样式:', trayIconLayout)

        self.themeModeComboBox = QComboBox()
        themeNames = {'system': '跟随系统', 'light': '浅色', 'dark': '深色'}
        for mode in THEME_MODES:
            self.themeModeComboBox.addItem(themeNames[mode], mode)
        themeLayout = QHBoxLayout()
        themeLayout.addWidget(self.themeModeComboBox)
        themeLayout.addStretch(1)
        formLayout.addRow('明暗主题:', themeLayout)

        self.accentComboBox = QComboBox()
        self.accentComboBox.setEditable(True)
        for color in ACCENT_PRESETS:
            self.accentComboBox.addItem(color, color)
        accentButton = QPushButton('选择颜色')
        accentLayout = QHBoxLayout()
        accentLayout.addWidget(self.accentComboBox)
        accentLayout.addWidget(accentButton)
        accentLayout.addStretch(1)
        formLayout.addRow('主题颜色:', accentLayout)

        settingWidget = QWidget()
        settingWidget.setLayout(formLayout)
        settingWidget.setContentsMargins(20,0,0,0)
        scrollToAria2Btn = QPushButton('Aria2 设置')
        scrollToAshoreBtn = QPushButton('Ashore 设置')
        self.saveBtn = QPushButton('保存设置')
        scrollBtnLayout = QVBoxLayout()
        scrollBtnLayout.addWidget(scrollToAria2Btn)
        scrollBtnLayout.addWidget(scrollToAshoreBtn)
        scrollBtnLayout.addStretch(10)
        scrollBtnLayout.addWidget(self.saveBtn)
        scrollBtnLayout.setContentsMargins(10,0,10,0)
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(settingWidget)

        mainLayout = QHBoxLayout()
        mainLayout.addLayout(scrollBtnLayout)
        mainLayout.addWidget(self.scrollArea)

        self.setLayout(mainLayout)
        self.setMinimumWidth(760)

        pathBtn.clicked.connect(self.slotDir)
        scrollToAria2Btn.clicked.connect(self.slotScrollToAria2)
        scrollToAshoreBtn.clicked.connect(self.slotScrollToAshore)
        self.trackerBtn.clicked.connect(self.slotTracker)
        self.saveBtn.clicked.connect(self.slotSaveConf)
        self.rpcPortChangeableComboBox.currentIndexChanged.connect(self.slotRpcPortChangeable)
        self.rpcPortLineEdit.textChanged.connect(self.updateEndpoints)
        self.rpcListenAllComboBox.currentIndexChanged.connect(self.toggleRpcAccess)
        self.rpcSecretRevealBtn.clicked.connect(self.toggleToken)
        self.rpcSecretCopyBtn.clicked.connect(self.copyToken)
        self.themeModeComboBox.currentIndexChanged.connect(self.previewTheme)
        self.accentComboBox.currentTextChanged.connect(self.previewTheme)
        accentButton.clicked.connect(self.pickAccent)
        self.updateTokenRow()
    
    def loadSettings(self, aria2Config:dict):
        self.ashoreConfig = self.loadAshoreConfig()
        self.loadAria2(aria2Config)
        self.loadAshore(self.ashoreConfig)

    def loadAria2(self, aria2Config:dict):
        aria2Config = dict(aria2Config)
        aria2Config.update(self.readRpcConfig())
        self.pathLineEdit.setText(aria2Config['dir'])
        self.maxDownloadsSpin.setValue(int(aria2Config['max-concurrent-downloads']))
        self.maxConnectionSpin.setValue(int(aria2Config['max-connection-per-server']))
        userAgent = aria2Config['user-agent']
        if self.userAgentComboBox.findText(userAgent) < 0:
            self.userAgentComboBox.addItem(userAgent)
        self.userAgentComboBox.setCurrentText(userAgent)
        self.setMaxLimit(aria2Config['max-overall-upload-limit'], 'upload')
        self.setMaxLimit(aria2Config['max-overall-download-limit'], 'download')
        self.rpcPortLineEdit.setText(aria2Config['rpc-listen-port'])
        self.setBoolOption(self.rpcListenAllComboBox, aria2Config.get('rpc-listen-all', False))
        self.setRpcSecret(aria2Config.get('rpc-secret', ''))
        self.updateEndpoints()
        self.updateTokenRow()
        self.btTracker.setText(aria2Config['bt-tracker'])
        self.showTrackerStatus()

    def loadAshore(self, ashoreConfig:dict):
        self.trackerTime = ashoreConfig['trackers_list_time']
        self.trackerInfo.setText(displayTime(self.trackerTime))
        self.trackerSource = ashoreConfig['trackers_list_source']
        self.showTrackerStatus()
        self.setBoolOption(self.withAria2QuitComboBox, ashoreConfig['quit_with_aria2'])
        self.setBoolOption(self.rpcPortChangeableComboBox, ashoreConfig['rpc_port_changeable'])
        self.updateIntervalSpin.setValue(int(ashoreConfig['update_interval']))
        self.rpcPortLineEdit.setEnabled(ashoreConfig['rpc_port_changeable'])
        languageIndex = self.languageComboBox.findData(ashoreConfig.get('language', 'zh_CN'))
        self.languageComboBox.setCurrentIndex(max(0, languageIndex))
        trayIconIndex = self.trayIconStyleComboBox.findData(
            ashoreConfig.get('tray_icon_style', 'colorful'))
        self.trayIconStyleComboBox.setCurrentIndex(max(0, trayIconIndex))
        self.setBoolOption(
            self.autoTrackerComboBox,
            ashoreConfig.get('trackers_auto_update', True))
        themeIndex = self.themeModeComboBox.findData(
            ashoreConfig.get('theme_mode', 'system'))
        self.themeModeComboBox.setCurrentIndex(max(0, themeIndex))
        self.accentComboBox.setCurrentText(
            validColor(ashoreConfig.get('accent_color', ACCENT_PRESETS[0])))

    def setMaxLimit(self, value, which:str):
        text = str(value or '0').strip()
        suffixes = {'K': 1, 'M': 2, 'G': 3}
        suffix = text[-1].upper()
        if suffix in suffixes:
            amount = int(text[:-1] or 0)
            unitIndex = suffixes[suffix]
        else:
            amount = int(text[:-1] if suffix == 'B' else text)
            unitIndex = 0
            while amount >= 1024 and unitIndex < 3:
                amount //= 1024
                unitIndex += 1
        if which == 'upload':
            self.uploadLimitSpin.setValue(amount)
            self.uploadLimitComboBox.setCurrentIndex(unitIndex)
        elif which == 'download':
            self.downloadLimitSpin.setValue(amount)
            self.downloadLimitComboBox.setCurrentIndex(unitIndex)

    def getMaxLimit(self, which:str) -> str:
        #将settingpage上带单位的限速设置写入aria2.conf
        if which == 'upload':
            amount = self.uploadLimitSpin.value()
            unitIndex = self.uploadLimitComboBox.currentIndex()
        else:
            amount = self.downloadLimitSpin.value()
            unitIndex = self.downloadLimitComboBox.currentIndex()
        return f'{amount}{("", "K", "M", "G")[unitIndex]}'

    def getBoolOption(self, boolObject:QComboBox) -> str:
        return 'true' if boolObject.currentIndex() == 0 else 'false'

    def setBoolOption(self, boolObject:QComboBox, flag:bool) -> None:
        boolObject.setCurrentIndex(0 if flag else 1)

    def loadAshoreConfig(self) -> dict:
        ashoreConfig = readAshore(
            self.ashoreConfPath, RESOURCE_DIR / 'config/ashore.conf')
        tempDict = {}
        for key in type(self).ashoreKeys:
            value = ashoreConfig.get(key)
            if value == 'true':
                value = True
            elif value == 'false':
                value = False
            elif key == 'user_agent_presets':
                try:
                    value = json.loads(value)
                except (TypeError, ValueError):
                    value = []
                if not isinstance(value, list):
                    value = []
                value = [item for item in value if isinstance(item, str) and item.strip()]
            tempDict[key] = value
        return tempDict

    def readRpcConfig(self) -> dict:
        options = {'rpc-listen-port': '6801', 'rpc-listen-all': False, 'rpc-secret': ''}
        options.update({key: value for key, value in readOptions(self.aria2ConfPath).items()
                        if key in options})
        options['rpc-listen-all'] = str(options['rpc-listen-all']).lower() == 'true'
        return options

    def readAria2Config(self) -> dict:
        options = {
            'dir': str(systemDownloadDirectory()),
            'user-agent': '',
            'max-concurrent-downloads': '5',
            'max-connection-per-server': '1',
            'max-overall-upload-limit': '0',
            'max-overall-download-limit': '0',
            'rpc-listen-port': '6801',
            'bt-tracker': '',
        }
        options.update({key: value for key, value in readOptions(self.aria2ConfPath).items()
                        if key in options})
        options.update(self.readRpcConfig())
        return options

    def slotDir(self):
        path = QFileDialog.getExistingDirectory(self,'Open dir', self.pathLineEdit.text(), QFileDialog.Option.ShowDirsOnly)
        if path != '':
            self.pathLineEdit.setText(path)

    def slotTracker(self):
        self.saveBtn.setEnabled(False)
        self.trackerBtn.setEnabled(False)
        self.trackerBtn.setText('更新中...')
        self.trackerManager.start(force=True)

    def startAutoTracker(self):
        return self.trackerManager.start()

    def showTrackerStatus(self):
        count = len(parseTrackers(self.btTracker.toPlainText()))
        source = urllib.parse.urlsplit(self.trackerSource).netloc if self.trackerSource else '手动配置'
        self.trackerStatus.setText(f'当前列表 {count} 条；来源：{source}。列表数量不代表连接有效。')

    def showTrackerMessage(self, message):
        self.trackerStatus.setText(message)

    def applyTrackerUpdate(self, trackers, source, timestamp):
        self.trackerSource = source
        self.trackerTime = timestamp
        self.trackerInfo.setText(displayTime(timestamp))
        self.btTracker.setText(','.join(trackers))
        host = urllib.parse.urlsplit(source).netloc
        self.trackerStatus.setText(f'获取 {len(trackers)} 条；来源：{host}。已保存。')
        self.trackerBtn.setText('更新Tracker')
        self.trackerBtn.setEnabled(True)
        self.saveBtn.setEnabled(True)
        self.trackerRuntimeChanged.emit({'bt-tracker': ','.join(trackers)})

    def applyTrackerFailure(self, error):
        self.trackerStatus.setText(f'更新失败：{error}；保留原列表。')
        self.trackerBtn.setText('更新失败')
        self.trackerBtn.setEnabled(True)
        self.saveBtn.setEnabled(True)

    def slotSaveConf(self) -> None:
        #用户配置界面有的选项
        aria2Values = {
            'dir'                       :   self.pathLineEdit.text(),
            'bt-tracker'                :   ','.join(parseTrackers(self.btTracker.toPlainText())),
            'max-concurrent-downloads'  :   str(self.maxDownloadsSpin.value()),
            'max-connection-per-server' :   str(self.maxConnectionSpin.value()),
            'user-agent'                :   self.userAgentComboBox.currentText().strip(),
            'max-overall-upload-limit'  :   self.getMaxLimit('upload'),
            'max-overall-download-limit':   self.getMaxLimit('download'),
            'rpc-listen-port'           :   self.rpcPortLineEdit.text(),
            'rpc-listen-all'            :   self.getBoolOption(self.rpcListenAllComboBox),
            }
        rpcExternal = aria2Values['rpc-listen-all'] == 'true'
        if rpcExternal:
            if not self.rpcSecret:
                self.setRpcSecret(secrets.token_urlsafe(32))
            aria2Values['rpc-secret'] = self.rpcSecret
        ashoreValues = {
            'trackers_list_time'    :   self.trackerTime,
            'trackers_list_source'  :   self.trackerSource,
            'quit_with_aria2'       :   self.getBoolOption(self.withAria2QuitComboBox),
            'update_interval'       :   str(self.updateIntervalSpin.value()),
            'rpc_port_changeable'   :   self.getBoolOption(self.rpcPortChangeableComboBox),
            'language'              :   self.languageComboBox.currentData(),
            'tray_icon_style'       :   self.trayIconStyleComboBox.currentData(),
            'trackers_auto_update'  :   self.getBoolOption(self.autoTrackerComboBox),
            'theme_mode'            :   self.themeModeComboBox.currentData(),
            'accent_color'          :   validColor(self.accentComboBox.currentText()),
        }
        oldRpc = self.readRpcConfig()
        removeKeys = set() if rpcExternal else {'rpc-secret'}
        aria2Saved = self.saveAria2Conf(aria2Values, removeKeys) == 0
        if aria2Saved:
            runningOptions = {key: value for key, value in aria2Values.items()
                               if key not in ('rpc-listen-port', 'rpc-listen-all', 'rpc-secret')}
            oldValues = {
                'rpc-listen-port': str(oldRpc.get('rpc-listen-port', '')),
                'rpc-listen-all': 'true' if oldRpc.get('rpc-listen-all') else 'false',
                'rpc-secret': str(oldRpc.get('rpc-secret', '')),
            }
            rpcChanged = any(oldValues[key] != str(aria2Values.get(key, ''))
                             for key in ('rpc-listen-port', 'rpc-listen-all', 'rpc-secret'))
            if not rpcExternal and oldRpc.get('rpc-secret'):
                rpcChanged = True
            self.aria2ConfigChanged.emit({'runtime': runningOptions, 'rpcChanged': rpcChanged})
        else:
            self.trackerStatus.setText('aria2 配置未能保存，请检查配置目录权限。')
            self.aria2ConfigChanged.emit({'ResultError': 'aria2 配置写入失败'})
        if self.saveAshoreConf(ashoreValues) == 0:
            if aria2Saved:
                self.showTrackerStatus()
            ashoreValues.update({'isSaved': '保存成功'})
            self.ashoreConfigChanged.emit(ashoreValues)
        else:
            ashoreValues.update({'isSaved': '保存失败'})
            self.ashoreConfigChanged.emit(ashoreValues)

    def saveAria2Conf(self, aria2Values:dict, removeKeys=None) -> int:
        removeKeys = set(removeKeys or ())
        if not writeOptions(self.aria2ConfPath, aria2Values, removeKeys):
            return -1
        return 0

    def toggleRpcAccess(self, index:int) -> None:
        if index == 0 and not self.rpcSecret:
            self.setRpcSecret(secrets.token_urlsafe(32))
        self.updateTokenRow()

    def updateTokenRow(self) -> None:
        visible = self.rpcListenAllComboBox.currentIndex() == 0
        self.rpcSecretLabel.setVisible(visible)
        self.rpcSecretLineEdit.setVisible(visible)
        self.rpcSecretRevealBtn.setVisible(visible)
        self.rpcSecretCopyBtn.setVisible(visible)

    def toggleToken(self) -> None:
        self.rpcSecretVisible = not self.rpcSecretVisible
        self.refreshRpcSecret()

    def setRpcSecret(self, token):
        self.rpcSecret = token or ''
        self.refreshRpcSecret()

    def refreshRpcSecret(self):
        mask = '●' * 12 if self.rpcSecret else ''
        self.rpcSecretLineEdit.setText(self.rpcSecret if self.rpcSecretVisible else mask)
        self.rpcSecretRevealBtn.setText('隐藏' if self.rpcSecretVisible else '显示')

    def copyToken(self) -> None:
        QApplication.clipboard().setText(self.rpcSecret)
        self.rpcSecretCopyBtn.setText('已复制')
        QTimer.singleShot(1500, lambda: self.rpcSecretCopyBtn.setText('复制'))

    def updateEndpoints(self) -> None:
        port = self.rpcPortLineEdit.text() or '6801'
        self.httpEndpointLabel.setText(f'http://127.0.0.1:{port}/jsonrpc')
        self.websocketEndpointLabel.setText(f'ws://127.0.0.1:{port}/jsonrpc')

    def setConnectionStatus(self, httpStatus:str, websocketStatus:str, aria2Version:str='') -> None:
        setConnectionBadge(self.httpStatusLabel, httpStatus, httpStatus == '已连接')
        setConnectionBadge(self.websocketStatusLabel, websocketStatus,
                           websocketStatus == '已连接')
        self.aria2VersionLabel.setText(aria2Version or '—')

    def saveAshoreConf(self, ashoreValues:dict) -> int:
        cleanValues = {key: value for key, value in ashoreValues.items()
                       if key != 'isSaved'}
        if not writeAshore(self.ashoreConfPath, cleanValues):
            return -1
        self.ashoreConfig = self.loadAshoreConfig()
        return 0

    def previewTheme(self, *_):
        mode = self.themeModeComboBox.currentData() or 'system'
        self.themePreview.emit(mode, validColor(self.accentComboBox.currentText()))

    def pickAccent(self):
        color = QColorDialog.getColor(
            QColor(validColor(self.accentComboBox.currentText())), self, '选择主题颜色')
        if color.isValid():
            self.accentComboBox.setCurrentText(color.name())

    def slotRpcPortChangeable(self, index:int=1) -> None:
        #将rpc port LineEdit设置为相应状态
        self.rpcPortLineEdit.setEnabled(not index)

    def slotScrollToAria2(self) -> None:
        self.scrollArea.verticalScrollBar().setValue(self.aria2SettingLabel.y())

    def slotScrollToAshore(self) -> None:
        self.scrollArea.verticalScrollBar().setValue(self.ashoreSettingLabel.y())
