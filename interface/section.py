"""Download task row-card widget."""

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu, QMessageBox,
    QProgressBar, QPushButton, QSizePolicy, QWidget,
)

from core.formatters import formatBytes, formatSpeed
from interface.actionIcons import DANGER_COLOR, actionIcon
from interface.fileIcons import fileIconPixmap


class Section(QFrame):
    actionRequested = pyqtSignal(tuple)
    openFolderRequested = pyqtSignal(str)
    copyUrlRequested = pyqtSignal(str)
    removeRequested = pyqtSignal(tuple)

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
        self.nameLabel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.metaLabel = QLabel()
        self.metaLabel.setProperty('cardMeta', True)

        self.rateLabel = QLabel()
        self.rateLabel.setProperty('cardPercent', True)
        self.rateLabel.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.rateLabel.setFixedWidth(66)

        self.actionButton = self.makeActionButton()
        self.openFolderButton = self.makeActionButton('打开目录')
        self.copyUrlButton = self.makeActionButton('复制下载链接')
        self.moreButton = self.makeActionButton('更多操作')

        self.moreMenu = QMenu(self)
        self.openFolderAction = self.moreMenu.addAction('打开目录')
        self.copyUrlAction = self.moreMenu.addAction('复制下载链接')
        self.moreMenu.addSeparator()
        self.removeAction = self.moreMenu.addAction('从列表移除')
        self.deleteAction = self.moreMenu.addAction('删除任务和文件…')
        self.moreButton.setMenu(self.moreMenu)

        self.quickActions = QWidget()
        self.quickActions.setFixedWidth(138)
        actionLayout = QHBoxLayout(self.quickActions)
        actionLayout.setContentsMargins(0, 0, 0, 0)
        actionLayout.setSpacing(4)
        actionLayout.addWidget(self.actionButton)
        actionLayout.addWidget(self.openFolderButton)
        actionLayout.addWidget(self.copyUrlButton)
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
        mainLayout.addWidget(self.quickActions, 0, 3, 2, 1)
        mainLayout.addWidget(self.metaLabel, 1, 1, 1, 2)
        mainLayout.addWidget(self.progressBar, 2, 0, 1, 4)
        mainLayout.setColumnStretch(1, 1)

        self.refresh()
        self.setQuickActionsVisible(False)

    @staticmethod
    def makeActionButton(toolTip=''):
        button = QPushButton()
        button.setProperty('cardAction', True)
        button.setIconSize(QSize(18, 18))
        if toolTip:
            button.setToolTip(toolTip)
        return button

    def connectSignals(self):
        self.actionButton.clicked.connect(self.slotAction)
        self.openFolderButton.clicked.connect(self.slotOpenFolder)
        self.copyUrlButton.clicked.connect(self.slotCopyUrl)
        self.openFolderAction.triggered.connect(self.slotOpenFolder)
        self.copyUrlAction.triggered.connect(self.slotCopyUrl)
        self.removeAction.triggered.connect(self.slotRemove)
        self.deleteAction.triggered.connect(self.slotDelete)

    def changeEvent(self, event):
        super().changeEvent(event)
        if (event.type() == QEvent.Type.PaletteChange
                and hasattr(self, 'actionButton')):
            self.refreshActionIcons()

    def enterEvent(self, event):
        self.setQuickActionsVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.moreMenu.isVisible():
            self.setQuickActionsVisible(False)
        super().leaveEvent(event)

    def contextMenuEvent(self, event):
        self.refreshActionIcons()
        self.moreMenu.exec(event.globalPos())
        event.accept()

    def setQuickActionsVisible(self, visible):
        for button in (
                self.actionButton, self.openFolderButton,
                self.copyUrlButton, self.moreButton):
            button.setVisible(visible)

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
        self.iconLabel.setPixmap(
            fileIconPixmap(
                self.fileName, self.isTorrent, status=self.status, size=52))
        progress = self.progressPercent()
        self.progressBar.setValue(progress)
        self.rateLabel.setText(
            f'{progress}%'
            if self.status == 'completed' or self.fileSize > 0 else '—')
        self.metaLabel.setText(self.metaText())
        self.refreshActionIcons()

    def refreshActionIcons(self):
        self.openFolderButton.setIcon(actionIcon('open-folder', size=18))
        self.copyUrlButton.setIcon(actionIcon('copy', size=18))
        self.moreButton.setIcon(actionIcon('more', size=18))

        self.openFolderAction.setIcon(actionIcon('open-folder', size=18))
        self.copyUrlAction.setIcon(actionIcon('copy', size=18))
        self.removeAction.setIcon(actionIcon('remove', size=18))
        self.deleteAction.setIcon(
            actionIcon('delete', color=DANGER_COLOR, size=18))

        if self.status in ('active', 'waiting'):
            self.actionButton.setIcon(actionIcon('pause', size=18))
            self.actionButton.setToolTip('暂停任务')
        elif self.status == 'paused':
            self.actionButton.setIcon(actionIcon('play', size=18))
            self.actionButton.setToolTip('开始任务')
        elif self.status == 'completed':
            self.actionButton.setIcon(actionIcon('open-file', size=18))
            self.actionButton.setToolTip('打开文件')
        elif self.status == 'error':
            self.actionButton.setIcon(actionIcon('retry', size=18))
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

    def confirmDelete(self):
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle('删除任务和文件')
        message.setText('删除任务和已下载文件？')
        message.setInformativeText(
            f'{self.fileName}\n\n'
            '此操作会删除 aria2 为该任务列出的下载文件。')
        cancelButton = message.addButton(
            '取消', QMessageBox.ButtonRole.RejectRole)
        deleteButton = message.addButton(
            '删除文件', QMessageBox.ButtonRole.DestructiveRole)
        message.setDefaultButton(cancelButton)
        message.exec()
        return message.clickedButton() is deleteButton

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
        if self.confirmDelete():
            self.removeRequested.emit((self.gid, True))
