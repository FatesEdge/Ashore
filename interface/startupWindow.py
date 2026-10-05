"""Lifecycle windows shown while Ashore starts or exits."""

from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


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
    def __init__(self, imagePath):
        super().__init__(imagePath, '正在读取配置')

    def finish(self, window):
        self.complete()
        window.show()
        QTimer.singleShot(0, self.close)


class ExitWindow(LifecycleWindow):
    def __init__(self, imagePath, statusText):
        super().__init__(imagePath, statusText, imageExtent=96)
        self.setMinimumWidth(320)
