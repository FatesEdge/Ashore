"""Download task row-card widget."""

from PyQt6.QtCore import QEvent, QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu, QMessageBox,
    QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from core.formatters import formatBytes, formatSpeed
from interface.actionIcons import DANGER_COLOR, actionIcon
from interface.fileIcons import fileIconPixmap
from interface.languageManager import translate


class HoverMenuButton(QPushButton):
    menuRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hoverTimer = QTimer(self)
        self.hoverTimer.setSingleShot(True)
        self.hoverTimer.setInterval(280)
        self.hoverTimer.timeout.connect(self.menuRequested)
        self.clicked.connect(lambda _checked=False: self.menuRequested.emit())

    def enterEvent(self, event):
        self.hoverTimer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hoverTimer.stop()
        super().leaveEvent(event)


class Section(QFrame):
    actionRequested = pyqtSignal(str, str)
    openFolderRequested = pyqtSignal(str)
    copyUrlRequested = pyqtSignal(str)
    removeRequested = pyqtSignal(tuple)

    CONTENT_MIN_WIDTH = 660
    CONTENT_MAX_WIDTH = 820

    def __init__(
            self, gid: str, fileName: str, status: str, fileSize: int,
            completedSize: int, speed: int, isTorrent: bool = False,
            files=None, language='zh_CN'):
        super().__init__()
        self.gid = gid
        self.fileName = fileName
        self.status = status
        self.fileSize = fileSize
        self.completedSize = completedSize
        self.speed = speed
        self.isTorrent = isTorrent
        self.files = list(files or [])
        self.language = language
        self.initUI()
        self.connectSignals()

    def tr(self, key):
        return translate(self.language, key)

    def initUI(self):
        self.setObjectName('Section')
        self.setProperty('downloadCard', True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFixedHeight(84)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.iconLabel = QLabel()
        self.iconLabel.setFixedSize(50, 60)
        self.iconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.nameLabel = QLabel(self.fileName)
        self.nameLabel.setProperty('cardTitle', True)
        self.nameLabel.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.nameLabel.setToolTip(self.fileName)

        self.rateLabel = QLabel()
        self.rateLabel.setProperty('cardPercent', True)
        self.rateLabel.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.rateLabel.setFixedWidth(64)

        self.actionButton = self.makeActionButton()
        self.openFolderButton = self.makeActionButton()
        self.copyUrlButton = self.makeActionButton()
        self.moreButton = HoverMenuButton()
        self.moreButton.setProperty('cardAction', True)
        self.moreButton.setIconSize(QSize(16, 16))

        self.actionSlot = QWidget()
        self.actionSlot.setFixedHeight(26)
        actionLayout = QHBoxLayout(self.actionSlot)
        actionLayout.setContentsMargins(30, 0, 0, 0)
        actionLayout.setSpacing(4)
        actionLayout.addWidget(self.actionButton)
        actionLayout.addWidget(self.openFolderButton)
        actionLayout.addWidget(self.copyUrlButton)
        actionLayout.addWidget(self.moreButton)
        actionLayout.addStretch(1)

        self.metaLabel = QLabel()
        self.metaLabel.setProperty('cardMeta', True)

        self.primaryAction = QAction(self)
        self.openFolderAction = QAction(self)
        self.copyUrlAction = QAction(self)
        self.removeAction = QAction(self)
        self.deleteAction = QAction(self)

        self.overflowMenu = QMenu(self)
        self.overflowMenu.addAction(self.removeAction)
        self.overflowMenu.addSeparator()
        self.overflowMenu.addAction(self.deleteAction)
        self.overflowMenu.aboutToHide.connect(self.menuClosed)

        self.contextMenu = QMenu(self)
        self.contextMenu.aboutToHide.connect(self.menuClosed)

        infoPanel = QWidget()
        infoPanel.setMinimumWidth(self.CONTENT_MIN_WIDTH)
        infoPanel.setMaximumWidth(self.CONTENT_MAX_WIDTH)
        infoPanel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        infoLayout = QGridLayout(infoPanel)
        infoLayout.setContentsMargins(0, 0, 0, 0)
        infoLayout.setHorizontalSpacing(8)
        infoLayout.setVerticalSpacing(0)
        infoLayout.addWidget(self.nameLabel, 0, 0, 1, 2)
        infoLayout.addWidget(self.actionSlot, 1, 0)
        infoLayout.addWidget(self.rateLabel, 1, 1)
        infoLayout.addWidget(self.metaLabel, 2, 0, 1, 2)
        infoLayout.setColumnStretch(0, 1)

        bodyLayout = QHBoxLayout()
        bodyLayout.setContentsMargins(0, 0, 0, 0)
        bodyLayout.setSpacing(14)
        bodyLayout.addWidget(
            self.iconLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        bodyLayout.addWidget(infoPanel, 1, Qt.AlignmentFlag.AlignTop)
        bodyLayout.addStretch(1)

        self.progressBar = QProgressBar()
        self.progressBar.setProperty('cardProgress', True)
        self.progressBar.setTextVisible(False)
        self.progressBar.setRange(0, 100)
        self.progressBar.setFixedHeight(4)

        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(14, 6, 10, 5)
        mainLayout.setSpacing(1)
        mainLayout.addLayout(bodyLayout)
        mainLayout.addWidget(self.progressBar)

        self.refresh()
        self.setQuickActionsVisible(False)

    @staticmethod
    def makeActionButton():
        button = QPushButton()
        button.setProperty('cardAction', True)
        button.setIconSize(QSize(16, 16))
        return button

    def connectSignals(self):
        self.actionButton.clicked.connect(self.slotPrimaryAction)
        self.openFolderButton.clicked.connect(self.slotOpenFolder)
        self.copyUrlButton.clicked.connect(self.slotCopyUrl)
        self.moreButton.menuRequested.connect(self.showOverflowMenu)

        self.primaryAction.triggered.connect(self.slotPrimaryAction)
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
        if not self.overflowMenu.isVisible() and not self.contextMenu.isVisible():
            self.setQuickActionsVisible(False)
        super().leaveEvent(event)

    def contextMenuEvent(self, event):
        self.prepareContextMenu()
        self.contextMenu.exec(event.globalPos())
        event.accept()

    def menuClosed(self):
        if not self.underMouse():
            self.setQuickActionsVisible(False)

    def showOverflowMenu(self):
        if self.overflowMenu.isVisible():
            return
        self.setQuickActionsVisible(True)
        self.refreshActionIcons()
        position = self.moreButton.mapToGlobal(
            QPoint(0, self.moreButton.height()))
        self.overflowMenu.popup(position)

    def prepareContextMenu(self):
        self.contextMenu.clear()
        self.contextMenu.addAction(self.primaryAction)
        if self.primaryActionKind() != 'open-folder':
            self.contextMenu.addAction(self.openFolderAction)
        self.contextMenu.addAction(self.copyUrlAction)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction(self.removeAction)
        self.contextMenu.addAction(self.deleteAction)
        self.refreshActionIcons()

    def setQuickActionsVisible(self, visible):
        for button in (
                self.actionButton, self.openFolderButton,
                self.copyUrlButton, self.moreButton):
            button.setVisible(visible)

    def setLanguage(self, language):
        self.language = language
        self.refresh()

    def updateInfo(
            self, status: str, fileSize: int, completedSize: int, speed: int,
            fileName: str | None = None, isTorrent: bool | None = None,
            files=None):
        if fileName is not None:
            self.fileName = fileName
        if isTorrent is not None:
            self.isTorrent = isTorrent
        if files is not None:
            self.files = list(files)
        self.fileSize = fileSize
        self.completedSize = completedSize
        self.status = status
        self.speed = speed
        self.refresh()

    def refresh(self):
        self.nameLabel.setText(self.fileName)
        self.nameLabel.setToolTip(self.fileName)
        self.iconLabel.setPixmap(
            fileIconPixmap(
                self.fileName, self.isTorrent, status=self.status))
        progress = self.progressPercent()
        self.progressBar.setValue(progress)
        self.rateLabel.setText(
            f'{progress}%'
            if self.status == 'completed' or self.fileSize > 0 else '—')
        self.metaLabel.setText(self.metaText())
        self.refreshActionText()
        self.refreshActionIcons()

    def primaryActionKind(self):
        if self.status in ('active', 'waiting'):
            return 'pause'
        if self.status == 'paused':
            return 'unpause'
        if self.status == 'error':
            return 'retry'
        if self.status == 'completed':
            fileCount = len([path for path in self.files if path])
            return 'open-folder' if fileCount > 1 else 'open-file'
        return 'none'

    def refreshActionText(self):
        kind = self.primaryActionKind()
        text = {
            'pause': self.tr('pauseTask'),
            'unpause': self.tr('startTask'),
            'open-file': self.tr('openFile'),
            'open-folder': self.tr('openFolder'),
            'retry': self.tr('retryTask'),
        }.get(kind, '')
        self.actionButton.setToolTip(text)
        self.primaryAction.setText(text)
        self.openFolderButton.setToolTip(self.tr('openFolder'))
        self.copyUrlButton.setToolTip(self.tr('copyLink'))
        self.moreButton.setToolTip(self.tr('moreActions'))
        self.openFolderAction.setText(self.tr('openFolder'))
        self.copyUrlAction.setText(self.tr('copyLink'))
        self.removeAction.setText(self.tr('removeFromList'))
        self.deleteAction.setText(self.tr('deleteTaskFiles'))

    def refreshActionIcons(self):
        kind = self.primaryActionKind()
        iconName = {
            'pause': 'pause',
            'unpause': 'play',
            'open-file': 'open-file',
            'open-folder': 'open-folder',
            'retry': 'retry',
        }.get(kind, 'more')
        icon = actionIcon(iconName, size=16)
        self.actionButton.setIcon(icon)
        self.primaryAction.setIcon(icon)
        self.openFolderButton.setIcon(actionIcon('open-folder', size=16))
        self.copyUrlButton.setIcon(actionIcon('copy', size=16))
        self.moreButton.setIcon(actionIcon('more', size=16))
        self.openFolderAction.setIcon(actionIcon('open-folder', size=16))
        self.copyUrlAction.setIcon(actionIcon('copy', size=16))
        self.removeAction.setIcon(actionIcon('remove', size=16))
        self.deleteAction.setIcon(
            actionIcon('delete', color=DANGER_COLOR, size=16))

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
            'waiting': self.tr('waitingStatus'),
            'paused': self.tr('pausedStatus'),
            'completed': self.tr('completedStatus'),
            'error': self.tr('errorStatus'),
        }.get(self.status, self.status)
        return f'{amount}   ·   {state}'

    def confirmDelete(self):
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle(self.tr('deleteTaskTitle'))
        message.setText(self.tr('deleteTaskQuestion'))
        message.setInformativeText(
            f'{self.fileName}\n\n{self.tr("deleteTaskInfo")}')
        cancelButton = message.addButton(
            self.tr('cancel'), QMessageBox.ButtonRole.RejectRole)
        deleteButton = message.addButton(
            self.tr('deleteFiles'), QMessageBox.ButtonRole.DestructiveRole)
        message.setDefaultButton(cancelButton)
        message.exec()
        return message.clickedButton() is deleteButton

    def mouseDoubleClickEvent(self, event):
        self.slotPrimaryAction()
        super().mouseDoubleClickEvent(event)

    def slotPrimaryAction(self):
        kind = self.primaryActionKind()
        if kind != 'none':
            self.actionRequested.emit(self.gid, kind)

    def slotOpenFolder(self):
        self.openFolderRequested.emit(self.gid)

    def slotCopyUrl(self):
        self.copyUrlRequested.emit(self.gid)

    def slotRemove(self):
        self.removeRequested.emit((self.gid, False))

    def slotDelete(self):
        if self.confirmDelete():
            self.removeRequested.emit((self.gid, True))
