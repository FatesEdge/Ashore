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


def contrastText(color):
    value = QColor(color)
    luminance = (value.red() * 299 + value.green() * 587 + value.blue() * 114) / 1000
    return '#171717' if luminance > 165 else '#ffffff'


def translucent(color, alpha):
    value = QColor(color)
    return f'rgba({value.red()}, {value.green()}, {value.blue()}, {alpha})'


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
        if self.mode == 'system':
            palette = QPalette(self.systemPalette)
        elif self.mode == 'light':
            palette = self.lightPalette()
        else:
            palette = self.darkPalette()
        accentColor = QColor(self.accent)
        palette.setColor(QPalette.ColorRole.Highlight, accentColor)
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(contrastText(accentColor)))
        palette.setColor(QPalette.ColorRole.Link, accentColor)
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
    def lightPalette():
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor('#f4f5f7'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('#202124'))
        palette.setColor(QPalette.ColorRole.Base, QColor('#ffffff'))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#eceff1'))
        palette.setColor(QPalette.ColorRole.Text, QColor('#202124'))
        palette.setColor(QPalette.ColorRole.Button, QColor('#f8f9fa'))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor('#202124'))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor('#ffffff'))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor('#202124'))
        return palette

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
        text = contrastText(self.accent)
        windowText = '#f2f2f2' if dark else '#202124'
        fieldBackground = '#1d1d1d' if dark else '#ffffff'
        subtle = translucent(self.accent, 55 if dark else 34)
        cardBackground = translucent(self.accent, 105 if dark else 54)
        return f'''
            QPushButton {{
                background-color: {subtle}; border: 1px solid {self.accent};
                border-radius: 6px; padding: 4px 10px; color: {windowText};
            }}
            QPushButton:hover {{ background-color: {self.accent}; color: {text}; border-color: {hover}; }}
            QPushButton:pressed, QPushButton:checked {{ background-color: {pressed}; color: {text}; }}
            QPushButton:disabled {{ background-color: transparent; color: #888888; border-color: #777777; }}
            QPushButton[toolbarButton="true"] {{
                min-width: 38px; max-width: 38px; min-height: 34px; max-height: 34px;
                border-radius: 8px; padding: 0; background-color: transparent;
            }}
            QPushButton[navigationTab="true"]:checked {{
                background-color: {self.accent}; color: {text}; border-color: {hover};
            }}
            QPushButton[settingsButton="true"] {{
                background-color: {self.accent}; color: {text}; border-color: {hover};
            }}
            QPushButton[settingsButton="true"]:hover {{ background-color: {hover}; }}
            QPushButton[settingsButton="true"]:pressed {{ background-color: {pressed}; }}
            QPushButton[cardAction="true"] {{
                min-width: 23px; max-width: 23px; min-height: 23px; max-height: 23px;
                padding: 0; border-radius: 4px; background-color: {subtle};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {self.accent}; }}
            QProgressBar {{
                background-color: {fieldBackground}; color: {text}; border: 1px solid {self.accent};
                border-radius: 4px; text-align: center;
            }}
            QProgressBar::chunk {{ background-color: {self.accent}; }}
            QFrame[downloadCard="true"] {{ background-color: {cardBackground}; border: 1px solid {self.accent}; border-radius: 6px; }}
            QFrame[downloadCard="true"]:hover {{ border: 2px solid {hover}; }}
        '''
