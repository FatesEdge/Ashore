"""Single-row Ashore top bar with native window-manager operations."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class TitleBar(QWidget):
    """Combine application commands and window controls in one compact row."""

    def __init__(self, window, commandWidgets, overflowButton, parent=None):
        super().__init__(parent)
        self.hostWindow = window
        self.setProperty('titleBar', True)
        self.setFixedHeight(38)

        self.appIconLabel = QLabel()
        self.appIconLabel.setFixedSize(20, 20)
        self.appIconLabel.setPixmap(self.hostWindow.windowIcon().pixmap(18, 18))
        self.appIconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.appIconLabel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.titleLabel = QLabel('Ashore')
        self.titleLabel.setProperty('windowTitle', True)
        self.titleLabel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.minimizeButton = self._windowButton('minimize', '−')
        self.maximizeButton = self._windowButton('maximize', '□')
        self.closeButton = self._windowButton('close', '×')

        self.minimizeButton.clicked.connect(self.hostWindow.showMinimized)
        self.maximizeButton.clicked.connect(self.toggleMaximized)
        self.closeButton.clicked.connect(self.hostWindow.close)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 6, 4)
        layout.setSpacing(4)

        controls = (self.minimizeButton, self.maximizeButton, self.closeButton)
        if sys.platform == 'darwin':
            for button in controls:
                layout.addWidget(button)
            layout.addSpacing(6)
            layout.addWidget(self.titleLabel)
        else:
            layout.addWidget(self.titleLabel)

        layout.addSpacing(8)
        for widget in commandWidgets:
            layout.addWidget(widget)
        layout.addStretch(1)
        layout.addWidget(overflowButton)

        if sys.platform != 'darwin':
            layout.addSpacing(4)
            for button in controls:
                layout.addWidget(button)

    def _windowButton(self, role, text):
        button = QPushButton(text)
        button.setProperty('windowControl', True)
        button.setProperty('windowControlRole', role)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setFixedSize(26, 26)
        return button

    def toggleMaximized(self):
        if self.hostWindow.isMaximized():
            self.hostWindow.showNormal()
        else:
            self.hostWindow.showMaximized()
        self.syncWindowState()

    def syncWindowState(self):
        self.maximizeButton.setText('❐' if self.hostWindow.isMaximized() else '□')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.hostWindow.windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggleMaximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
