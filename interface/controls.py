"""Ashore-styled native controls with palette-aware accent arrows."""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPainter, QPalette, QPen
from PyQt6.QtWidgets import (
    QComboBox, QSpinBox, QStyle, QStyleOptionComboBox, QStyleOptionSpinBox,
)


def _drawChevron(widget, painter, rect, direction):
    palette = widget.palette()
    if widget.isEnabled():
        color = palette.color(QPalette.ColorRole.Highlight)
    else:
        color = palette.color(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)

    center = rect.center()
    width = min(8.0, max(5.0, rect.width() * 0.34))
    height = min(4.0, max(2.5, rect.height() * 0.18))
    if direction == 'up':
        points = (
            QPointF(center.x() - width / 2, center.y() + height / 2),
            QPointF(center.x(), center.y() - height / 2),
            QPointF(center.x() + width / 2, center.y() + height / 2),
        )
    else:
        points = (
            QPointF(center.x() - width / 2, center.y() - height / 2),
            QPointF(center.x(), center.y() + height / 2),
            QPointF(center.x() + width / 2, center.y() - height / 2),
        )

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, 1.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawLine(points[0], points[1])
    painter.drawLine(points[1], points[2])
    painter.restore()


class AshoreComboBox(QComboBox):
    """Native combo behaviour with an Ashore accent chevron."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def hasWheelFocus(self):
        editor = self.lineEdit()
        return self.hasFocus() or (editor is not None and editor.hasFocus())

    def wheelEvent(self, event):
        if self.hasWheelFocus():
            super().wheelEvent(event)
        else:
            event.ignore()

    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            option,
            QStyle.SubControl.SC_ComboBoxArrow,
            self)
        painter = QPainter(self)
        _drawChevron(self, painter, rect, 'down')


class AshoreSpinBox(QSpinBox):
    """Native spin behaviour with Ashore accent chevrons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def hasWheelFocus(self):
        editor = self.lineEdit()
        return self.hasFocus() or (editor is not None and editor.hasFocus())

    def wheelEvent(self, event):
        if self.hasWheelFocus():
            super().wheelEvent(event)
        else:
            event.ignore()

    def paintEvent(self, event):
        super().paintEvent(event)
        option = QStyleOptionSpinBox()
        self.initStyleOption(option)
        nativeUpRect = self.style().subControlRect(
            QStyle.ComplexControl.CC_SpinBox,
            option,
            QStyle.SubControl.SC_SpinBoxUp,
            self)

        buttonWidth = max(20, nativeUpRect.width())
        separatorX = self.width() - buttonWidth - 1
        top = 1.0
        bottom = float(self.height() - 1)
        middle = self.height() / 2.0

        upRect = QRectF(
            separatorX + 1, top,
            buttonWidth, max(1.0, middle - top))
        downRect = QRectF(
            separatorX + 1, middle,
            buttonWidth, max(1.0, bottom - middle))

        painter = QPainter(self)
        painter.save()
        borderColor = self.palette().color(QPalette.ColorRole.Mid)
        pen = QPen(borderColor, 1.0)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(separatorX, top),
            QPointF(separatorX, bottom))
        painter.drawLine(
            QPointF(separatorX, middle),
            QPointF(self.width() - 1, middle))
        painter.restore()

        _drawChevron(self, painter, upRect, 'up')
        _drawChevron(self, painter, downRect, 'down')
