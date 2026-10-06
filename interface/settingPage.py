"""Ashore and aria2 settings interface."""

import json
import secrets

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFileSystemModel
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QCheckBox,
    QComboBox,
    QCompleter,
    QFileDialog,
    QGridLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.configStore import readAshore, readOptions, writeAshore, writeOptions
from core.trackerManager import TrackerManager, displayTime
from core.trackerSources import (
    DEFAULT_SOURCE_KEYS,
    TRACKER_SOURCE_CATALOG,
    parseTrackers,
    sourceUrls,
    validSourceUrl,
)
from interface.actionIcons import actionIcon
from interface.controls import AshoreComboBox, AshoreSpinBox
from interface.languageManager import LANGUAGES, translate
from interface.settingItem import SettingItem
from interface.trackerManagerPanel import TrackerManagerPanel
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
        'theme_mode', 'accent_color', 'show_aria2_status',
        'tracker_source_keys', 'tracker_custom_sources',
    )

    def __init__(self):
        super().__init__()
        self.ashoreConfPath = self.ashoreConfDir + '/ashore.conf'
        ensureConfig('ashore.conf')
        ensureConfig('aria2.conf')
        self.ashoreConfig = self.loadAshoreConfig()
        self.language = self.ashoreConfig.get('language', 'zh_CN')
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

    def tr(self, key):
        return translate(self.language, key)

    def initUI(self):
        self.setProperty('settingsPage', True)

        settingsLayout = QVBoxLayout()
        settingsLayout.setContentsMargins(12, 0, 12, 14)
        settingsLayout.setSpacing(4)
        self.settingItems = []

        self.aria2SettingLabel = QLabel()
        self.aria2SettingLabel.setProperty('settingsSectionTitle', True)
        settingsLayout.addWidget(self.aria2SettingLabel)

        self.basicSettingLabel = QLabel()
        self.basicSettingLabel.setProperty('settingsSubTitle', True)
        settingsLayout.addWidget(self.basicSettingLabel)

        completer = QCompleter()
        model = QFileSystemModel()
        model.setRootPath(str(systemDownloadDirectory()))
        completer.setModel(model)

        self.pathLineEdit = QLineEdit(str(systemDownloadDirectory()))
        self.pathLineEdit.setCompleter(completer)
        self.pathLineEdit.setMinimumWidth(260)
        self.pathLineEdit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.pathBtn = QPushButton()
        pathLayout = QHBoxLayout()
        pathLayout.addWidget(self.pathLineEdit, 1)
        pathLayout.addWidget(self.pathBtn)
        self.defaultDownloadDirLabel = QLabel()
        self.addSettingItem(settingsLayout, self.defaultDownloadDirLabel, pathLayout)

        self.maxDownloadsSpin = AshoreSpinBox()
        self.maxDownloadsSpin.setRange(1, 100)
        self.maxDownloadsSpin.setMaximumWidth(100)
        self.maxDownloadsLabel = QLabel()
        self.addSettingItem(settingsLayout, self.maxDownloadsLabel, self.maxDownloadsSpin)

        self.maxConnectionSpin = AshoreSpinBox()
        self.maxConnectionSpin.setRange(1, 16)
        self.maxConnectionSpin.setMaximumWidth(100)
        self.maxConnectionsLabel = QLabel()
        self.addSettingItem(settingsLayout, self.maxConnectionsLabel, self.maxConnectionSpin)

        self.userAgentComboBox = AshoreComboBox()
        self.userAgentComboBox.setEditable(True)
        self.userAgentComboBox.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.userAgentComboBox.addItems(self.ashoreConfig['user_agent_presets'])
        self.userAgentComboBox.setMinimumWidth(260)
        self.userAgentComboBox.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.userAgentLabel = QLabel('User Agent:')
        self.addSettingItem(settingsLayout, self.userAgentLabel, self.userAgentComboBox)

        self.uploadLimitLabel = QLabel()
        self.uploadLimitSpin = AshoreSpinBox()
        self.uploadLimitSpin.setRange(0, 1024)
        self.uploadLimitSpin.setMinimumWidth(150)
        self.uploadLimitComboBox = AshoreComboBox()
        self.uploadLimitComboBox.addItems(['B/s', 'KB/s', 'MB/s', 'GB/s'])

        self.downloadLimitLabel = QLabel()
        self.downloadLimitSpin = AshoreSpinBox()
        self.downloadLimitSpin.setRange(0, 1024)
        self.downloadLimitSpin.setMinimumWidth(150)
        self.downloadLimitComboBox = AshoreComboBox()
        self.downloadLimitComboBox.addItems(['B/s', 'KB/s', 'MB/s', 'GB/s'])

        transLayout = QGridLayout()
        transLayout.addWidget(self.uploadLimitLabel, 0, 0)
        transLayout.addWidget(self.uploadLimitSpin, 0, 1)
        transLayout.addWidget(self.uploadLimitComboBox, 0, 2)
        transLayout.addWidget(self.downloadLimitLabel, 1, 0)
        transLayout.addWidget(self.downloadLimitSpin, 1, 1)
        transLayout.addWidget(self.downloadLimitComboBox, 1, 2)
        transLayout.setColumnStretch(3, 1)
        self.speedLimitsLabel = QLabel()
        self.addSettingItem(settingsLayout, self.speedLimitsLabel, transLayout)

        self.rpcPortLineEdit = QLineEdit()
        self.rpcPortLineEdit.setMaximumWidth(200)
        self.rpcPortLabel = QLabel()
        self.addSettingItem(settingsLayout, self.rpcPortLabel, self.rpcPortLineEdit)

        self.httpEndpointLabel = QLabel()
        self.httpEndpointLabel.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.httpStatusLabel = QLabel()
        httpLayout = QHBoxLayout()
        httpLayout.addWidget(self.httpEndpointLabel)
        httpLayout.addWidget(self.httpStatusLabel)
        httpLayout.addStretch(10)
        self.httpPollingLabel = QLabel()
        self.addSettingItem(settingsLayout, self.httpPollingLabel, httpLayout)

        self.websocketEndpointLabel = QLabel()
        self.websocketEndpointLabel.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.websocketStatusLabel = QLabel()
        websocketLayout = QHBoxLayout()
        websocketLayout.addWidget(self.websocketEndpointLabel)
        websocketLayout.addWidget(self.websocketStatusLabel)
        websocketLayout.addStretch(10)
        self.websocketLabel = QLabel()
        self.addSettingItem(settingsLayout, self.websocketLabel, websocketLayout)

        self.aria2VersionLabel = QLabel('—')
        self.aria2VersionFormLabel = QLabel()
        self.addSettingItem(
            settingsLayout, self.aria2VersionFormLabel, self.aria2VersionLabel)

        self.rpcListenAllComboBox = AshoreComboBox()
        self.rpcListenAllComboBox.addItems(['', ''])
        self.rpcListenAllComboBox.setCurrentIndex(1)
        listenAllLayout = QHBoxLayout()
        listenAllLayout.addWidget(self.rpcListenAllComboBox)
        listenAllLayout.addStretch(10)
        self.externalRpcLabel = QLabel()
        self.addSettingItem(settingsLayout, self.externalRpcLabel, listenAllLayout)

        self.rpcSecretLineEdit = QLineEdit()
        self.rpcSecretLineEdit.setReadOnly(True)
        self.rpcSecretLineEdit.setMinimumWidth(220)
        self.rpcSecretLineEdit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.rpcSecret = ''
        self.rpcSecretVisible = False
        self.rpcSecretRevealBtn = QPushButton()
        self.rpcSecretCopyBtn = QPushButton()
        tokenLayout = QHBoxLayout()
        tokenLayout.addWidget(self.rpcSecretLineEdit, 1)
        tokenLayout.addWidget(self.rpcSecretRevealBtn)
        tokenLayout.addWidget(self.rpcSecretCopyBtn)
        self.rpcSecretLabel = QLabel()
        self.addSettingItem(settingsLayout, self.rpcSecretLabel, tokenLayout)

        self.btSettingLabel = QLabel()
        self.btSettingLabel.setProperty('settingsSubTitle', True)
        settingsLayout.addWidget(self.btSettingLabel)

        self.trackers = []
        self.trackerSource = self.ashoreConfig.get('trackers_list_source', '')
        self.trackerHealthSummary = None

        self.trackerSourceChecks = {}
        trackerSourceLayout = QVBoxLayout()
        trackerSourceLayout.setContentsMargins(0, 0, 0, 0)
        trackerSourceLayout.setSpacing(5)
        for source in TRACKER_SOURCE_CATALOG:
            checkBox = QCheckBox(source['name'])
            checkBox.setToolTip(source['url'])
            self.trackerSourceChecks[source['key']] = checkBox
            trackerSourceLayout.addWidget(checkBox)

        self.customTrackerRows = []
        self.customTrackerSourceLayout = QVBoxLayout()
        self.customTrackerSourceLayout.setContentsMargins(0, 0, 0, 0)
        self.customTrackerSourceLayout.setSpacing(4)
        trackerSourceLayout.addLayout(self.customTrackerSourceLayout)

        self.customTrackerSourceInput = QLineEdit()
        self.customTrackerSourceInput.setPlaceholderText('https://example.org/trackers.txt')
        self.addTrackerSourceBtn = QPushButton()
        customSourceInputLayout = QHBoxLayout()
        customSourceInputLayout.setContentsMargins(0, 0, 0, 0)
        customSourceInputLayout.addWidget(self.customTrackerSourceInput, 1)
        customSourceInputLayout.addWidget(self.addTrackerSourceBtn)
        trackerSourceLayout.addLayout(customSourceInputLayout)

        self.trackerSourcesLabel = QLabel()
        self.addSettingItem(
            settingsLayout, self.trackerSourcesLabel, trackerSourceLayout)

        self.autoTrackerComboBox = AshoreComboBox()
        self.autoTrackerComboBox.addItems(['', ''])
        self.autoTrackerHintLabel = QLabel()
        autoTrackerLayout = QHBoxLayout()
        autoTrackerLayout.addWidget(self.autoTrackerComboBox)
        autoTrackerLayout.addWidget(self.autoTrackerHintLabel)
        autoTrackerLayout.addStretch(1)
        self.autoTrackerLabel = QLabel()
        self.addSettingItem(settingsLayout, self.autoTrackerLabel, autoTrackerLayout)

        self.trackerStatus = QLabel('')
        self.trackerStatus.setWordWrap(True)
        self.trackerInfo = QLabel('')
        self.trackerBtn = QPushButton()
        trackerActions = QHBoxLayout()
        trackerActions.setContentsMargins(0, 0, 0, 0)
        trackerActions.addWidget(self.trackerInfo)
        trackerActions.addStretch(1)
        trackerActions.addWidget(self.trackerBtn)
        trackerOverviewLayout = QVBoxLayout()
        trackerOverviewLayout.setContentsMargins(0, 0, 0, 0)
        trackerOverviewLayout.setSpacing(6)
        trackerOverviewLayout.addLayout(trackerActions)
        self.btTrackerLabel = QLabel()
        self.addSettingItem(
            settingsLayout, self.btTrackerLabel, trackerOverviewLayout)

        self.trackerToggle = QToolButton()
        self.trackerToggle.setCheckable(True)
        self.trackerToggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.trackerToggle.setProperty('trackerToggle', True)
        self.trackerToggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trackerPanel = TrackerManagerPanel(
            self.trackers, self.language, self)
        self.trackerPanel.setVisible(False)
        settingsLayout.addWidget(
            self.trackerToggle, 0, Qt.AlignmentFlag.AlignLeft)
        settingsLayout.addWidget(self.trackerPanel)

        self.ashoreSettingLabel = QLabel()
        self.ashoreSettingLabel.setProperty('settingsSectionTitle', True)
        settingsLayout.addWidget(self.ashoreSettingLabel)

        self.withAria2QuitComboBox = AshoreComboBox()
        self.withAria2QuitComboBox.addItems(['', ''])
        quitWithAria2Layout = QHBoxLayout()
        quitWithAria2Layout.addWidget(self.withAria2QuitComboBox)
        quitWithAria2Layout.addStretch(10)
        self.quitWithAria2Label = QLabel()
        self.addSettingItem(settingsLayout, self.quitWithAria2Label, quitWithAria2Layout)

        self.showAria2StatusComboBox = AshoreComboBox()
        self.showAria2StatusComboBox.addItems(['', ''])
        showAria2StatusLayout = QHBoxLayout()
        showAria2StatusLayout.addWidget(self.showAria2StatusComboBox)
        showAria2StatusLayout.addStretch(10)
        self.showAria2StatusLabel = QLabel()
        self.addSettingItem(
            settingsLayout, self.showAria2StatusLabel, showAria2StatusLayout)

        self.updateIntervalSpin = AshoreSpinBox()
        self.updateIntervalSpin.setRange(500, 10000)
        self.updateIntervalSpin.setSingleStep(100)
        self.updateIntervalSpin.setMaximumWidth(110)
        self.updateIntervalUnitLabel = QLabel()
        updateIntervalLayout = QHBoxLayout()
        updateIntervalLayout.addWidget(self.updateIntervalSpin)
        updateIntervalLayout.addWidget(self.updateIntervalUnitLabel)
        self.refreshIntervalLabel = QLabel()
        self.addSettingItem(settingsLayout, self.refreshIntervalLabel, updateIntervalLayout)

        self.rpcPortChangeableComboBox = AshoreComboBox()
        self.rpcPortChangeableComboBox.addItems(['', ''])
        rpcPortChangeableLayout = QHBoxLayout()
        rpcPortChangeableLayout.addWidget(self.rpcPortChangeableComboBox)
        rpcPortChangeableLayout.addStretch(10)
        self.rpcChangeLabel = QLabel()
        self.addSettingItem(settingsLayout, self.rpcChangeLabel, rpcPortChangeableLayout)

        self.languageComboBox = AshoreComboBox()
        for code, name in LANGUAGES.items():
            self.languageComboBox.addItem(name, code)
        languageLayout = QHBoxLayout()
        languageLayout.addWidget(self.languageComboBox)
        languageLayout.addStretch(10)
        self.languageLabel = QLabel()
        self.addSettingItem(settingsLayout, self.languageLabel, languageLayout)

        self.trayIconStyleComboBox = AshoreComboBox()
        self.trayIconStyleComboBox.addItem('', 'colorful')
        self.trayIconStyleComboBox.addItem('', 'gray')
        trayIconLayout = QHBoxLayout()
        trayIconLayout.addWidget(self.trayIconStyleComboBox)
        trayIconLayout.addStretch(10)
        self.trayIconStyleLabel = QLabel()
        self.addSettingItem(settingsLayout, self.trayIconStyleLabel, trayIconLayout)

        self.themeModeComboBox = AshoreComboBox()
        for mode in THEME_MODES:
            self.themeModeComboBox.addItem('', mode)
        themeLayout = QHBoxLayout()
        themeLayout.addWidget(self.themeModeComboBox)
        themeLayout.addStretch(1)
        self.themeModeLabel = QLabel()
        self.addSettingItem(settingsLayout, self.themeModeLabel, themeLayout)

        self.accentComboBox = AshoreComboBox()
        self.accentComboBox.setEditable(True)
        for color in ACCENT_PRESETS:
            self.accentComboBox.addItem(color, color)
        self.accentButton = QPushButton()
        accentLayout = QHBoxLayout()
        accentLayout.addWidget(self.accentComboBox)
        accentLayout.addWidget(self.accentButton)
        accentLayout.addStretch(1)
        self.accentColorLabel = QLabel()
        self.addSettingItem(settingsLayout, self.accentColorLabel, accentLayout)

        settingsLayout.addStretch(1)
        settingWidget = QWidget()
        settingWidget.setProperty('settingsSurface', True)
        settingWidget.setLayout(settingsLayout)

        self.scrollToAria2Btn = QPushButton()
        self.scrollToAshoreBtn = QPushButton()
        self.saveBtn = QPushButton()
        self.saveBtn.setProperty('primaryAction', True)

        settingsNav = QWidget()
        settingsNav.setProperty('settingsSurface', True)
        scrollBtnLayout = QVBoxLayout(settingsNav)
        scrollBtnLayout.addWidget(self.scrollToAria2Btn)
        scrollBtnLayout.addWidget(self.scrollToAshoreBtn)
        scrollBtnLayout.addStretch(10)
        scrollBtnLayout.addWidget(self.saveBtn)
        scrollBtnLayout.setContentsMargins(2, 0, 6, 0)

        self.scrollArea = QScrollArea()
        self.scrollArea.setProperty('settingsScroll', True)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(settingWidget)
        self.scrollArea.viewport().setProperty('settingsSurface', True)

        mainLayout = QHBoxLayout(self)
        mainLayout.setContentsMargins(8, 10, 6, 8)
        mainLayout.setSpacing(0)
        mainLayout.addWidget(settingsNav)
        mainLayout.addWidget(self.scrollArea, 1)
        self.setMinimumWidth(700)

        self.pathBtn.clicked.connect(self.slotDir)
        self.scrollToAria2Btn.clicked.connect(self.slotScrollToAria2)
        self.scrollToAshoreBtn.clicked.connect(self.slotScrollToAshore)
        self.trackerBtn.clicked.connect(self.slotTracker)
        self.addTrackerSourceBtn.clicked.connect(
            lambda _checked=False: self.addCustomTrackerSource())
        self.trackerToggle.toggled.connect(self.toggleTrackerManager)
        self.trackerPanel.trackersChanged.connect(self.applyManagedTrackers)
        self.trackerPanel.healthSummaryChanged.connect(
            self.applyTrackerHealthSummary)
        self.saveBtn.clicked.connect(self.slotSaveConf)
        self.rpcPortChangeableComboBox.currentIndexChanged.connect(
            self.slotRpcPortChangeable)
        self.rpcPortLineEdit.textChanged.connect(self.updateEndpoints)
        self.rpcListenAllComboBox.currentIndexChanged.connect(
            self.toggleRpcAccess)
        self.rpcSecretRevealBtn.clicked.connect(self.toggleToken)
        self.rpcSecretCopyBtn.clicked.connect(self.copyToken)
        self.themeModeComboBox.currentIndexChanged.connect(self.previewTheme)
        self.accentComboBox.currentTextChanged.connect(self.previewTheme)
        self.accentButton.clicked.connect(self.pickAccent)

        self.loadTrackerSourceControls(self.ashoreConfig)
        self.retranslateUi()
        self.updateTokenRow()

    def setLanguage(self, language):
        self.language = language or 'zh_CN'
        self.retranslateUi()

    def addSettingItem(self, layout, label, field):
        item = SettingItem(label, field, self)
        layout.addWidget(item)
        self.settingItems.append(item)
        return item

    def retranslateUi(self):
        self.aria2SettingLabel.setText(
            f'<h3>{self.tr("aria2Settings")}</h3>')
        self.ashoreSettingLabel.setText(
            f'<h3>{self.tr("ashoreSettings")}</h3>')
        self.basicSettingLabel.setText(self.tr('basicSettings'))
        self.btSettingLabel.setText(self.tr('btSettings'))

        self.defaultDownloadDirLabel.setText(self.tr('defaultDownloadDir'))
        self.pathBtn.setText(self.tr('chooseDirectory'))
        self.maxDownloadsLabel.setText(self.tr('maxConcurrentDownloads'))
        self.maxConnectionsLabel.setText(self.tr('maxConnectionsServer'))
        self.speedLimitsLabel.setText(self.tr('speedLimits'))
        self.uploadLimitLabel.setText(self.tr('uploadLimit'))
        self.downloadLimitLabel.setText(self.tr('downloadLimit'))
        self.uploadLimitSpin.setSpecialValueText(self.tr('unlimited'))
        self.downloadLimitSpin.setSpecialValueText(self.tr('unlimited'))

        self.rpcPortLabel.setText(self.tr('rpcPort'))
        self.rpcPortLineEdit.setToolTip('Ashore RPC: 6801')
        self.rpcPortLineEdit.setPlaceholderText('6801')
        self.httpPollingLabel.setText(self.tr('httpPolling'))
        self.websocketLabel.setText(self.tr('websocketNotifications'))
        self.aria2VersionFormLabel.setText(self.tr('aria2Version'))
        self.externalRpcLabel.setText(self.tr('externalRpc'))
        self.rpcListenAllComboBox.setItemText(0, self.tr('yes'))
        self.rpcListenAllComboBox.setItemText(1, self.tr('no'))
        self.rpcSecretLabel.setText(self.tr('rpcToken'))

        self.trackerSourcesLabel.setText(self.tr('trackerSources'))
        self.addTrackerSourceBtn.setText(self.tr('addTrackerSource'))
        self.btTrackerLabel.setText(self.tr('trackerOverview'))
        self.trackerBtn.setText(
            self.tr('updateTracker')
            if self.trackerBtn.isEnabled()
            else self.tr('trackerUpdating'))
        self.trackerToggle.setText(self.tr('trackerManagement'))
        self.updateTrackerToggleIcon()
        self.trackerPanel.setLanguage(self.language)
        self.trackerInfo.setText(
            self.tr('lastTrackerUpdate').format(
                time=displayTime(self.trackerTime)))
        self.autoTrackerLabel.setText(self.tr('autoTracker'))
        self.autoTrackerHintLabel.setText(self.tr('autoTrackerHint'))
        self.autoTrackerComboBox.setItemText(0, self.tr('yes'))
        self.autoTrackerComboBox.setItemText(1, self.tr('no'))

        self.quitWithAria2Label.setText(self.tr('quitWithAria2'))
        self.showAria2StatusLabel.setText(self.tr('showAria2Status'))
        self.withAria2QuitComboBox.setItemText(0, self.tr('yes'))
        self.withAria2QuitComboBox.setItemText(1, self.tr('no'))
        self.showAria2StatusComboBox.setItemText(0, self.tr('yes'))
        self.showAria2StatusComboBox.setItemText(1, self.tr('no'))
        self.refreshIntervalLabel.setText(self.tr('refreshInterval'))
        self.updateIntervalUnitLabel.setText(self.tr('milliseconds'))
        self.rpcChangeLabel.setText(self.tr('allowRpcPortChange'))
        self.rpcPortChangeableComboBox.setItemText(0, self.tr('yes'))
        self.rpcPortChangeableComboBox.setItemText(1, self.tr('no'))
        self.languageLabel.setText(self.tr('interfaceLanguage'))
        self.trayIconStyleLabel.setText(self.tr('trayIconStyle'))
        self.trayIconStyleComboBox.setItemText(0, self.tr('colorful'))
        self.trayIconStyleComboBox.setItemText(1, self.tr('gray'))
        self.themeModeLabel.setText(self.tr('themeMode'))
        for index, key in enumerate(('followSystem', 'light', 'dark')):
            self.themeModeComboBox.setItemText(index, self.tr(key))
        self.accentColorLabel.setText(self.tr('accentColor'))
        self.accentButton.setText(self.tr('chooseColor'))
        self.scrollToAria2Btn.setText(self.tr('aria2Settings'))
        self.scrollToAshoreBtn.setText(self.tr('ashoreSettings'))
        self.saveBtn.setText(self.tr('saveSettings'))
        self.refreshRpcSecret()
        self.showTrackerStatus()

    def loadSettings(self, aria2Config: dict):
        self.ashoreConfig = self.loadAshoreConfig()
        self.loadAria2(aria2Config)
        self.loadAshore(self.ashoreConfig)

    def loadAria2(self, aria2Config: dict):
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
        self.trackers = parseTrackers(aria2Config['bt-tracker'])
        self.trackerHealthSummary = None
        self.trackerPanel.setTrackers(self.trackers)
        self.showTrackerStatus()


    def loadAshore(self, ashoreConfig: dict):
        self.trackerTime = ashoreConfig['trackers_list_time']
        self.trackerInfo.setText(
            self.tr('lastTrackerUpdate').format(
                time=displayTime(self.trackerTime)))
        self.trackerSource = ashoreConfig.get('trackers_list_source', '')
        self.loadTrackerSourceControls(ashoreConfig)
        self.setLanguage(ashoreConfig.get('language', self.language))
        self.showTrackerStatus()
        self.setBoolOption(
            self.withAria2QuitComboBox, ashoreConfig['quit_with_aria2'])
        self.setBoolOption(
            self.showAria2StatusComboBox,
            ashoreConfig.get('show_aria2_status', True))
        self.setBoolOption(
            self.rpcPortChangeableComboBox,
            ashoreConfig['rpc_port_changeable'])
        self.updateIntervalSpin.setValue(int(ashoreConfig['update_interval']))
        self.rpcPortLineEdit.setEnabled(
            ashoreConfig['rpc_port_changeable'])
        languageIndex = self.languageComboBox.findData(
            ashoreConfig.get('language', 'zh_CN'))
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
            validColor(
                ashoreConfig.get(
                    'accent_color', ACCENT_PRESETS[0])))
    def setMaxLimit(self, value, which: str):
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

    def getMaxLimit(self, which: str) -> str:
        if which == 'upload':
            amount = self.uploadLimitSpin.value()
            unitIndex = self.uploadLimitComboBox.currentIndex()
        else:
            amount = self.downloadLimitSpin.value()
            unitIndex = self.downloadLimitComboBox.currentIndex()
        return f'{amount}{("", "K", "M", "G")[unitIndex]}'

    def getBoolOption(self, boolObject: QComboBox) -> str:
        return 'true' if boolObject.currentIndex() == 0 else 'false'

    def setBoolOption(self, boolObject: QComboBox, flag: bool) -> None:
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
            elif key in (
                    'user_agent_presets', 'tracker_source_keys',
                    'tracker_custom_sources'):
                try:
                    value = json.loads(value)
                except (TypeError, ValueError):
                    value = []
                if not isinstance(value, list):
                    value = []
                if key == 'user_agent_presets':
                    value = [
                        item for item in value
                        if isinstance(item, str) and item.strip()]
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
        path = QFileDialog.getExistingDirectory(
            self, self.tr('chooseDirectory'),
            self.pathLineEdit.text(), QFileDialog.Option.ShowDirsOnly)
        if path:
            self.pathLineEdit.setText(path)

    def slotTracker(self):
        sources = self.selectedTrackerSourceUrls()
        if not sources:
            self.showTrackerMessage(self.tr('noTrackerSources'))
            return
        self.saveBtn.setEnabled(False)
        self.trackerBtn.setEnabled(False)
        self.trackerBtn.setText(self.tr('trackerUpdating'))
        if not self.trackerManager.start(force=True, sources=sources):
            self.trackerBtn.setEnabled(True)
            self.saveBtn.setEnabled(True)
            self.trackerBtn.setText(self.tr('updateTracker'))
    def startAutoTracker(self):
        return self.trackerManager.start()


    def selectedTrackerSourceKeys(self):
        return [
            key for key, checkBox in self.trackerSourceChecks.items()
            if checkBox.isChecked()]

    def customTrackerSources(self):
        return [
            {'url': row['checkBox'].text(), 'enabled': row['checkBox'].isChecked()}
            for row in self.customTrackerRows]

    def selectedTrackerSourceUrls(self):
        return sourceUrls(
            self.selectedTrackerSourceKeys(), self.customTrackerSources())

    def loadTrackerSourceControls(self, ashoreConfig):
        selectedKeys = ashoreConfig.get(
            'tracker_source_keys', list(DEFAULT_SOURCE_KEYS))
        for key, checkBox in self.trackerSourceChecks.items():
            checkBox.setChecked(key in selectedKeys)

        for row in list(self.customTrackerRows):
            row['widget'].deleteLater()
        self.customTrackerRows.clear()
        for item in ashoreConfig.get('tracker_custom_sources', []):
            if isinstance(item, str):
                self.addCustomTrackerSource(item, True)
            elif isinstance(item, dict):
                self.addCustomTrackerSource(
                    item.get('url', ''), item.get('enabled', True))

    def addCustomTrackerSource(self, url=None, enabled=True):
        value = (
            self.customTrackerSourceInput.text()
            if url is None else str(url))
        value = validSourceUrl(value)
        if not value:
            if url is None:
                self.showTrackerMessage(self.tr('invalidTrackerSource'))
            return
        known = {
            source['url'] for source in TRACKER_SOURCE_CATALOG}
        known.update(
            row['checkBox'].text() for row in self.customTrackerRows)
        if value in known:
            if url is None:
                self.showTrackerMessage(self.tr('duplicateTrackerSource'))
            return

        rowWidget = QWidget()
        rowLayout = QHBoxLayout(rowWidget)
        rowLayout.setContentsMargins(0, 0, 0, 0)
        rowLayout.setSpacing(6)
        checkBox = QCheckBox(value)
        checkBox.setChecked(bool(enabled))
        removeBtn = QPushButton('×')
        removeBtn.setFixedSize(26, 26)
        rowLayout.addWidget(checkBox, 1)
        rowLayout.addWidget(removeBtn)
        row = {'widget': rowWidget, 'checkBox': checkBox}
        self.customTrackerRows.append(row)
        self.customTrackerSourceLayout.addWidget(rowWidget)
        removeBtn.clicked.connect(
            lambda _checked=False, row=row: self.removeCustomTrackerSource(row))
        if url is None:
            self.customTrackerSourceInput.clear()
            self.showTrackerStatus()

    def removeCustomTrackerSource(self, row):
        if row not in self.customTrackerRows:
            return
        self.customTrackerRows.remove(row)
        self.customTrackerSourceLayout.removeWidget(row['widget'])
        row['widget'].deleteLater()
        self.showTrackerStatus()

    def toggleTrackerManager(self, expanded):
        self.trackerPanel.setVisible(expanded)
        self.updateTrackerToggleIcon()

    def updateTrackerToggleIcon(self):
        name = 'chevron-down' if self.trackerToggle.isChecked() else 'chevron-right'
        self.trackerToggle.setIcon(actionIcon(name, size=16))

    def showTrackerStatus(self):
        self.trackerInfo.setText(
            self.tr('lastTrackerUpdate').format(
                time=displayTime(self.trackerTime)))

    def applyManagedTrackers(self, trackers):
        self.trackers = list(trackers)
        self.trackerSource = ''
        self.trackerHealthSummary = None
        self.showTrackerStatus()

    def applyTrackerHealthSummary(self, healthy, failed):
        self.trackerHealthSummary = (healthy, failed)
        self.showTrackerStatus()

    def showTrackerMessage(self, message):
        self.trackerInfo.setText(message)


    def applyTrackerUpdate(self, trackers, sources, timestamp):
        self.trackerSource = json.dumps(sources, ensure_ascii=False)
        self.trackerTime = timestamp
        self.trackerInfo.setText(
            self.tr('lastTrackerUpdate').format(time=displayTime(timestamp)))
        self.trackers = list(trackers)
        self.trackerHealthSummary = None
        self.trackerPanel.setTrackers(self.trackers)
        self.trackerInfo.setText(
            self.tr('lastTrackerUpdate').format(
                time=displayTime(timestamp)))
        self.trackerBtn.setText(self.tr('updateTracker'))
        self.trackerBtn.setEnabled(True)
        self.saveBtn.setEnabled(True)
        self.trackerRuntimeChanged.emit(
            {'bt-tracker': ','.join(trackers)})

    def applyTrackerFailure(self, error):
        self.trackerInfo.setText(
            self.tr('trackerUpdateFailed').format(error=error))
        self.trackerBtn.setText(self.tr('trackerFailed'))
        self.trackerBtn.setEnabled(True)
        self.saveBtn.setEnabled(True)
    def slotSaveConf(self) -> None:
        self.trackers = self.trackerPanel.trackers()
        aria2Values = {
            'dir'                       :   self.pathLineEdit.text(),
            'bt-tracker'                :   ','.join(self.trackers),
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
            'show_aria2_status'     :   self.getBoolOption(self.showAria2StatusComboBox),
            'trackers_auto_update'  :   self.getBoolOption(self.autoTrackerComboBox),
            'tracker_source_keys'   :   json.dumps(
                self.selectedTrackerSourceKeys(), ensure_ascii=False),
            'tracker_custom_sources':   json.dumps(
                self.customTrackerSources(), ensure_ascii=False),
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

    def saveAria2Conf(self, aria2Values: dict, removeKeys=None) -> int:
        removeKeys = set(removeKeys or ())
        if not writeOptions(self.aria2ConfPath, aria2Values, removeKeys):
            return -1
        return 0

    def toggleRpcAccess(self, index: int) -> None:
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
        self.rpcSecretLineEdit.setText(
            self.rpcSecret if self.rpcSecretVisible else mask)
        self.rpcSecretRevealBtn.setText(
            self.tr('conceal') if self.rpcSecretVisible
            else self.tr('reveal'))
        if self.rpcSecretCopyBtn.text() != self.tr('copied'):
            self.rpcSecretCopyBtn.setText(self.tr('copy'))

    def copyToken(self) -> None:
        QApplication.clipboard().setText(self.rpcSecret)
        self.rpcSecretCopyBtn.setText(self.tr('copied'))
        QTimer.singleShot(
            1500,
            lambda: self.rpcSecretCopyBtn.setText(self.tr('copy')))
    def updateEndpoints(self) -> None:
        port = self.rpcPortLineEdit.text() or '6801'
        self.httpEndpointLabel.setText(f'http://127.0.0.1:{port}/jsonrpc')
        self.websocketEndpointLabel.setText(f'ws://127.0.0.1:{port}/jsonrpc')



    def setConnectionStatus(
            self, httpStatus: str, websocketStatus: str,
            aria2Version: str = '') -> None:
        statusKeys = {
            '已连接': 'connected', 'Connected': 'connected',
            '未连接': 'disconnected', 'Disconnected': 'disconnected',
            '连接中': 'connecting', 'Connecting': 'connecting',
            '等待检测': 'waitingCheck',
        }
        httpKey = statusKeys.get(httpStatus)
        websocketKey = statusKeys.get(websocketStatus)
        httpText = self.tr(httpKey) if httpKey else httpStatus
        websocketText = (
            self.tr(websocketKey) if websocketKey else websocketStatus)

        httpState = (
            'connected' if httpKey == 'connected'
            else 'connecting' if httpKey in ('connecting', 'waitingCheck')
            else 'disconnected')
        websocketState = (
            'connected' if websocketKey == 'connected'
            else 'connecting' if websocketKey in ('connecting', 'waitingCheck')
            else 'disconnected')

        setConnectionBadge(
            self.httpStatusLabel, httpText, httpState)
        setConnectionBadge(
            self.websocketStatusLabel, websocketText, websocketState)
        self.aria2VersionLabel.setText(aria2Version or '—')
    def saveAshoreConf(self, ashoreValues: dict) -> int:
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
            QColor(validColor(self.accentComboBox.currentText())),
            self, self.tr('chooseColor'))
        if color.isValid():
            self.accentComboBox.setCurrentText(color.name())
    def slotRpcPortChangeable(self, index: int=1) -> None:
        self.rpcPortLineEdit.setEnabled(not index)

    def slotScrollToAria2(self) -> None:
        self.scrollArea.verticalScrollBar().setValue(self.aria2SettingLabel.y())

    def slotScrollToAshore(self) -> None:
        self.scrollArea.verticalScrollBar().setValue(self.ashoreSettingLabel.y())
