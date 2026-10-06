"""Standardized runtime-tinted action icons for Ashore."""

from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap, QPalette
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

from paths import RESOURCE_DIR


ACTION_NAMES = {
    'add', 'copy', 'delete', 'hide', 'info', 'menu', 'more', 'open-file',
    'open-folder', 'pause', 'play', 'quit', 'remove', 'restart',
    'retry', 'save', 'show', 'download', 'completed', 'settings',
    'chevron-down', 'chevron-right',
}
DANGER_COLOR = '#c42b1c'


def displayDevicePixelRatio():
    """Return the current desktop scale for crisp rasterized SVG actions."""
    app = QApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    if screen is None:
        return 1.0
    return max(1.0, float(screen.devicePixelRatio()))


def actionIcon(name, color=None, size=20, devicePixelRatio=None):
    """Return a palette-tinted SVG icon rendered at native display density."""
    if name not in ACTION_NAMES:
        raise ValueError(f'Unknown action icon: {name}')

    iconPath = Path(RESOURCE_DIR) / 'static/icon/actions' / f'{name}.svg'
    renderer = QSvgRenderer(str(iconPath))
    if not renderer.isValid():
        return QIcon()

    size = max(12, int(size))
    ratio = (
        displayDevicePixelRatio()
        if devicePixelRatio is None
        else max(1.0, float(devicePixelRatio))
    )
    pixmap = QPixmap(
        max(1, round(size * ratio)),
        max(1, round(size * ratio)))
    pixmap.setDevicePixelRatio(ratio)
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
