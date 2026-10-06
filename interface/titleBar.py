"""Ashore integrated command bar and frameless window chrome."""

import sys

from PyQt6.QtCore import QEvent, QRect, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QStyle, QStyleOptionTitleBar, QToolButton, QWidget,
)


class WindowFrame(QWidget):
    RESIZE_MARGIN = 5

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setProperty('windowFrame', True)
        self.setMouseTracking(True)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def edgeAt(self, position):
        if self.window.isMaximized():
            return None
        margin = self.RESIZE_MARGIN
        rect = self.rect()
        edges = None

        def addEdge(current, edge):
            return edge if current is None else current | edge

        if position.x() <= margin:
            edges = addEdge(edges, Qt.Edge.LeftEdge)
        elif position.x() >= rect.width() - margin:
            edges = addEdge(edges, Qt.Edge.RightEdge)
        if position.y() <= margin:
            edges = addEdge(edges, Qt.Edge.TopEdge)
        elif position.y() >= rect.height() - margin:
            edges = addEdge(edges, Qt.Edge.BottomEdge)
        return edges

    @staticmethod
    def cursorForEdges(edges):
        if edges is None:
            return Qt.CursorShape.ArrowCursor
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

    def belongsToWindow(self, watched):
        return (
            isinstance(watched, QWidget)
            and (watched is self.window
                 or self.window.isAncestorOf(watched)))

    def updateResizeCursor(self):
        position = self.mapFromGlobal(QCursor.pos())
        edges = self.edgeAt(position)
        if edges is None:
            self.unsetCursor()
        else:
            self.setCursor(self.cursorForEdges(edges))
        return edges

    def eventFilter(self, watched, event):
        if self.belongsToWindow(watched):
            if event.type() in (
                    QEvent.Type.Enter,
                    QEvent.Type.MouseMove,
                    QEvent.Type.HoverMove):
                self.updateResizeCursor()
            elif event.type() == QEvent.Type.MouseButtonPress:
                edges = self.updateResizeCursor()
                if (edges is not None
                        and event.button() == Qt.MouseButton.LeftButton):
                    handle = self.window.windowHandle()
                    if (handle is not None
                            and handle.startSystemResize(edges)):
                        return True
            elif event.type() == QEvent.Type.Leave and watched is self.window:
                self.unsetCursor()
        return super().eventFilter(watched, event)


class AshoreTitleBar(QWidget):
    """One top row for commands, dragging, overflow, and native-order controls."""

    def __init__(
            self, window, addButton, startButton, pauseButton, moreButton):
        super().__init__(window)
        self.window = window
        self.setProperty('customTitleBar', True)
        self.setProperty('commandBar', True)
        self.setFixedHeight(40)

        self.minimizeButton = self.makeButton('−', 'minimize')
        self.maximizeButton = self.makeButton('□', 'maximize')
        self.closeButton = self.makeButton('×', 'close')
        self.windowButtons = {
            'minimize': self.minimizeButton,
            'maximize': self.maximizeButton,
            'close': self.closeButton,
        }

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        controlsLeft, controlOrder = self.nativeControlLayout()
        if controlsLeft:
            self.addWindowControls(layout, controlOrder)
            layout.addSpacing(4)

        layout.addWidget(addButton)
        layout.addWidget(startButton)
        layout.addWidget(pauseButton)
        layout.addStretch(1)
        layout.addWidget(moreButton)

        if not controlsLeft:
            layout.addSpacing(4)
            self.addWindowControls(layout, controlOrder)

        self.minimizeButton.clicked.connect(window.showMinimized)
        self.maximizeButton.clicked.connect(self.toggleMaximized)
        self.closeButton.clicked.connect(window.close)

    def nativeControlLayout(self):
        """Infer control side and order from the active Qt platform style."""
        option = QStyleOptionTitleBar()
        option.rect = QRect(0, 0, 320, 32)
        option.titleBarFlags = self.window.windowFlags()

        controls = (
            ('minimize', QStyle.SubControl.SC_TitleBarMinButton),
            ('maximize', QStyle.SubControl.SC_TitleBarMaxButton),
            ('close', QStyle.SubControl.SC_TitleBarCloseButton),
        )
        positions = []
        for role, control in controls:
            rect = self.style().subControlRect(
                QStyle.ComplexControl.CC_TitleBar,
                option,
                control,
                self)
            if rect.isValid() and rect.width() > 0:
                positions.append((rect.center().x(), role))

        if len(positions) == len(controls):
            positions.sort()
            center = sum(position for position, _ in positions) / len(positions)
            return center < option.rect.center().x(), [
                role for _, role in positions]

        if sys.platform == 'darwin':
            return True, ['close', 'minimize', 'maximize']
        return False, ['minimize', 'maximize', 'close']

    def addWindowControls(self, layout, order):
        for role in order:
            layout.addWidget(self.windowButtons[role])

    def makeButton(self, text, role):
        button = QToolButton(self)
        button.setText(text)
        button.setProperty('windowControl', True)
        button.setProperty('windowControlRole', role)
        button.setFixedSize(24, 24)
        return button

    def toggleMaximized(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()
        self.syncState()

    def syncState(self):
        self.maximizeButton.setText('▣' if self.window.isMaximized() else '□')

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
