"""Cross-platform client-side window chrome.

The application paints its own top bar, while move/resize operations are still
delegated to the platform window manager through QWindow.
"""

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QWidget


class WindowChrome(QObject):
    """Provide frameless chrome without reimplementing window geometry."""

    resizeMargin = 6

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._installed = False
        self.window.destroyed.connect(self._hostDestroyed)

    def install(self):
        flags = self.window.windowFlags() | Qt.WindowType.FramelessWindowHint
        self.window.setWindowFlags(flags)
        self.window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        QApplication.instance().installEventFilter(self)
        self._installed = True

    def uninstall(self):
        app = QApplication.instance()
        if self._installed and app is not None:
            app.removeEventFilter(self)
        self._installed = False

    def _hostDestroyed(self):
        self.uninstall()
        self.window = None

    def eventFilter(self, watched, event):
        if self.window is None or sip.isdeleted(self.window):
            self.window = None
            self._installed = False
            return False
        if not isinstance(watched, QWidget):
            return False
        if watched is not self.window and not self.window.isAncestorOf(watched):
            return False
        if self.window.isMaximized() or self.window.isFullScreen():
            if event.type() == QEvent.Type.MouseMove:
                self.window.unsetCursor()
            return False

        if event.type() == QEvent.Type.MouseMove:
            edges = self._edgesAt(event.globalPosition())
            self._applyCursor(self.window, edges)
        elif event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                edges = self._edgesAt(event.globalPosition())
                if edges:
                    handle = self.window.windowHandle()
                    if handle is not None and handle.startSystemResize(edges):
                        return True
        return False

    def _edgesAt(self, globalPosition):
        point = self.window.mapFromGlobal(globalPosition.toPoint())
        margin = self.resizeMargin
        rect = self.window.rect()

        edges = Qt.Edge(0)
        if point.x() <= margin:
            edges |= Qt.Edge.LeftEdge
        elif point.x() >= rect.width() - margin - 1:
            edges |= Qt.Edge.RightEdge
        if point.y() <= margin:
            edges |= Qt.Edge.TopEdge
        elif point.y() >= rect.height() - margin - 1:
            edges |= Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def _applyCursor(widget, edges):
        horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
        vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
        if horizontal and vertical:
            sameDiagonal = bool(edges & Qt.Edge.LeftEdge and edges & Qt.Edge.TopEdge) or bool(
                edges & Qt.Edge.RightEdge and edges & Qt.Edge.BottomEdge)
            shape = Qt.CursorShape.SizeFDiagCursor if sameDiagonal else Qt.CursorShape.SizeBDiagCursor
            widget.setCursor(QCursor(shape))
        elif horizontal:
            widget.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif vertical:
            widget.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        else:
            widget.unsetCursor()
