"""Lifecycle windows shown while Ashore starts or exits."""

from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPlainTextEdit,
    QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from interface.actionIcons import actionIcon
from interface.languageManager import translate


class LifecycleWindow(QWidget):
    firstPainted = pyqtSignal()
    ready = pyqtSignal()

    def __init__(self, imagePath, statusText, imageExtent=None):
        super().__init__(None, Qt.WindowType.SplashScreen)
        self.hasPainted = False
        self.hasActivated = False
        self.readyScheduled = False
        self.readyEmitted = False
        image = QLabel()
        pixmap = QPixmap(str(imagePath))
        if imageExtent and not pixmap.isNull():
            pixmap = pixmap.scaled(
                imageExtent, imageExtent,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
        image.setPixmap(pixmap)
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.statusLabel = QLabel(statusText)
        self.statusLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(4)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(6)
        layout.addWidget(image)
        layout.addWidget(self.statusLabel)
        layout.addWidget(self.progressBar)

    def event(self, event):
        result = super().event(event)
        if event.type() == QEvent.Type.WindowActivate:
            self.hasActivated = True
            self.checkReady()
        return result

    def showStatus(self, text):
        self.statusLabel.setText(text)

    def showActive(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.hasPainted:
            self.hasPainted = True
            QTimer.singleShot(0, self.firstPainted.emit)
            self.checkReady()

    def checkReady(self):
        if (self.hasActivated and self.hasPainted
                and not self.readyScheduled and not self.readyEmitted):
            self.readyScheduled = True
            QTimer.singleShot(0, self.emitReady)

    def emitReady(self):
        self.readyScheduled = False
        if self.readyEmitted or not self.hasActivated or not self.hasPainted:
            return
        self.readyEmitted = True
        self.ready.emit()

    def complete(self):
        self.progressBar.setRange(0, 1)
        self.progressBar.setValue(1)


class StartupWindow(LifecycleWindow):
    def __init__(self, imagePath, language='en'):
        super().__init__(imagePath, translate(language, 'startupLoadingConfig'))

    def finish(self, window):
        self.complete()
        window.show()
        QTimer.singleShot(0, self.close)


class ExitWindow(LifecycleWindow):
    def __init__(self, imagePath, statusText):
        super().__init__(imagePath, statusText, imageExtent=96)
        self.setMinimumWidth(320)


class RecoveryWindow(QWidget):
    recheckRequested = pyqtSignal()
    quitRequested = pyqtSignal()

    def __init__(self, issue, language='en'):
        super().__init__()
        self.issue = issue
        self.language = language
        self.setProperty('recoveryPage', True)
        self.setWindowTitle('Ashore')
        self.setMinimumSize(640, 460)
        self.resize(700, 500)

        title = QLabel('Ashore')
        title.setProperty('recoveryTitle', True)

        intro = QLabel(self.tr('recoveryIntro'))
        intro.setProperty('recoveryIntro', True)
        intro.setWordWrap(True)

        self.reasonLabel = QLabel()
        self.reasonLabel.setProperty('recoveryReason', True)
        self.reasonLabel.setWordWrap(True)

        self.systemLabel = QLabel()
        self.systemLabel.setProperty('recoveryMeta', True)

        commandTitle = QLabel(self.tr('recoveryInstallCommand'))
        commandTitle.setProperty('recoveryMeta', True)

        self.commandBox = QPlainTextEdit()
        self.commandBox.setProperty('terminalBlock', True)
        self.commandBox.setReadOnly(True)
        self.commandBox.setMaximumHeight(82)
        terminalFont = QFont('monospace')
        terminalFont.setStyleHint(QFont.StyleHint.Monospace)
        self.commandBox.setFont(terminalFont)

        self.copyButton = QPushButton(self.tr('copyCommand'))
        self.copyButton.setIcon(actionIcon('copy', size=17))
        self.recheckButton = QPushButton(self.tr('recheckEnvironment'))
        self.recheckButton.setProperty('primaryAction', True)
        self.recheckButton.setIcon(actionIcon('retry', size=17))
        self.quitButton = QPushButton(self.tr('quitAshore'))
        self.quitButton.setIcon(actionIcon('quit', size=17))

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.copyButton)
        buttonLayout.addStretch(1)
        buttonLayout.addWidget(self.quitButton)
        buttonLayout.addWidget(self.recheckButton)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 28)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(intro)
        layout.addSpacing(6)
        layout.addWidget(self.reasonLabel)
        layout.addWidget(self.systemLabel)
        layout.addSpacing(8)
        layout.addWidget(commandTitle)
        layout.addWidget(self.commandBox)
        layout.addStretch(1)
        layout.addLayout(buttonLayout)

        self.copyButton.clicked.connect(lambda _checked=False: self.copyCommand())
        self.recheckButton.clicked.connect(
            lambda _checked=False: self.recheckRequested.emit())
        self.quitButton.clicked.connect(
            lambda _checked=False: self.quitRequested.emit())
        self.setIssue(issue)

    def tr(self, key):
        return translate(self.language, key)

    def setIssue(self, issue):
        self.issue = issue
        self.copyButton.setText(self.tr('copyCommand'))
        reasonKey = {
            'aria2_missing': 'recoveryIssueMissing',
            'aria2_rpc_unavailable': 'recoveryIssueRpc',
            'aria2_startup_error': 'recoveryIssueStartup',
        }.get(issue.code, 'recoveryIssueStartup')
        self.reasonLabel.setText(
            self.tr('recoveryReason').format(
                reason=self.tr(reasonKey)))
        if issue.detail:
            self.reasonLabel.setText(
                self.reasonLabel.text() + '\n' + issue.detail)
        self.systemLabel.setText(
            self.tr('recoverySystem').format(system=issue.systemName))
        self.commandBox.setPlainText(f'$ {issue.installCommand}')

    def copyCommand(self):
        QApplication.clipboard().setText(self.issue.installCommand)
        self.copyButton.setText(self.tr('copied'))
