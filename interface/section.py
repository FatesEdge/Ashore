"""Download task card widget."""

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from core.formatters import formatBytes, formatSpeed
from interface.fileIcons import iconForFile
from paths import RESOURCE_DIR


class Section(QFrame):
    actionRequested = pyqtSignal(tuple)
    openFolderRequested = pyqtSignal(str)
    copyUrlRequested = pyqtSignal(str)
    removeRequested = pyqtSignal(tuple)
    resourcePath = str(RESOURCE_DIR) + '/'

    def __init__(self, gid:str, fileName:str, status:str, fileSize:int, completedSize:int, speed:int, isTorrent:bool=False):
        super().__init__()
        self.gid = gid              #得到索引号
        self.fileName = fileName    #得到文件名
        self.status = status
        self.fileSize = fileSize
        self.completedSize = completedSize
        self.speed = speed
        self.isTorrent = isTorrent
        self.initUI()
        self.connectSignals()           #设置部件事件链接

    def initUI(self):
        self.setObjectName('Section')
        self.iconLabel = QLabel('icon')
        self.iconLabel.setFixedSize(50,50)
        self.iconLabel.setScaledContents(True)
        self.setIcon(self.status)
        self.nameLabel = QLabel(self.fileName)
        self.nameLabel.setFixedHeight(25)
        self.nameLabel.setMinimumWidth(100)
        self.sizeLabel = QLabel(self.fileSizeText())
        self.sizeLabel.setFixedSize(100,25)
        if self.fileSize == 0:
            self.rateLabel = QLabel('-')
        else:
            self.rateLabel = QLabel(f'{self.completedSize / self.fileSize * 100:.1f}%')
        self.rateLabel.setFixedSize(100,25)
        self.completedLabel = QLabel('已下载:')
        self.completedLabel.setFixedSize(50,25)
        self.speedLabel = QLabel(self.speedText())
        self.speedLabel.setFixedSize(100,25)
        temp = QWidget()
        temp.setFixedSize(23,23)
        self.actionButton = QPushButton()
        self.actionButton.setFixedSize(23,23)
        self.actionButton.setFlat(True)
        if self.status == 'active' or self.status == 'waiting':
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/pause.png'))
            self.actionButton.setIconSize(QSize(16,16))
            self.actionButton.setToolTip('暂停任务')
            self.actionButton.setStatusTip('暂停任务')
        elif self.status == 'paused':
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/play.png'))
            self.actionButton.setIconSize(QSize(20,20))
            self.actionButton.setToolTip('开始任务')
            self.actionButton.setStatusTip('开始任务')
        elif self.status == 'completed':
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/openfile.png'))
            self.actionButton.setIconSize(QSize(18,18))
            self.actionButton.setToolTip('打开文件')
            self.actionButton.setStatusTip('打开文件')
        elif self.status == 'error':
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/retry.png'))
            self.actionButton.setIconSize(QSize(18,18))
            self.actionButton.setToolTip('重试')
            self.actionButton.setStatusTip('重试')
        self.openDirBtn = QPushButton()
        self.openDirBtn.setFixedSize(23,23)
        self.openDirBtn.setFlat(True)
        self.openDirBtn.setIconSize(QSize(16,16))
        self.openDirBtn.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/openfolder.png'))
        self.openDirBtn.setToolTip('打开目录')
        self.openDirBtn.setStatusTip('打开文件所在目录')
        self.copyUrlButton = QPushButton()
        self.copyUrlButton.setFixedSize(23,23)
        self.copyUrlButton.setFlat(True)
        self.copyUrlButton.setIconSize(QSize(16,16))
        self.copyUrlButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/copy.png'))
        self.copyUrlButton.setToolTip('复制下载链接')
        self.copyUrlButton.setStatusTip('复制下载链接到剪贴板')
        self.removeBtn = QPushButton()
        self.removeBtn.setFixedSize(23,23)
        self.removeBtn.setFlat(True)
        self.removeBtn.setIconSize(QSize(20,20))
        self.removeBtn.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/remove.png'))
        self.removeBtn.setToolTip('从列表中移除任务')
        self.removeBtn.setStatusTip('从列表中移除任务，不删除下载文件')
        self.delBtn = QPushButton()
        self.delBtn.setFixedSize(23,23)
        self.delBtn.setFlat(True)
        self.delBtn.setIconSize(QSize(16,16))
        self.delBtn.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/del.png'))
        self.delBtn.setToolTip('彻底删除任务')
        self.delBtn.setStatusTip('从列表中移除任务，同时删除下载文件')
        for button in (
                self.actionButton, self.openDirBtn, self.copyUrlButton,
                self.removeBtn, self.delBtn):
            button.setProperty('cardAction', True)

        btnLayout = QHBoxLayout()
        btnLayout.addWidget(temp)
        btnLayout.addWidget(self.actionButton)
        btnLayout.addWidget(self.openDirBtn)
        btnLayout.addWidget(self.copyUrlButton)
        btnLayout.addWidget(self.removeBtn)
        btnLayout.addWidget(self.delBtn)
        btnLayout.addStretch()
        btnLayout.setContentsMargins(0,5,0,0)
        self.actionButton.hide()
        self.openDirBtn.hide()
        self.copyUrlButton.hide()
        self.removeBtn.hide()
        self.delBtn.hide()
        infoLayout = QHBoxLayout()
        # infoLayout.addWidget(self.iconLabel)
        # infoLayout.addWidget(self.nameLabel)

        infoLayout.addWidget(self.sizeLabel)
        infoLayout.addSpacerItem(QSpacerItem(10,10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        infoLayout.addWidget(self.completedLabel)
        infoLayout.addWidget(self.rateLabel)
        infoLayout.addWidget(self.speedLabel)
        self.progressBar = QProgressBar()
        self.progressBar.setFixedHeight(20)
        self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progressBar.setFormat('%p%')
        self.progressBar.setTextVisible(True)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(
            int(self.completedSize / self.fileSize * 100) if self.fileSize else 0)
        self.progressBar.setContentsMargins(0,0,0,0)
        mainLayout = QGridLayout(self)
        mainLayout.addItem(QSpacerItem(10,0,QSizePolicy.Policy.Fixed),0,0,3,1)
        mainLayout.addWidget(self.iconLabel, 0, 1, 3, 1)
        mainLayout.addWidget(self.nameLabel, 0, 2, 1, 5)
        mainLayout.addLayout(btnLayout, 1, 2, 1, 5)
        mainLayout.addLayout(infoLayout, 2, 2, 1, 5)
        mainLayout.addWidget(self.progressBar, 3, 0, 1, 7)
        mainLayout.setContentsMargins(0,6,0,6)
        self.setLayout(mainLayout)
        self.setFixedHeight(110)
        self.setContentsMargins(5,5,5,0)
        self.setProperty('downloadCard', True)

    def updateInfo(
            self, status: str, fileSize: int, completedSize: int, speed: int,
            fileName: str | None = None, isTorrent: bool | None = None):
        if fileName is not None and fileName != self.fileName:
            self.fileName = fileName
            self.nameLabel.setText(fileName)
        if isTorrent is not None:
            self.isTorrent = isTorrent
        self.fileSize = fileSize
        self.status = status
        self.speed = speed
        self.sizeLabel.setText(self.fileSizeText())
        if fileSize != 0:
            self.rateLabel.setText(f'{completedSize / fileSize * 100:.1f}%')
            self.progressBar.setValue(int(completedSize / fileSize * 100))
        if status == 'active':
            self.speedLabel.setText(self.speedText())
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/pause.png'))
            self.actionButton.setToolTip('暂停任务')
        elif status == 'paused':
            self.speedLabel.setText('已暂停')
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/play.png'))
            self.actionButton.setToolTip('开始任务')
        elif status == 'waiting':
            self.speedLabel.setText('等待中')
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/pause.png'))
            self.actionButton.setToolTip('暂停任务')
        elif status == 'error':
            self.speedLabel.setText('错误')
            self.actionButton.setIcon(QIcon(self.resourcePath + 'static/icon/functionIcons/retry.png'))
            self.actionButton.setToolTip('重试')
        elif status == 'completed':
            self.speedLabel.setText('已完成')
        self.setIcon(status)
    
    def setIcon(self, status:str):
        folder = 'icon.ing' if status in ('active', 'completed') else 'icon.stop'
        icon = iconForFile(self.fileName, self.isTorrent)
        self.iconLabel.setPixmap(QPixmap(self.resourcePath + 'static/icon/' + folder + '/' + icon + '.png'))

    def mouseDoubleClickEvent(self,event):
        self.actionRequested.emit((self.gid, self.status))
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event):        #鼠标进入控件;
        self.actionButton.show()
        self.openDirBtn.show()
        self.copyUrlButton.show()
        self.removeBtn.show()
        self.delBtn.show()
        super().enterEvent(event)
    def leaveEvent(self, event):        #鼠标离开控件;
        self.actionButton.hide()
        self.openDirBtn.hide()
        self.copyUrlButton.hide()
        self.removeBtn.hide()
        self.delBtn.hide()
        super().leaveEvent(event)
    def connectSignals(self):
        self.actionButton.clicked.connect(self.slotAction)
        self.openDirBtn.clicked.connect(self.slotOpenFolder)
        self.copyUrlButton.clicked.connect(self.slotCopyUrl)
        self.removeBtn.clicked.connect(self.slotRemove)
        self.delBtn.clicked.connect(self.slotDelete)

    def slotAction(self):   #与双击效果相同
        self.actionRequested.emit((self.gid, self.status))

    def slotOpenFolder(self):       #打开文件夹
        self.openFolderRequested.emit(self.gid)

    def slotCopyUrl(self):        #复制url
        self.copyUrlRequested.emit(self.gid)

    def slotRemove(self):
        self.removeRequested.emit((self.gid, False))
    
    def slotDelete(self):
        self.removeRequested.emit((self.gid, True))

    def fileSizeText(self) -> str:
        return formatBytes(self.fileSize)

    def speedText(self) -> str:
        return formatSpeed(self.speed)
