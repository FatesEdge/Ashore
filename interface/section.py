"""Download task row-card widget."""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu, QProgressBar,
    QPushButton, QSizePolicy, QWidget,
)

from core.formatters import formatBytes, formatSpeed
from interface.fileIcons import fileIconPixmap
from paths import RESOURCE_DIR


class Section(QFrame):
    actionRequested = pyqtSignal(tuple)
    openFolderRequested = pyqtSignal(str)
    copyUrlRequested = pyqtSignal(str)
    removeRequested = pyqtSignal(tuple)
    resourcePath = str(RESOURCE_DIR) + '/'

    def __init__(self, gid: str, fileName: str, status: str, fileSize: int,
                 completedSize: int, speed: int, isTorrent: bool = False):
        super().__init__()
        self.gid = gid
        self.fileName = fileName
        self.status = status
        self.fileSize = fileSize
        self.completedSize = completedSize
        self.speed = speed
        self.isTorrent = isTorrent
        self.initUI()
        self.connectSignals()

    def initUI(self):
        self.setObjectName('Section')
        self.setProperty('downloadCard', True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFixedHeight(98)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.iconLabel = QLabel()
        self.iconLabel.setFixedSize(56, 56)
        self.iconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.nameLabel = QLabel(self.fileName)
        self.nameLabel.setProperty('cardTitle', True)
        self.nameLabel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.metaLabel = QLabel()
        self.metaLabel.setProperty('cardMeta', True)

        self.rateLabel = QLabel()
        self.rateLabel.setProperty('cardPercent', True)
        self.rateLabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.rateLabel.setFixedWidth(66)

        self.actionButton = QPushButton()
        self.actionButton.setProperty('cardAction', True)
        self.actionButton.setIconSize(QSize(17, 17))

        self.moreButton = QPushButton('⋯')
        self.moreButton.setProperty('cardAction', True)
        self.moreButton.setToolTip('更多操作')

        self.moreMenu = QMenu(self)
        self.openFolderAction = self.moreMenu.addAction('打开目录')
        self.copyUrlAction = self.moreMenu.addAction('复制下载链接')
        self.moreMenu.addSeparator()
        self.removeAction = self.moreMenu.addAction('从列表移除')
        self.deleteAction = self.moreMenu.addAction('删除任务和文件')
        self.moreButton.setMenu(self.moreMenu)

        actions = QWidget()
        actions.setFixedWidth(70)
        actionLayout = QHBoxLayout(actions)
        actionLayout.setContentsMargins(2, 0, 0, 0)
        actionLayout.setSpacing(4)
        actionLayout.addWidget(self.actionButton)
        actionLayout.addWidget(self.moreButton)

        self.progressBar = QProgressBar()
        self.progressBar.setProperty('cardProgress', True)
        self.progressBar.setTextVisible(False)
        self.progressBar.setRange(0, 100)
        self.progressBar.setFixedHeight(4)

        mainLayout = QGridLayout(self)
        mainLayout.setContentsMargins(12, 10, 12, 9)
        mainLayout.setHorizontalSpacing(11)
        mainLayout.setVerticalSpacing(4)
        mainLayout.addWidget(self.iconLabel, 0, 0, 2, 1)
        mainLayout.addWidget(self.nameLabel, 0, 1)
        mainLayout.addWidget(self.rateLabel, 0, 2)
        mainLayout.addWidget(actions, 0, 3, 2, 1)
        mainLayout.addWidget(self.metaLabel, 1, 1, 1, 2)
        mainLayout.addWidget(self.progressBar, 2, 0, 1, 4)
        mainLayout.setColumnStretch(1, 1)
        self.refresh()

    def connectSignals(self):
        self.actionButton.clicked.connect(self.slotAction)
        self.openFolderAction.triggered.connect(self.slotOpenFolder)
        self.copyUrlAction.triggered.connect(self.slotCopyUrl)
        self.removeAction.triggered.connect(self.slotRemove)
        self.deleteAction.triggered.connect(self.slotDelete)

    def updateInfo(self, status: str, fileSize: int, completedSize: int, speed: int,
                   fileName: str | None = None, isTorrent: bool | None = None):
        if fileName is not None:
            self.fileName = fileName
        if isTorrent is not None:
            self.isTorrent = isTorrent
        self.fileSize = fileSize
        self.completedSize = completedSize
        self.status = status
        self.speed = speed
        self.refresh()

    def refresh(self):
        self.nameLabel.setText(self.fileName)
        self.iconLabel.setPixmap(fileIconPixmap(self.fileName, self.isTorrent, 52))
        progress = self.progressPercent()
        self.progressBar.setValue(progress)
        self.rateLabel.setText(f'{progress}%' if self.status == 'completed' or self.fileSize > 0 else '—')
        self.metaLabel.setText(self.metaText())
        if self.status in ('active', 'waiting'):
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/pause.png'))
            self.actionButton.setToolTip('暂停任务')
        elif self.status == 'paused':
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/play.png'))
            self.actionButton.setToolTip('开始任务')
        elif self.status == 'completed':
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/openfile.png'))
            self.actionButton.setToolTip('打开文件')
        elif self.status == 'error':
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/retry.png'))
            self.actionButton.setToolTip('重试')

    def progressPercent(self):
        if self.status == 'completed':
            return 100
        if self.fileSize <= 0:
            return 0
        return max(0, min(100, int(self.completedSize * 100 / self.fileSize)))

    def metaText(self):
        amount = (
            f'{formatBytes(self.completedSize)} / {formatBytes(self.fileSize)}'
            if self.fileSize > 0 else formatBytes(self.completedSize))
        state = {
            'active': f'↓ {formatSpeed(self.speed)}',
            'waiting': '等待中',
            'paused': '已暂停',
            'completed': '已完成',
            'error': '错误',
        }.get(self.status, self.status)
        return f'{amount}   ·   {state}'

    def mouseDoubleClickEvent(self, event):
        self.actionRequested.emit((self.gid, self.status))
        super().mouseDoubleClickEvent(event)

    def slotAction(self):
        self.actionRequested.emit((self.gid, self.status))

    def slotOpenFolder(self):
        self.openFolderRequested.emit(self.gid)

    def slotCopyUrl(self):
        self.copyUrlRequested.emit(self.gid)

    def slotRemove(self):
        self.removeRequested.emit((self.gid, False))

    def slotDelete(self):
        self.removeRequested.emit((self.gid, True))
