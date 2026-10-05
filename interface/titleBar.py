"""Frameless Ashore window chrome with native system move/resize gestures."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QSizePolicy, QToolButton, QWidget,
)


class WindowFrame(QWidget):
    RESIZE_MARGIN = 5

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setProperty('windowFrame', True)
        self.setMouseTracking(True)

    def edgeAt(self, position):
        if self.window.isMaximized():
            return Qt.Edge(0)
        margin = self.RESIZE_MARGIN
        rect = self.rect()
        edges = Qt.Edge(0)
        if position.x() <= margin:
            edges |= Qt.Edge.LeftEdge
        elif position.x() >= rect.width() - margin:
            edges |= Qt.Edge.RightEdge
        if position.y() <= margin:
            edges |= Qt.Edge.TopEdge
        elif position.y() >= rect.height() - margin:
            edges |= Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def cursorForEdges(edges):
        horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
        vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
        if horizontal and vertical:
            if ((edges & Qt.Edge.LeftEdge and edges & Qt.Edge.TopEdge)
                    or (edges & Qt.Edge.RightEdge and edges & Qt.Edge.BottomEdge)):
                return Qt.CursorShape.SizeFDiagCursor
            return Qt.CursorShape.SizeBDiagCursor
        if horizontal:
            return Qt.CursorShape.SizeHorCursor
        if vertical:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def mouseMoveEvent(self, event):
        self.setCursor(self.cursorForEdges(self.edgeAt(event.position())))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.unsetCursor()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self.edgeAt(event.position())
            handle = self.window.windowHandle()
            if edges and handle is not None and handle.startSystemResize(edges):
                event.accept()
                return
        super().mousePressEvent(event)


class AshoreTitleBar(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setProperty('customTitleBar', True)
        self.setFixedHeight(40)

        self.titleLabel = QLabel(window.windowTitle() or 'Ashore')
        self.titleLabel.setProperty('windowTitleText', True)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.titleLabel.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.leftSpacer = QWidget()
        self.controls = QWidget()
        controlsLayout = QHBoxLayout(self.controls)
        controlsLayout.setContentsMargins(0, 0, 0, 0)
        controlsLayout.setSpacing(4)

        self.minimizeButton = self.makeButton('−', 'minimize')
        self.maximizeButton = self.makeButton('□', 'maximize')
        self.closeButton = self.makeButton('×', 'close')
        controlsLayout.addWidget(self.minimizeButton)
        controlsLayout.addWidget(self.maximizeButton)
        controlsLayout.addWidget(self.closeButton)

        self.leftSpacer.setFixedWidth(self.controls.sizeHint().width())
        self.leftSpacer.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 8, 0)
        layout.setSpacing(0)
        layout.addWidget(self.leftSpacer)
        layout.addWidget(self.titleLabel, 1)
        layout.addWidget(self.controls)

        self.minimizeButton.clicked.connect(window.showMinimized)
        self.maximizeButton.clicked.connect(self.toggleMaximized)
        self.closeButton.clicked.connect(window.close)

    def makeButton(self, text, role):
        button = QToolButton(self)
        button.setText(text)
        button.setProperty('windowControl', True)
        button.setProperty('windowControlRole', role)
        button.setFixedSize(28, 28)
        return button

    def toggleMaximized(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()
        self.syncState()

    def syncState(self):
        self.maximizeButton.setText('❐' if self.window.isMaximized() else '□')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window.windowHandle()
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
