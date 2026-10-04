#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Time    :   2023/03/26 16:56:04
@File    :   settingPage.py
@Software:   VSCode
@Author  :   PPPPAN 
@Version :   0.7.66
@Contact :   for_freedom_x64@live.com
'''

import sys, os, time, configparser, platform, secrets, urllib.parse
from paths import CONFIG_DIR, RESOURCE_DIR, ensure_config
from core.trackerSources import fetchTrackers, parseTrackers
from interface.languageManager import LANGUAGES
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QScrollArea, QFormLayout, QLineEdit, QTextEdit,QGridLayout, QComboBox, QCompleter, QSpinBox, QSpacerItem
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer

class Thread(QThread):

    sinOut = pyqtSignal(list, str)

    def run(self):
        trackers, source = fetchTrackers()
        self.sinOut.emit(trackers, source)


class SettingPage(QWidget):

    aria2ConfSinOut = pyqtSignal(dict)
    ashoreConfigSinOut = pyqtSignal(dict)
    #生成资源文件目录访问路径
    #说明： pyinstaller工具打包的可执行文件，运行时sys。frozen会被设置成True
    #      因此可以通过sys.frozen的值区分是开发环境还是打包后的生成环境
    #
    #      打包后的生产环境，资源文件都放在sys._MEIPASS目录下
    #      修改main.spec中的datas，
    #      如datas=[('res', 'res')]，意思是当前目录下的res目录加入目标exe中，在运行时放在零时文件的根目录下，名称为res
    BASEPATH = ''
    aria2ConfPath = str(CONFIG_DIR / 'aria2.conf')
    ashoreConfDir = str(CONFIG_DIR)

    Aria2Config = {
        'dir'                           :   None,
        'user-agent'                    :   None,
        'max-concurrent-downloads'      :   None,
        'max-connection-per-server'     :   None,
        'max-overall-upload-limit'      :   None,
        'max-overall-download-limit'    :   None,
        'rpc-listen-port'               :   None,
        'rpc-listen-all'                :   None,
        'rpc-secret'                    :   None,
        'bt-tracker'                    :   None,
    }

    AshoreConfig = {
        'trackers_list_time'    : None,
        'trackers_list_source'  : None,
        'quit_with_aria2'       : None,
        'update_interval'       : None,
        'rpc_port_changeable'   : None,
        'language'              : None,
    }

    def __init__(self):
        super().__init__()
        #定义aria2配置字典
        self.globalAria2Conf = dict(self.Aria2Config)
        #ashore.conf配置文件路径
        self.ashoreConfPath = self.ashoreConfDir + '/ashore.conf'
        # 可能因第一次运行或目录损坏导致conf目录不存在，则新建目录
        ensure_config('ashore.conf')
        #在生成settinpage时就将AshoreConfig注入进来，关于aria2的配置已在aria2Operate加载，则在点开settpage时显示出即可
        self.AshoreConfig = self.getAshoreConfig()
        self.initUI()

    def initUI(self):
        formLayout = QFormLayout()
        formLayout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        # Aira2设置控件 开始
        self.aria2SettingLabel = QLabel('<h3>Aira2 设置</h3>')
        self.aria2SettingLabel.setFixedHeight(50)
        self.aria2SettingLabel.setMargin(10)
        formLayout.addRow(self.aria2SettingLabel)
        formLayout.addWidget(QLabel('基本设置'))
        #设置目录补全
        completer = QCompleter()
        model = QFileSystemModel()
        model.setRootPath(os.path.expanduser('~/Downloads'))
        completer.setModel(model)
        self.pathLineEdit = QLineEdit('~/Download')
        self.pathLineEdit.setCompleter(completer)
        self.pathLineEdit.setMinimumWidth(450)
        pathBtn = QPushButton('选择目录')
        pathBtn.setFixedWidth(100)
        pathLayout = QHBoxLayout()
        pathLayout.addWidget(self.pathLineEdit)
        pathLayout.addWidget(pathBtn)
        formLayout.addRow('默认下载目录:', pathLayout)
        self.maxDownloadsSpin = QSpinBox()
        self.maxDownloadsSpin.setRange(1, 100)
        self.maxDownloadsSpin.setMaximumWidth(100)
        formLayout.addRow('同时最大下载数:', self.maxDownloadsSpin)
        self.maConnectionSpin = QSpinBox()
        self.maConnectionSpin.setRange(1, 16)
        self.maConnectionSpin.setMaximumWidth(100)
        formLayout.addRow('同一服务器连接数:', self.maConnectionSpin)
        self.userAgentLineEdit = QLineEdit('')
        self.userAgentLineEdit.setMinimumWidth(500)
        formLayout.addRow('User Agent:', self.userAgentLineEdit)
        uploadLimitLabel = QLabel('上传限速')
        self.uploadLimitSpin = QSpinBox()
        self.uploadLimitSpin.setRange(0, 1024)
        self.uploadLimitSpin.setSpecialValueText('不限速') 
        self.uploadLimitSpin.setMinimumWidth(150)
        self.uploadLimitComboBox = QComboBox()
        self.uploadLimitComboBox.addItems(['B/s', 'KB/s', 'MB/s', 'GB/s'])
        downloaLimitLabel = QLabel('下载限速') 
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
        transLayout.addWidget(downloaLimitLabel,1,0,1,1)
        transLayout.addWidget(self.downloadLimitSpin,1,1,1,1)
        transLayout.addWidget(self.downloadLimitComboBox,1,2,1,1)
        transLayout.addItem(QSpacerItem(300,20),0,3,2,1)
        formLayout.addRow('限速设置:', transLayout)
        self.rpcPortLineEdit = QLineEdit()
        self.rpcPortLineEdit.setMaximumWidth(200)
        self.rpcPortLineEdit.setToolTip('Ashore默认端口为6801')
        self.rpcPortLineEdit.setPlaceholderText('Ashore默认端口为6801')
        formLayout.addRow('rpc监听端口:', self.rpcPortLineEdit)
        self.rpcProtocolLabel = QLabel()
        self.rpcProtocolLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        formLayout.addRow('Ashore 连接地址:', self.rpcProtocolLabel)
        self.rpcConnectionLabel = QLabel('HTTP：等待检测；WebSocket：等待检测')
        formLayout.addRow('连接状态:', self.rpcConnectionLabel)
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
        self.rpcSecretLineEdit.setEchoMode(QLineEdit.EchoMode.Password)
        self.rpcSecretLineEdit.setMinimumWidth(360)
        self.rpcSecretRevealBtn = QPushButton('显示')
        self.rpcSecretCopyBtn = QPushButton('复制')
        tokenLayout = QHBoxLayout()
        tokenLayout.addWidget(self.rpcSecretLineEdit)
        tokenLayout.addWidget(self.rpcSecretRevealBtn)
        tokenLayout.addWidget(self.rpcSecretCopyBtn)
        self.rpcSecretLabel = QLabel('RPC 授权令牌:')
        formLayout.addRow(self.rpcSecretLabel, tokenLayout)
        formLayout.addWidget(QLabel('BT设置'))
        self.btTracker = QTextEdit()
        self.btTracker.setMinimumWidth(500)
        self.trackerBtn = QPushButton('更新Tracker')
        self.trackerBtn.setFixedWidth(100)
        self.trackerInfo = QLabel('1')
        self.trackerStatus = QLabel('')
        self.trackerSource = self.AshoreConfig['trackers_list_source']
        trackerLayout = QGridLayout()
        trackerLayout.addWidget(self.btTracker, 0, 0, 1, 2)
        trackerLayout.addWidget(self.trackerInfo, 1, 0, 1, 1)
        trackerLayout.addWidget(self.trackerBtn, 1, 1, 1, 1)
        trackerLayout.addWidget(self.trackerStatus, 2, 0, 1, 2)
        formLayout.addRow('btTracker:', trackerLayout)

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

        settingWidget = QWidget()
        settingWidget.setLayout(formLayout)
        settingWidget.setContentsMargins(20,0,0,0)
        # settingWidget.setMinimumWidth(400)
        scrollToAria2Btn = QPushButton('Aria2 设置')
        scrollToAria2Btn.setFixedWidth(120)
        scrollToAshoreBtn = QPushButton('Ashore 设置')
        scrollToAshoreBtn.setFixedWidth(120)
        self.saveBtn = QPushButton('保存设置')
        self.saveBtn.setFixedWidth(120)
        scrollBtnLayout = QVBoxLayout()
        scrollBtnLayout.addWidget(scrollToAria2Btn)
        scrollBtnLayout.addWidget(scrollToAshoreBtn)
        scrollBtnLayout.addStretch(10)
        scrollBtnLayout.addWidget(self.saveBtn)
        scrollBtnLayout.setContentsMargins(10,0,10,0)
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(settingWidget)

        mainLayout = QHBoxLayout()
        mainLayout.addLayout(scrollBtnLayout)
        mainLayout.addWidget(self.scrollArea)

        self.setLayout(mainLayout)
        self.setMinimumWidth(945)

        # 生成时先更新已获取的Ashore配置部分
        # self.updateAhoreSetting(self.AshoreConfig)

        pathBtn.clicked.connect(self.slotDir)
        scrollToAria2Btn.clicked.connect(self.slotScrollToAria2)
        scrollToAshoreBtn.clicked.connect(self.slotScrollToAshore)
        self.trackerBtn.clicked.connect(self.slotTracker)
        self.saveBtn.clicked.connect(self.slotSaveConf)
        self.rpcPortChangeableComboBox.currentIndexChanged.connect(self.slotRpcPortChangeable)
        self.rpcPortLineEdit.textChanged.connect(self.updateRpcAddress)
        self.rpcListenAllComboBox.currentIndexChanged.connect(self.slotRpcListenAllChanged)
        self.rpcSecretRevealBtn.clicked.connect(self.slotToggleRpcSecret)
        self.rpcSecretCopyBtn.clicked.connect(self.slotCopyRpcSecret)
        self.updateRpcSecretVisibility()
    
    def updateSettingPage(self, aria2Config:dict):
        self.AshoreConfig = self.getAshoreConfig()
        self.updateAria2Setting(aria2Config)
        self.updateAhoreSetting(self.AshoreConfig)

    def updateAria2Setting(self, aria2Config:dict):
        aria2Config = dict(aria2Config)
        aria2Config.update(self.readLocalRpcConfig())
        self.globalAria2Conf = aria2Config
        self.pathLineEdit.setText(aria2Config['dir'])
        self.maxDownloadsSpin.setValue(int(aria2Config['max-concurrent-downloads']))
        self.maConnectionSpin.setValue(int(aria2Config['max-connection-per-server']))
        self.userAgentLineEdit.setText(aria2Config['user-agent'])
        self.setMaxLimit(aria2Config['max-overall-upload-limit'], 'upload')
        self.setMaxLimit(aria2Config['max-overall-download-limit'], 'download')
        self.rpcPortLineEdit.setText(aria2Config['rpc-listen-port'])
        self.setBoolOption(self.rpcListenAllComboBox, aria2Config.get('rpc-listen-all', False))
        self.rpcSecretLineEdit.setText(aria2Config.get('rpc-secret', ''))
        self.updateRpcAddress()
        self.updateRpcSecretVisibility()
        self.btTracker.setText(aria2Config['bt-tracker'])
        self.showTrackerStatus()

    def updateAhoreSetting(self, ashoreConfig:dict):
        self.trackerInfo.setText(ashoreConfig['trackers_list_time'])
        self.trackerSource = ashoreConfig['trackers_list_source']
        self.showTrackerStatus()
        self.setBoolOption(self.withAria2QuitComboBox, ashoreConfig['quit_with_aria2'])
        self.setBoolOption(self.rpcPortChangeableComboBox, ashoreConfig['rpc_port_changeable'])
        self.updateIntervalSpin.setValue(int(ashoreConfig['update_interval']))
        self.rpcPortLineEdit.setEnabled(ashoreConfig['rpc_port_changeable'])
        languageIndex = self.languageComboBox.findData(ashoreConfig.get('language', 'zh_CN'))
        self.languageComboBox.setCurrentIndex(max(0, languageIndex))

    def setMaxLimit(self, value, which:str):
        #将running中的aria2限速配置显示在settingpage上
        tempNum = 0
        tempIndex = 0
        #若限速以单位结尾
        if value[-1] == 'G' or value[-1] == 'g':
            tempNum = int(value[:-1])
            tempIndex = 3
        if value[-1] == 'M' or value[-1] == 'm':
            tempNum = int(value[:-1])
            tempIndex = 2
        elif  value[-1] == 'K' or value[-1] == 'k':
            tempNum = int(value[:-1])
            tempIndex = 1
        elif  value[-1] == 'B':
            tempNum = int(value[:-1])
            tempIndex = 0
        else:
            #若限速无单位结尾为纯byte的数字
            value = int(value)
            if value < 1024:
                tempNum = value
                tempIndex = 0
            elif value < 1048576:
                tempNum = int(value/1024)
                tempIndex = 1
            elif value < 1073741824:
                tempNum = int(value/1048576)
                tempIndex = 2
            else:
                tempNum = int(value/1073741824)
                tempIndex = 3
        if which == 'upload':
            self.uploadLimitSpin.setValue(tempNum)
            self.uploadLimitComboBox.setCurrentIndex(tempIndex)
        elif which == 'download':
            self.downloadLimitSpin.setValue(tempNum)
            self.downloadLimitComboBox.setCurrentIndex(tempIndex)

    def getMaxLimit(self, which:str) -> str:
        #将settingpage上带单位的限速设置写入aria2.conf
        tempNum = 0
        tempIndex = 0
        if which == 'upload':
            tempNum = self.uploadLimitSpin.value()
            tempIndex = self.uploadLimitComboBox.currentIndex()
        elif which == 'download':
            tempNum = self.downloadLimitSpin.value()
            tempIndex = self.downloadLimitComboBox.currentIndex()
        if tempIndex == 0:
            return str(tempNum)
        elif tempIndex == 1:
            return str(tempNum) + 'K'
        elif tempIndex == 2:
            return str(tempNum) + 'M'
        elif tempIndex == 3:
            return str(tempNum) + 'G'

    def getBoolOption(self, boolObject:QComboBox) -> str:
        index = boolObject.currentIndex()
        if index == 0:
            return 'true'
        elif index == 1:
            return 'false'

    def setBoolOption(self, boolObject:QComboBox, flag:bool) -> None:
        if flag == True:
            boolObject.setCurrentIndex(0)
        elif flag == False:
            boolObject.setCurrentIndex(1)

    def getAshoreConfig(self) -> dict:
        ashoreConfig = configparser.ConfigParser()
        ashoreConfig.read([str(RESOURCE_DIR / 'config/ashore.conf'), self.ashoreConfPath], encoding='UTF-8')
        tempDict = {}
        for key in type(self).AshoreConfig:
            value = ashoreConfig.get('global', key)
            if value == 'true':
                value = True
            elif value == 'false':
                value = False
            tempDict[key] = value
        return tempDict

    def readLocalRpcConfig(self) -> dict:
        options = {'rpc-listen-port': '6801', 'rpc-listen-all': False, 'rpc-secret': ''}
        try:
            with open(self.aria2ConfPath, encoding='utf-8') as file:
                for line in file:
                    stripped = line.strip()
                    if not stripped or stripped.startswith(('#', ';')) or '=' not in stripped:
                        continue
                    key, value = stripped.split('=', 1)
                    key = key.strip()
                    if key in options:
                        options[key] = value.strip()
        except OSError:
            return options
        options['rpc-listen-all'] = str(options['rpc-listen-all']).lower() == 'true'
        return options

    def readLocalAria2Config(self) -> dict:
        options = {
            'dir': os.path.expanduser('~/Downloads'),
            'user-agent': '',
            'max-concurrent-downloads': '5',
            'max-connection-per-server': '1',
            'max-overall-upload-limit': '0',
            'max-overall-download-limit': '0',
            'rpc-listen-port': '6801',
            'bt-tracker': '',
        }
        try:
            with open(self.aria2ConfPath, encoding='utf-8') as file:
                for line in file:
                    stripped = line.strip()
                    if not stripped or stripped.startswith(('#', ';')) or '=' not in stripped:
                        continue
                    key, value = stripped.split('=', 1)
                    key = key.strip()
                    if key in options:
                        options[key] = os.path.expandvars(value.strip())
        except OSError:
            pass
        options.update(self.readLocalRpcConfig())
        return options

    def slotDir(self):
        path = QFileDialog.getExistingDirectory(self,'Open dir', self.pathLineEdit.text(), QFileDialog.Option.ShowDirsOnly)
        if path != '':
            self.pathLineEdit.setText(path)

    def slotTracker(self):
        self.saveBtn.setEnabled(False)
        self.trackerBtn.setEnabled(False)
        self.trackerBtn.setText('更新中...')
        #交给线程处理，以免主界面卡死
        self.trakersThreading = Thread()
        self.trakersThreading.sinOut.connect(self.slotShowTrakers)
        self.trakersThreading.start()

    def showTrackerStatus(self):
        count = len(parseTrackers(self.btTracker.toPlainText()))
        source = urllib.parse.urlsplit(self.trackerSource).netloc if self.trackerSource else '手动配置'
        self.trackerStatus.setText(f'当前列表 {count} 条；来源：{source}。列表数量不代表连接有效。')

    def slotShowTrakers(self, trackers:list, sourceOrError:str):
        if not trackers:
            self.trackerStatus.setText(f'更新失败：{sourceOrError}；保留原列表。')
            self.trackerBtn.setText('更新失败')
        else:
            self.trackerSource = sourceOrError
            self.trackerInfo.setText(time.strftime("%Y.%m.%d %H:%M", time.localtime()))
            self.btTracker.setText(','.join(trackers))
            source = urllib.parse.urlsplit(sourceOrError).netloc
            self.trackerStatus.setText(f'获取 {len(trackers)} 条；来源：{source}。尚未保存。')
            self.trackerBtn.setText('更新Tracker')
        self.trackerBtn.setEnabled(True)
        self.saveBtn.setEnabled(True)

    def slotSaveConf(self) -> None:
        #用户配置界面有的选项
        UserAria2Conf = {
            'dir'                       :   self.pathLineEdit.text(),
            'bt-tracker'                :   ','.join(parseTrackers(self.btTracker.toPlainText())),
            'max-concurrent-downloads'  :   str(self.maxDownloadsSpin.value()),
            'max-connection-per-server' :   str(self.maConnectionSpin.value()),
            'user-agent'                :   self.userAgentLineEdit.text(),
            'max-overall-upload-limit'  :   self.getMaxLimit('upload'),
            'max-overall-download-limit':   self.getMaxLimit('download'),
            'rpc-listen-port'           :   self.rpcPortLineEdit.text(),
            'rpc-listen-all'            :   self.getBoolOption(self.rpcListenAllComboBox),
            }
        rpcExternal = UserAria2Conf['rpc-listen-all'] == 'true'
        if rpcExternal:
            if not self.rpcSecretLineEdit.text():
                self.rpcSecretLineEdit.setText(secrets.token_urlsafe(32))
            UserAria2Conf['rpc-secret'] = self.rpcSecretLineEdit.text()
        UserAshoreConf ={
            'trackers_list_time'    :   self.trackerInfo.text(),
            'trackers_list_source'  :   self.trackerSource,
            'quit_with_aria2'       :   self.getBoolOption(self.withAria2QuitComboBox),
            'update_interval'       :   str(self.updateIntervalSpin.value()),
            'rpc_port_changeable'   :   self.getBoolOption(self.rpcPortChangeableComboBox),
            'language'              :   self.languageComboBox.currentData(),
        }
        oldRpc = self.readLocalRpcConfig()
        removeKeys = set() if rpcExternal else {'rpc-secret'}
        aria2Saved = self.saveAria2Conf(UserAria2Conf, removeKeys) == 0
        if aria2Saved:
            running_options = {key: value for key, value in UserAria2Conf.items()
                               if key not in ('rpc-listen-port', 'rpc-listen-all', 'rpc-secret')}
            oldValues = {
                'rpc-listen-port': str(oldRpc.get('rpc-listen-port', '')),
                'rpc-listen-all': 'true' if oldRpc.get('rpc-listen-all') else 'false',
                'rpc-secret': str(oldRpc.get('rpc-secret', '')),
            }
            rpcChanged = any(oldValues[key] != str(UserAria2Conf.get(key, ''))
                             for key in ('rpc-listen-port', 'rpc-listen-all', 'rpc-secret'))
            if not rpcExternal and oldRpc.get('rpc-secret'):
                rpcChanged = True
            self.aria2ConfSinOut.emit({'runtime': running_options, 'rpcChanged': rpcChanged})
        else:
            self.trackerStatus.setText('aria2 配置未能保存，请检查配置目录权限。')
            self.aria2ConfSinOut.emit({'ResultError': 'aria2 配置写入失败'})
        if self.saveAshoreConf(UserAshoreConf) == 0:
            if aria2Saved:
                self.showTrackerStatus()
            UserAshoreConf.update({'isSaved' : '保存成功'})                    #成功则增加一条信息‘保存成功’
            self.ashoreConfigSinOut.emit(UserAshoreConf)                        #发射信号
        else:
            UserAshoreConf.update({'isSaved' : '保存失败'})                    #成功则增加一条信息‘保存失败’
            self.ashoreConfigSinOut.emit(UserAshoreConf)                        #发射信号

    def saveAria2Conf(self, UserAria2Conf:dict, removeKeys=None) -> int:
        removeKeys = set(removeKeys or ())
        remaining = dict(UserAria2Conf)
        lines = []
        try:
            with open(self.aria2ConfPath, encoding='utf-8') as file:
                for line in file:
                    stripped = line.strip()
                    if stripped == '[global]':
                        continue
                    key = stripped.split('=', 1)[0].strip() if '=' in stripped else ''
                    if key in removeKeys:
                        continue
                    if key in remaining:
                        lines.append(f'{key}={remaining.pop(key)}\n')
                    else:
                        lines.append(line)
            lines.extend(f'{key}={value}\n' for key, value in remaining.items())
            with open(self.aria2ConfPath, 'w', encoding='utf-8') as file:
                file.writelines(lines)
        except OSError:
            return -1
        self.globalAria2Conf.update(UserAria2Conf)
        for key in removeKeys:
            self.globalAria2Conf.pop(key, None)
        return 0

    def slotRpcListenAllChanged(self, index:int) -> None:
        if index == 0 and not self.rpcSecretLineEdit.text():
            self.rpcSecretLineEdit.setText(secrets.token_urlsafe(32))
        self.updateRpcSecretVisibility()

    def updateRpcSecretVisibility(self) -> None:
        visible = self.rpcListenAllComboBox.currentIndex() == 0
        self.rpcSecretLabel.setVisible(visible)
        self.rpcSecretLineEdit.setVisible(visible)
        self.rpcSecretRevealBtn.setVisible(visible)
        self.rpcSecretCopyBtn.setVisible(visible)

    def slotToggleRpcSecret(self) -> None:
        showing = self.rpcSecretLineEdit.echoMode() == QLineEdit.EchoMode.Normal
        self.rpcSecretLineEdit.setEchoMode(
            QLineEdit.EchoMode.Password if showing else QLineEdit.EchoMode.Normal)
        self.rpcSecretRevealBtn.setText('显示' if showing else '隐藏')

    def slotCopyRpcSecret(self) -> None:
        QApplication.clipboard().setText(self.rpcSecretLineEdit.text())
        self.rpcSecretCopyBtn.setText('已复制')
        QTimer.singleShot(1500, lambda: self.rpcSecretCopyBtn.setText('复制'))

    def updateRpcAddress(self) -> None:
        port = self.rpcPortLineEdit.text() or '6801'
        self.rpcProtocolLabel.setText(
            f'HTTP 轮询：http://127.0.0.1:{port}/jsonrpc\n'
            f'WebSocket 通知：ws://127.0.0.1:{port}/jsonrpc')

    def setConnectionStatus(self, httpStatus:str, websocketStatus:str, aria2Version:str='') -> None:
        version = f'；aria2 {aria2Version}' if aria2Version else ''
        self.rpcConnectionLabel.setText(
            f'HTTP：{httpStatus}；WebSocket：{websocketStatus}{version}')

    def saveAshoreConf(self, UserAshoreConf:dict) -> int:
        configFile = configparser.ConfigParser()
        configFile.read(self.ashoreConfPath, encoding='UTF-8')
        #更新程序内存中configFile与运行中Ashore的配置，准备发送
        for key,value in UserAshoreConf.items():
            configFile.set('global', key, value)                        #修改Ashore配置文件
        try:
            with open(self.ashoreConfPath, 'w', encoding='utf-8') as file:
                configFile.write(file)
        except OSError:
            return -1
        self.AshoreConfig = self.getAshoreConfig()
        return 0

    def slotRpcPortChangeable(self, index:int=1) -> None:
        #将rpc port LineEdit设置为相应状态
        self.rpcPortLineEdit.setEnabled(not index)

    def slotScrollToAria2(self) -> None:
        self.scrollArea.verticalScrollBar().setValue(self.aria2SettingLabel.y())

    def slotScrollToAshore(self) -> None:
        self.scrollArea.verticalScrollBar().setValue(self.ashoreSettingLabel.y())
