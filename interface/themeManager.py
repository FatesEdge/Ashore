"""Central Ashore palette, design tokens, and semantic widget styling."""

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QColor, QPalette

THEME_MODES = ('system', 'light', 'dark')
ACCENT_PRESETS = (
    '#1c71d8', '#3f7cac', '#7b5ea7', '#b56576', '#b7791f', '#287271',
)
TRAY_GRAY = QColor('#9b9b9b')


def validColor(value, fallback='#1c71d8'):
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
        palette.setColor(QPalette.ColorRole.Window, QColor('#f3f4f6'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('#1f2328'))
        palette.setColor(QPalette.ColorRole.Base, QColor('#ffffff'))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#f7f8fa'))
        palette.setColor(QPalette.ColorRole.Text, QColor('#1f2328'))
        palette.setColor(QPalette.ColorRole.Button, QColor('#f8f9fb'))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor('#1f2328'))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor('#ffffff'))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor('#1f2328'))
        return palette

    @staticmethod
    def darkPalette():
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor('#1f2023'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('#f1f3f5'))
        palette.setColor(QPalette.ColorRole.Base, QColor('#27282c'))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#2d2f34'))
        palette.setColor(QPalette.ColorRole.Text, QColor('#f1f3f5'))
        palette.setColor(QPalette.ColorRole.Button, QColor('#2d2f34'))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor('#f1f3f5'))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor('#2d2f34'))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor('#f1f3f5'))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor('#ffffff'))
        return palette

    def styleSheet(self, dark):
        token = self.tokens(dark)
        accentHover = QColor(self.accent).lighter(112 if dark else 108).name()
        accentPressed = QColor(self.accent).darker(118).name()
        accentText = contrastText(self.accent)
        accentSoft = translucent(self.accent, 52 if dark else 34)
        return f"""
            QMainWindow, QWidget#mainRoot {{
                background: transparent;
                color: {token['text']};
            }}
            QWidget[windowSurface="true"] {{
                background: {token['background']};
                border: none;
                border-radius: 12px;
            }}
            QWidget[windowSurface="true"][windowMaximized="true"],
            QWidget[windowSurface="true"][nativeChrome="true"] {{
                border-radius: 0;
            }}
            QWidget[commandBar="true"] {{
                background: {token['surface']};
                border: none;
                border-bottom: 1px solid {token['border']};
            }}
            QWidget[titleBar="true"] {{
                background: {token['surface']};
                border: none;
                border-bottom: 1px solid {token['border']};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
            QWidget[titleBar="true"][windowMaximized="true"] {{
                border-top-left-radius: 0;
                border-top-right-radius: 0;
            }}
            QLabel[windowIcon="true"] {{
                background: transparent;
                border: none;
                padding: 0;
            }}
            QLabel[windowTitle="true"] {{
                background: transparent;
                color: {token['text']};
                border: none;
                padding: 0 6px;
                font-weight: 700;
            }}
            QPushButton[windowControl="true"] {{
                background: {token['raised']};
                color: {token['text']};
                border: 1px solid {token['border']};
                border-radius: 10px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                padding: 0;
                font-weight: 400;
            }}
            QPushButton[windowControlRole="minimize"] {{
                font-size: 10px;
            }}
            QPushButton[windowControlRole="maximize"] {{
                font-size: 8px;
            }}
            QPushButton[windowControlRole="close"] {{
                font-size: 10px;
            }}
            QPushButton[windowControl="true"]:hover {{
                background: {token['hover']};
                border-color: {token['borderStrong']};
            }}
            QPushButton[windowControlRole="close"]:hover {{
                background: #c42b1c;
                color: #ffffff;
                border-color: #c42b1c;
            }}
            QPushButton[windowControl="true"]:pressed {{
                background: {token['pressed']};
            }}
            QPushButton {{
                background: {token['raised']};
                color: {token['text']};
                border: 1px solid {token['border']};
                border-radius: 8px;
                min-height: 28px;
                max-height: 28px;
                padding: 0 11px;
            }}
            QPushButton:hover {{
                background: {token['hover']};
                border-color: {token['borderStrong']};
            }}
            QPushButton:pressed {{ background: {token['pressed']}; }}
            QPushButton:disabled {{
                background: transparent;
                color: {token['disabled']};
                border-color: {token['border']};
            }}
            QPushButton[commandPrimary="true"] {{
                background: {self.accent};
                color: {accentText};
                border: 1px solid {self.accent};
                min-height: 28px;
                max-height: 28px;
                padding: 0 10px;
                font-size: 13px;
                font-weight: 400;
            }}
            QPushButton[primaryAction="true"] {{
                background: {self.accent};
                color: {accentText};
                border: 1px solid {self.accent};
                min-height: 28px;
                max-height: 28px;
                padding: 0 12px;
                font-weight: 600;
            }}
            QPushButton[commandPrimary="true"]:hover,
            QPushButton[primaryAction="true"]:hover {{
                background: {accentHover}; border-color: {accentHover};
            }}
            QPushButton[commandPrimary="true"]:pressed,
            QPushButton[primaryAction="true"]:pressed {{
                background: {accentPressed}; border-color: {accentPressed};
            }}
            QPushButton[commandSecondary="true"] {{
                background: transparent;
                border-color: transparent;
                min-height: 28px;
                max-height: 28px;
                padding: 0 8px;
                font-size: 13px;
                font-weight: 400;
            }}
            QPushButton[commandSecondary="true"]:hover {{
                background: {token['hover']}; border-color: {token['border']};
            }}
            QPushButton[overflowButton="true"] {{
                min-width: 30px; max-width: 30px;
                min-height: 30px; max-height: 30px;
                padding: 0;
                background: transparent;
                border-color: transparent;
                font-size: 20px;
                font-weight: 700;
            }}
            QPushButton[overflowButton="true"]:hover {{
                background: {token['hover']}; border-color: {token['border']};
            }}
            QPushButton[overflowButton="true"]::menu-indicator,
            QPushButton[cardAction="true"]::menu-indicator {{
                image: none; width: 0px;
            }}
            QWidget[navigationRail="true"] {{ background: {token['background']}; }}
            QPushButton[navigationTab="true"] {{
                background: transparent;
                border: none;
                border-radius: 10px;
                padding: 0;
                min-width: 42px;
                max-width: 42px;
                min-height: 52px;
                max-height: 52px;
            }}
            QPushButton[navigationTab="true"]:hover {{
                background: {token['hover']};
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
            }}
            QPushButton[navigationTab="true"]:checked {{
                background: {token['surface']};
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
            }}
            QWidget[pageSurface="true"] {{
                background: {token['surface']};
                border: none;
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            QStackedWidget[pageStack="true"],
            QScrollArea[downloadPage="true"],
            QWidget[pageViewport="true"],
            QWidget[pageBody="true"] {{
                background: transparent;
                border: none;
            }}
            QFrame[downloadCard="true"] {{
                background: {token['raised']};
                border: 1px solid {token['border']};
                border-radius: 10px;
            }}
            QFrame[downloadCard="true"]:hover {{
                background: {token['cardHover']};
                border-color: {token['borderStrong']};
            }}
            QLabel[cardTitle="true"] {{
                color: {token['text']}; font-size: 14px; font-weight: 600;
            }}
            QLabel[cardMeta="true"] {{
                color: {token['muted']}; font-size: 12px;
            }}
            QLabel[cardPercent="true"] {{
                color: {token['text']}; font-size: 14px; font-weight: 600;
            }}
            QPushButton[cardAction="true"] {{
                min-width: 22px; max-width: 22px;
                min-height: 22px; max-height: 22px;
                padding: 0;
                background: transparent;
                border-color: transparent;
                border-radius: 7px;
            }}
            QPushButton[cardAction="true"]:hover {{
                background: {token['hover']}; border-color: {token['border']};
            }}
            QProgressBar[cardProgress="true"] {{
                min-height: 4px; max-height: 4px;
                background: {token['track']};
                border: none;
                border-radius: 2px;
                text-align: center;
            }}
            QProgressBar[cardProgress="true"]::chunk {{
                background: {self.accent}; border-radius: 2px;
            }}
            QWidget[settingsPage="true"],
            QWidget[settingsSurface="true"],
            QScrollArea[settingsScroll="true"],
            QScrollArea[settingsScroll="true"] > QWidget > QWidget {{
                background: transparent;
                border: none;
            }}
            QWidget[settingsSectionHeader="true"] {{
                background: transparent;
                border: none;
            }}
            QLabel[settingsSectionTitle="true"] {{
                color: {token['text']};
                background: transparent;
                border: none;
                font-size: 16px;
                font-weight: 700;
                padding: 0;
            }}
            QFrame[settingsSectionDivider="true"] {{
                background: {token['border']};
                border: none;
                min-height: 1px;
                max-height: 1px;
            }}
            QWidget[settingItem="true"],
            QWidget[settingFieldHost="true"] {{
                background: transparent;
                border: none;
            }}
            QLabel[settingsFormLabel="true"] {{
                color: {token['text']};
                background: transparent;
                border: none;
                padding: 0;
                font-weight: 500;
            }}
            QLabel[settingsSubTitle="true"] {{
                color: {token['text']};
                font-weight: 600;
                padding: 8px 0 4px 0;
            }}

            QComboBox, QSpinBox {{
                background: {token['field']};
                color: {token['text']};
                border: 1px solid {token['border']};
                border-radius: 7px;
                min-height: 28px;
                max-height: 28px;
                padding: 0 28px 0 7px;
                selection-background-color: {self.accent};
                selection-color: {accentText};
            }}
            QComboBox:hover, QSpinBox:hover {{
                border-color: {token['borderStrong']};
            }}
            QComboBox:focus, QSpinBox:focus {{
                border-color: {self.accent};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                background: transparent;
                border: none;
                border-left: 1px solid {token['border']};
                border-top-right-radius: 7px;
                border-bottom-right-radius: 7px;
            }}
            QComboBox::drop-down:hover {{
                background: {accentSoft};
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 10px;
                height: 10px;
            }}
            QSpinBox {{
                padding-right: 26px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border;
                width: 22px;
                background: transparent;
                border: none;
            }}
            QSpinBox::up-button {{
                subcontrol-position: top right;
                border-top-right-radius: 7px;
            }}
            QSpinBox::down-button {{
                subcontrol-position: bottom right;
                border-bottom-right-radius: 7px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: {accentSoft};
            }}
            QSpinBox::up-arrow, QSpinBox::down-arrow {{
                image: none;
                width: 9px;
                height: 9px;
            }}

            QLabel[dialogStatus="true"] {{
                color: {token['muted']};
                background: transparent;
                border: none;
                padding: 2px 0;
            }}
            QTableWidget {{
                background: {token['field']};
                alternate-background-color: {token['surface']};
                color: {token['text']};
                border: 1px solid {token['border']};
                border-radius: 8px;
                gridline-color: {token['border']};
                selection-background-color: {accentSoft};
                selection-color: {token['text']};
            }}
            QHeaderView::section {{
                background: {token['raised']};
                color: {token['muted']};
                border: none;
                border-bottom: 1px solid {token['border']};
                padding: 2px 7px;
                min-height: 22px;
                max-height: 22px;
                font-weight: 500;
            }}
            QLineEdit {{
                background: {token['field']};
                color: {token['text']};
                border: 1px solid {token['border']};
                border-radius: 7px;
                min-height: 28px;
                max-height: 28px;
                padding: 0 7px;
                selection-background-color: {self.accent};
                selection-color: {accentText};
            }}
            QTextEdit {{
                background: {token['field']};
                color: {token['text']};
                border: 1px solid {token['border']};
                border-radius: 7px;
                padding: 4px 7px;
                selection-background-color: {self.accent};
                selection-color: {accentText};
            }}
            QSpinBox QLineEdit {{
                background: transparent;
                border: none;
                border-radius: 0;
                min-height: 0;
                max-height: 16777215px;
                padding: 0;
            }}
            QLineEdit[joinedLeft="true"] {{
                border-top-right-radius: 0;
                border-bottom-right-radius: 0;
            }}
            QPushButton[joinedRight="true"] {{
                border-top-left-radius: 0;
                border-bottom-left-radius: 0;
                border-left: none;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {self.accent};
            }}
            QLineEdit:disabled {{
                background: {token['background']};
                color: {token['disabled']};
                border-color: {token['border']};
            }}
            QToolButton[advancedToggle="true"] {{
                color: {token['text']};
                background: transparent;
                border: 1px solid transparent;
                border-radius: 7px;
                padding: 3px 6px;
                font-weight: 600;
            }}
            QToolButton[trackerToggle="true"] {{
                color: {token['text']};
                background: {token['raised']};
                border: 1px solid {token['border']};
                border-radius: 7px;
                min-height: 26px;
                max-height: 26px;
                padding: 0 8px;
                font-weight: 500;
            }}
            QToolButton[trackerToggle="true"]:hover {{
                background: {token['hover']};
                border-color: {token['borderStrong']};
            }}
            QLabel[trackerStatus="healthy"] {{ color: {token['success']}; }}
            QLabel[trackerStatus="failed"] {{ color: {token['danger']}; }}
            QLabel[trackerStatus="pending"] {{ color: {token['muted']}; }}
            QToolButton[advancedToggle="true"]:hover {{
                background: {token['hover']};
                border-color: {token['border']};
            }}
            QLabel[connectionBadge="true"] {{
                background: transparent;
                border: none;
                padding: 1px 2px;
                font-weight: 500;
            }}
            QLabel[mainConnectionDot="true"] {{
                background: transparent;
                border: none;
                padding: 0;
                font-weight: 700;
            }}
            QLabel[statusMetricText="true"] {{
                background: transparent;
                color: {token['muted']};
                border: none;
                padding: 0;
            }}
            QWidget[recoveryPage="true"] {{
                background: {token['background']};
            }}
            QLabel[recoveryTitle="true"] {{
                color: {token['text']};
                font-size: 24px;
                font-weight: 700;
            }}
            QLabel[recoveryIntro="true"], QLabel[recoveryMeta="true"] {{
                color: {token['muted']};
            }}
            QLabel[recoveryReason="true"] {{
                color: {token['text']};
                font-weight: 600;
            }}
            QPlainTextEdit[terminalBlock="true"] {{
                background: #111317;
                color: #e6edf3;
                border: 1px solid {token['border']};
                border-radius: 8px;
                padding: 10px;
            }}
            QMenu {{
                background: {token['surface']};
                color: {token['text']};
                border: 1px solid {token['border']};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item {{
                border-radius: 6px;
                padding: 7px 24px 7px 10px;
            }}
            QMenu::item:selected {{ background: {accentSoft}; }}
            QMenu::separator {{
                height: 1px; background: {token['border']}; margin: 5px 8px;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 10px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {token['scroll']};
                min-height: 32px;
                border-radius: 4px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {token['scrollHover']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
            QScrollBar:horizontal {{
                background: transparent; height: 10px; margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {token['scroll']};
                min-width: 32px;
                border-radius: 4px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{ background: {token['scrollHover']}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
            QWidget[statusStrip="true"] {{
                background: {token['background']};
                color: {token['muted']};
                border-top: 1px solid {token['border']};
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            QWidget[statusStrip="true"][windowMaximized="true"] {{
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
            }}
            QLabel[statusMessage="true"] {{
                color: {token['muted']};
                background: transparent;
                border: none;
                padding: 0;
            }}
            QToolTip {{
                background: {token['surface']};
                color: {token['text']};
                border: 1px solid {token['borderStrong']};
                padding: 4px 6px;
            }}
        """

    @staticmethod
    def tokens(dark):
        if dark:
            return {
                'background': '#1f2023', 'surface': '#27282c', 'raised': '#2d2f34',
                'field': '#24262a', 'hover': '#35373d', 'pressed': '#3c3f45',
                'cardHover': '#313339', 'border': '#3f4248', 'borderStrong': '#565a63',
                'text': '#f1f3f5', 'muted': '#aeb4bc', 'disabled': '#737981',
                'track': '#41444a', 'scroll': '#666b73', 'scrollHover': '#858b94',
                'success': '#69ad78', 'danger': '#d46b6b',
            }
        return {
            'background': '#f3f4f6', 'surface': '#ffffff', 'raised': '#f8f9fb',
            'field': '#ffffff', 'hover': '#eef1f4', 'pressed': '#e3e7eb',
            'cardHover': '#f3f5f7', 'border': '#d7dbe0', 'borderStrong': '#b9c0c8',
            'text': '#1f2328', 'muted': '#626a73', 'disabled': '#9aa1a9',
            'track': '#dfe3e8', 'scroll': '#aab1b8', 'scrollHover': '#858d96',
            'success': '#2f7d4a', 'danger': '#b84a4a',
        }
