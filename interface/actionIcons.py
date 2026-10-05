"""Standardized runtime-tinted action icons for Ashore."""

from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap, QPalette
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

from paths import RESOURCE_DIR


ACTION_NAMES = {
    'add', 'copy', 'delete', 'hide', 'info', 'more', 'open-file',
    'open-folder', 'pause', 'play', 'quit', 'remove', 'restart',
    'retry', 'save', 'show', 'download', 'completed', 'settings',
    'chevron-down', 'chevron-right',
}
DANGER_COLOR = '#c42b1c'


def actionIcon(name, color=None, size=20):
    """Return a consistently sized monochrome SVG icon tinted for the current palette."""
    if name not in ACTION_NAMES:
        raise ValueError(f'Unknown action icon: {name}')

    iconPath = Path(RESOURCE_DIR) / 'static/icon/actions' / f'{name}.svg'
    renderer = QSvgRenderer(str(iconPath))
    if not renderer.isValid():
        return QIcon()

    size = max(12, int(size))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)

    if color is None:
        app = QApplication.instance()
        color = (
            app.palette().color(QPalette.ColorRole.WindowText)
            if app is not None else QColor('#30343a')
        )
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)
