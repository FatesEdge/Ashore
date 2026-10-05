"""Responsive startup window for Ashore initialization."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class StartupWindow(QWidget):
    firstPainted = pyqtSignal()

    def __init__(self, imagePath):
        super().__init__(None, Qt.WindowType.SplashScreen)
        self.hasPainted = False
        image = QLabel()
        image.setPixmap(QPixmap(str(imagePath)))
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.statusLabel = QLabel('正在读取配置')
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

    def showStatus(self, text):
        self.statusLabel.setText(text)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.hasPainted:
            self.hasPainted = True
            QTimer.singleShot(0, self.firstPainted.emit)

    def finish(self, window):
        self.progressBar.setRange(0, 1)
        self.progressBar.setValue(1)
        window.show()
        QTimer.singleShot(0, self.close)
