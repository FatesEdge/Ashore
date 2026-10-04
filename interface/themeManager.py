"""Central application palette and accent styling."""

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QColor, QPalette

THEME_MODES = ('system', 'light', 'dark')
ACCENT_PRESETS = (
    '#5d795f', '#3f7cac', '#7b5ea7', '#b56576', '#b7791f', '#287271',
)
TRAY_GRAY = QColor('#9b9b9b')


def validColor(value, fallback='#5d795f'):
    color = QColor(value)
    return color.name() if color.isValid() else fallback


class ThemeManager(QObject):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.systemPalette = QPalette(app.palette())
        self.mode = 'system'
        self.accent = ACCENT_PRESETS[0]
        hints = app.styleHints()
        if hasattr(hints, 'colorSchemeChanged'):
            hints.colorSchemeChanged.connect(self.refreshSystemTheme)

    def apply(self, mode='system', accent=None):
        self.mode = mode if mode in THEME_MODES else 'system'
        self.accent = validColor(accent or self.accent)
        dark = self.isDarkMode()
        if self.mode == 'system' and not dark:
            palette = QPalette(self.systemPalette)
        else:
            palette = self.darkPalette() if dark else self.app.style().standardPalette()
        self.app.setPalette(palette)
        self.app.setStyleSheet(self.styleSheet(dark))

    def isDarkMode(self):
        if self.mode == 'dark':
            return True
        if self.mode == 'light':
            return False
        hints = self.app.styleHints()
        scheme = hints.colorScheme() if hasattr(hints, 'colorScheme') else Qt.ColorScheme.Unknown
        if scheme != Qt.ColorScheme.Unknown:
            return scheme == Qt.ColorScheme.Dark
        return self.systemPalette.color(QPalette.ColorRole.Window).lightness() < 128

    def refreshSystemTheme(self, *_):
        if self.mode == 'system':
            self.apply(self.mode, self.accent)

    @staticmethod
    def darkPalette():
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor('#242424'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('#f2f2f2'))
        palette.setColor(QPalette.ColorRole.Base, QColor('#1d1d1d'))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#2c2c2c'))
        palette.setColor(QPalette.ColorRole.Text, QColor('#f2f2f2'))
        palette.setColor(QPalette.ColorRole.Button, QColor('#303030'))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor('#f2f2f2'))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor('#303030'))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor('#f2f2f2'))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor('#ffffff'))
        return palette

    def styleSheet(self, dark):
        hover = QColor(self.accent).lighter(115).name()
        pressed = QColor(self.accent).darker(120).name()
        border = '#666666' if dark else '#a0a0a0'
        cardBackground = QColor(self.accent).darker(180 if dark else 110).name()
        return f'''
            QPushButton {{ border: 1px solid {border}; border-radius: 5px; padding: 4px 10px; }}
            QPushButton:hover {{ border-color: {hover}; }}
            QPushButton:pressed, QPushButton:checked {{ background-color: {pressed}; color: white; }}
            QPushButton[navigationTab="true"] {{ border-radius: 8px; padding: 5px; }}
            QPushButton[navigationTab="true"]:checked {{ background-color: {self.accent}; color: white; }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {self.accent}; }}
            QProgressBar::chunk {{ background-color: {self.accent}; }}
            QFrame[downloadCard="true"] {{ background-color: {cardBackground}; border: 1px solid {self.accent}; border-radius: 6px; }}
            QFrame[downloadCard="true"]:hover {{ border: 2px solid {hover}; }}
        '''
