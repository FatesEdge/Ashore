"""Cross-platform client-side window chrome.

The application paints its own top bar, while move/resize operations are still
delegated to the platform window manager through QWindow.
"""

from PyQt6 import sip
from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QWidget


class WindowChrome(QObject):
    """Provide frameless chrome scoped to one application window."""

    resizeMargin = 6

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._installed = False

    def install(self):
        if self._installed or self.window is None or sip.isdeleted(self.window):
            return

        flags = self.window.windowFlags() | Qt.WindowType.FramelessWindowHint
        self.window.setWindowFlags(flags)
        self.window.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._installOnSubtree(self.window)
        self._installed = True

    def uninstall(self):
        if (self._installed and self.window is not None
                and not sip.isdeleted(self.window)):
            self._removeFromSubtree(self.window)
        self._installed = False

    def _installOnSubtree(self, widget):
        widget.installEventFilter(self)
        for child in widget.findChildren(
                QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            self._installOnSubtree(child)

    def _removeFromSubtree(self, widget):
        widget.removeEventFilter(self)
        for child in widget.findChildren(
                QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            self._removeFromSubtree(child)

    def eventFilter(self, watched, event):
        if self.window is None or sip.isdeleted(self.window):
            self._installed = False
            return False

        if event.type() == QEvent.Type.ChildAdded:
            child = event.child()
            if self._installed and isinstance(child, QWidget):
                self._installOnSubtree(child)
            return False

        if not isinstance(watched, QWidget):
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
        horizontal = bool(
            edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
        vertical = bool(
            edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
        if horizontal and vertical:
            sameDiagonal = bool(
                edges & Qt.Edge.LeftEdge and edges & Qt.Edge.TopEdge
            ) or bool(
                edges & Qt.Edge.RightEdge and edges & Qt.Edge.BottomEdge)
            shape = (
                Qt.CursorShape.SizeFDiagCursor
                if sameDiagonal
                else Qt.CursorShape.SizeBDiagCursor)
            widget.setCursor(QCursor(shape))
        elif horizontal:
            widget.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        elif vertical:
            widget.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        else:
            widget.unsetCursor()
