"""Platform-aware Ashore title and command bar."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class TitleBar(QWidget):
    """Use native macOS window chrome and custom chrome elsewhere."""

    def __init__(self, window, commandWidgets, overflowButton, parent=None):
        super().__init__(parent)
        self.hostWindow = window
        self.commandWidgets = tuple(commandWidgets)
        self.overflowButton = overflowButton
        self.nativeChrome = sys.platform == 'darwin'

        self.setProperty('titleBar', not self.nativeChrome)
        self.setProperty('commandBar', self.nativeChrome)
        self.setFixedHeight(40 if self.nativeChrome else 36)

        self.appIconLabel = None
        self.titleLabel = None
        self.minimizeButton = None
        self.maximizeButton = None
        self.closeButton = None

        layout = QHBoxLayout(self)
        layout.setSpacing(4)

        commandLayout = QHBoxLayout()
        commandLayout.setContentsMargins(0, 1, 0, 0)
        commandLayout.setSpacing(4)
        for widget in self.commandWidgets:
            commandLayout.addWidget(widget)

        if self.nativeChrome:
            # The actual title, traffic-light controls, dragging and fullscreen
            # behaviour belong to the native macOS title bar above this row.
            layout.setContentsMargins(12, 5, 12, 4)
            layout.addLayout(commandLayout)
            layout.addStretch(1)
            layout.addWidget(self.overflowButton)
            return

        self.appIconLabel = QLabel()
        self.appIconLabel.setProperty('windowIcon', True)
        self.appIconLabel.setFixedSize(20, 20)
        self.appIconLabel.setPixmap(self.hostWindow.windowIcon().pixmap(18, 18))
        self.appIconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.appIconLabel.setContentsMargins(1, 4, 0, 0)
        self.appIconLabel.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.titleLabel = QLabel('Ashore')
        self.titleLabel.setProperty('windowTitle', True)
        self.titleLabel.setContentsMargins(8, 0, 0, 0)
        self.titleLabel.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.minimizeButton = self._windowButton('minimize', '−')
        self.maximizeButton = self._windowButton('maximize', '□')
        self.closeButton = self._windowButton('close', '×')

        self.minimizeButton.clicked.connect(self.hostWindow.showMinimized)
        self.maximizeButton.clicked.connect(self.toggleMaximized)
        self.closeButton.clicked.connect(self.hostWindow.close)

        layout.setContentsMargins(14, 4, 12, 2)
        layout.addWidget(self.appIconLabel)
        layout.addSpacing(2)
        layout.addWidget(self.titleLabel)
        layout.addSpacing(8)
        layout.addLayout(commandLayout)
        layout.addStretch(1)
        layout.addWidget(self.overflowButton)
        layout.addSpacing(8)

        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 3, 0, 0)
        controlLayout.setSpacing(6)
        for button in (
                self.minimizeButton, self.maximizeButton, self.closeButton):
            controlLayout.addWidget(button)
        layout.addLayout(controlLayout)

    def _windowButton(self, role, text):
        button = QPushButton(text)
        button.setProperty('windowControl', True)
        button.setProperty('windowControlRole', role)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setFixedSize(20, 20)
        return button

    def toggleMaximized(self):
        if self.nativeChrome:
            return
        if self.hostWindow.isMaximized():
            self.hostWindow.showNormal()
        else:
            self.hostWindow.showMaximized()
        self.syncWindowState()

    def syncWindowState(self):
        if self.maximizeButton is not None:
            self.maximizeButton.setText(
                '❐' if self.hostWindow.isMaximized() else '□')

    def mousePressEvent(self, event):
        if (not self.nativeChrome
                and event.button() == Qt.MouseButton.LeftButton):
            handle = self.hostWindow.windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        interactive = [*self.commandWidgets, self.overflowButton]
        if not self.nativeChrome:
            interactive.extend((
                self.minimizeButton,
                self.maximizeButton,
                self.closeButton,
            ))
        if any(
                widget is not None
                and widget.geometry().contains(event.pos())
                for widget in interactive):
            event.ignore()
            return

        menu = self.overflowButton.menu()
        if menu is not None:
            menu.popup(event.globalPos())
            event.accept()
            return
        super().contextMenuEvent(event)

    def mouseDoubleClickEvent(self, event):
        if (not self.nativeChrome
                and event.button() == Qt.MouseButton.LeftButton):
            self.toggleMaximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
