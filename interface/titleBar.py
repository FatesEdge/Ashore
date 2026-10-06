"""Single-row Ashore top bar with native window-manager operations."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class TitleBar(QWidget):
    """Combine application commands and window controls in one compact row."""

    def __init__(self, window, commandWidgets, overflowButton, parent=None):
        super().__init__(parent)
        self.hostWindow = window
        self.commandWidgets = tuple(commandWidgets)
        self.overflowButton = overflowButton
        self.setProperty('titleBar', True)
        self.setFixedHeight(36)

        self.appIconLabel = QLabel()
        self.appIconLabel.setProperty('windowIcon', True)
        self.appIconLabel.setFixedSize(20, 20)
        self.appIconLabel.setPixmap(self.hostWindow.windowIcon().pixmap(18, 18))
        self.appIconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.appIconLabel.setContentsMargins(0, 2, 0, 0)
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
        layout.setContentsMargins(12, 4, 12, 2)
        layout.setSpacing(4)

        controls = (self.minimizeButton, self.maximizeButton, self.closeButton)
        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.setSpacing(6)
        for button in controls:
            controlLayout.addWidget(button)

        if sys.platform == 'darwin':
            layout.addLayout(controlLayout)
            layout.addSpacing(8)
            layout.addWidget(self.appIconLabel)
            layout.addWidget(self.titleLabel)
        else:
            layout.addWidget(self.appIconLabel)
            layout.addWidget(self.titleLabel)

        layout.addSpacing(8)
        for widget in self.commandWidgets:
            layout.addWidget(widget)
        layout.addStretch(1)
        layout.addWidget(overflowButton)

        if sys.platform != 'darwin':
            layout.addSpacing(8)
            layout.addLayout(controlLayout)

    def _windowButton(self, role, text):
        button = QPushButton(text)
        button.setProperty('windowControl', True)
        button.setProperty('windowControlRole', role)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setFixedSize(20, 20)
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

    def contextMenuEvent(self, event):
        interactive = (
            *self.commandWidgets,
            self.overflowButton,
            self.minimizeButton,
            self.maximizeButton,
            self.closeButton,
        )
        if any(widget.geometry().contains(event.pos()) for widget in interactive):
            event.ignore()
            return

        menu = self.overflowButton.menu()
        if menu is not None:
            menu.popup(event.globalPos())
            event.accept()
            return
        super().contextMenuEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggleMaximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
