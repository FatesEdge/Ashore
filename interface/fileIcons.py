"""Ashore file icon classification and status-aware SVG composition."""

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

from paths import RESOURCE_DIR


@dataclass(frozen=True)
class FileIconSpec:
    family: str
    label: str
    color: str


FAMILY_COLORS = {
    'video': '#b65d63', 'audio': '#7b63b3', 'image': '#4f8a72',
    'vector': '#c77845', 'archive': '#9b7048', 'document': '#5a7fab',
    'pdf': '#c95e5e', 'spreadsheet': '#4f8a63', 'presentation': '#c77949',
    'code': '#60708a', 'data': '#4f7f88', 'package': '#8069a0',
    'disk': '#687786', 'font': '#a06f8d', 'subtitle': '#567e8d',
    'executable': '#596675', 'torrent': '#3f7cac', 'generic': '#747b84',
}

FAMILY_EXTENSIONS = {
    'video': {'mp4','mkv','mov','avi','webm','m4v','flv','wmv','mpeg','mpg','m2ts','ts','3gp','vob','ogv'},
    'audio': {'mp3','flac','wav','aac','m4a','ogg','opus','wma','aiff','ape','alac','mid','midi'},
    'image': {'jpg','jpeg','png','webp','gif','bmp','tif','tiff','heic','heif','avif','ico','raw','dng'},
    'vector': {'svg','ai','eps','cdr'},
    'archive': {'zip','7z','rar','tar','gz','bz2','xz','tgz','tbz','txz','tar.gz','tar.bz2','tar.xz','ace'},
    'document': {'txt','rtf','doc','docx','odt','pages','md','markdown','epub','mobi','azw3'},
    'pdf': {'pdf'},
    'spreadsheet': {'xls','xlsx','csv','tsv','ods'},
    'presentation': {'ppt','pptx','odp','key'},
    'code': {'py','pyw','c','cc','cpp','cxx','h','hpp','js','mjs','ts','tsx','jsx','java','kt','kts','rs','go','rb','php','css','scss','sass','less','sh','bash','zsh','fish','ps1','lua','swift','dart','vue','svelte'},
    'data': {'json','xml','yaml','yml','toml','ini','conf','sql','db','sqlite','sqlite3'},
    'package': {'deb','rpm','apk','pkg','dmg','msi','appimage','snap','flatpak'},
    'disk': {'iso','img','vhd','vhdx','qcow','qcow2'},
    'font': {'ttf','otf','woff','woff2'},
    'subtitle': {'srt','ass','ssa','vtt','sub'},
    'executable': {'exe','bin','run','com','bat','cmd'},
    'torrent': {'torrent'},
}

FORMAT_LABELS = {
    'jpeg': 'JPEG', 'tiff': 'TIFF', 'markdown': 'MD',
    'tar.gz': 'TGZ', 'tar.bz2': 'TBZ', 'tar.xz': 'TXZ',
    'appimage': 'APP', 'sqlite3': 'SQL',
}
GLYPH_SCALE = {
    'disk': 0.86,
    'font': 0.88,
    'code': 0.92,
    'torrent': 0.90,
}
PAUSED_COLOR = QColor('#858585')
ERROR_COLOR = QColor('#767676')
ERROR_BADGE_COLOR = QColor('#c42b1c')


def extensionForFile(fileName):
    cleanName = str(fileName or '').split('?', 1)[0].split('#', 1)[0].lower()
    for compound in ('tar.gz', 'tar.bz2', 'tar.xz'):
        if cleanName.endswith('.' + compound):
            return compound
    return Path(cleanName).suffix.lstrip('.')


def familyForExtension(extension):
    for family, extensions in FAMILY_EXTENSIONS.items():
        if extension in extensions:
            return family
    return 'generic'


def labelForExtension(extension, family):
    if family == 'torrent':
        return 'BT'
    if not extension:
        return 'FILE'
    label = FORMAT_LABELS.get(extension, extension.upper())
    return label if len(label) <= 6 else label[:5] + '…'


def fileIconSpec(fileName, isTorrent=False):
    extension = extensionForFile(fileName)
    family = familyForExtension(extension)
    if family == 'generic' and isTorrent:
        family = 'torrent'
    label = labelForExtension(extension, family)
    return FileIconSpec(family, label, FAMILY_COLORS[family])


def mixColor(first, second, amount):
    amount = max(0.0, min(1.0, amount))
    return QColor(
        round(first.red() * (1 - amount) + second.red() * amount),
        round(first.green() * (1 - amount) + second.green() * amount),
        round(first.blue() * (1 - amount) + second.blue() * amount),
    )


def iconColorForStatus(baseColor, status):
    base = QColor(baseColor)
    if status == 'waiting':
        return mixColor(base, QColor('#9aa1a9'), 0.42)
    if status == 'paused':
        return QColor(PAUSED_COLOR)
    if status == 'error':
        return QColor(ERROR_COLOR)
    return base


def statusHasErrorBadge(status):
    return status == 'error'


def fitSvgRect(renderer, bounds, scale=1.0):
    viewBox = renderer.viewBoxF()
    if viewBox.width() <= 0 or viewBox.height() <= 0:
        return bounds
    availableWidth = bounds.width() * scale
    availableHeight = bounds.height() * scale
    ratio = min(
        availableWidth / viewBox.width(),
        availableHeight / viewBox.height())
    width = viewBox.width() * ratio
    height = viewBox.height() * ratio
    return QRectF(
        bounds.center().x() - width / 2,
        bounds.center().y() - height / 2,
        width,
        height,
    )


def fileIconPixmap(fileName, isTorrent=False, status='active', size=52):
    spec = fileIconSpec(fileName, isTorrent)
    size = max(32, int(size))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(iconColorForStatus(spec.color, status))
    radius = size * 0.18
    painter.drawRoundedRect(
        QRectF(0.5, 0.5, size - 1.0, size - 1.0), radius, radius)

    renderer = QSvgRenderer(
        str(RESOURCE_DIR / 'static/icon/fileTypes' / f'{spec.family}.svg'))
    if renderer.isValid():
        bounds = QRectF(
            size * 0.18, size * 0.07, size * 0.64, size * 0.51)
        renderer.render(
            painter,
            fitSvgRect(
                renderer, bounds, GLYPH_SCALE.get(spec.family, 1.0)))

    font = QFont()
    font.setBold(True)
    font.setPixelSize(
        max(7, int(size * (0.155 if len(spec.label) <= 4 else 0.13))))
    painter.setFont(font)
    painter.setPen(QColor('#ffffff'))
    painter.drawText(
        QRectF(size * 0.08, size * 0.61, size * 0.84, size * 0.28),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        spec.label,
    )

    if statusHasErrorBadge(status):
        badgeSize = size * 0.27
        badgeRect = QRectF(
            size - badgeSize - size * 0.02,
            size * 0.02,
            badgeSize,
            badgeSize,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ERROR_BADGE_COLOR)
        painter.drawEllipse(badgeRect)
        badgeFont = QFont()
        badgeFont.setBold(True)
        badgeFont.setPixelSize(max(8, int(badgeSize * 0.72)))
        painter.setFont(badgeFont)
        painter.setPen(QColor('#ffffff'))
        painter.drawText(
            badgeRect,
            Qt.AlignmentFlag.AlignCenter,
            '!',
        )

    painter.end()
    return pixmap
