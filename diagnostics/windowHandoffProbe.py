"""Compare direct display with Ashore's splash-to-window handoff."""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QSize, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from Ashore import AshoreApplication
from interface.page import Page
from interface.settingPage import SettingPage
from interface.startupWindow import StartupWindow
from interface.themeManager import ThemeManager
from paths import RESOURCE_DIR


@dataclass(frozen=True)
class WindowStage:
    name: str
    description: str


WINDOW_STAGES = (
    WindowStage('base', 'empty QMainWindow'),
    WindowStage('controls', 'navigation and toolbar without icons'),
    WindowStage('icons', 'add production navigation and toolbar icons'),
    WindowStage('stackEmpty', 'add an empty stacked layout'),
    WindowStage('stackOne', 'add one blank page to the stack'),
    WindowStage('stackTwo', 'add two blank pages to the stack'),
    WindowStage('stack', 'add three blank pages to the stack'),
    WindowStage('scrollAreas', 'replace two blank pages with scroll areas'),
    WindowStage('firstPage', 'replace the first scroll area with Page'),
    WindowStage('pages', 'add two production download pages'),
    WindowStage('settings', 'add the production settings page'),
)


def stageIndex(name):
    return next(index for index, stage in enumerate(WINDOW_STAGES)
                if stage.name == name)


def includes(selected, required):
    return stageIndex(selected) >= stageIndex(required)


class ProbeWindow(QMainWindow):
    def __init__(self, stage, stackKind):
        super().__init__()
        self.stage = stage
        self.stackKind = stackKind
        self.setWindowTitle(f'Ashore Handoff Probe — {stage}')
        self.setMinimumSize(1000, 520)
        if includes(stage, 'controls'):
            self.buildControls()
        else:
            self.setCentralWidget(QLabel('Empty main window'))

    def buildControls(self):
        navigation = QVBoxLayout()
        navigationGroup = QButtonGroup(self)
        navigationGroup.setExclusive(True)
        navigationItems = (
            ('Downloading', 'download.png'),
            ('Completed', 'completed.png'),
            ('Settings', 'setting.png'),
        )
        for index, (name, iconName) in enumerate(navigationItems):
            icon = self.controlIcon(iconName)
            button = QPushButton(icon, name)
            button.setFlat(True)
            button.setIconSize(QSize(23, 23))
            button.setCheckable(True)
            button.setProperty('navigationTab', True)
            button.setProperty('toolbarButton', True)
            navigationGroup.addButton(button)
            navigation.addWidget(button)
            if index == 0:
                button.setChecked(True)
        navigation.addStretch()

        toolbar = QHBoxLayout()
        toolbarItems = (
            ('Add', 'add.png'),
            ('Start', 'play.png'),
            ('Pause', 'pause.png'),
        )
        for name, iconName in toolbarItems:
            button = QPushButton(self.controlIcon(iconName), name)
            button.setFlat(True)
            button.setIconSize(QSize(20, 20))
            button.setProperty('toolbarButton', True)
            toolbar.addWidget(button)
        toolbar.addStretch()

        content = QVBoxLayout()
        content.addLayout(toolbar)
        if includes(self.stage, 'stackEmpty'):
            pages = []
            if includes(self.stage, 'stackOne'):
                pages.append(self.downloadPage(True))
            if includes(self.stage, 'stackTwo'):
                pages.append(self.downloadPage(False))
            if includes(self.stage, 'stack'):
                if includes(self.stage, 'settings'):
                    pages.append(SettingPage())
                else:
                    pages.append(QWidget())
            self.addPages(content, pages)
        else:
            content.addWidget(QLabel('Empty content area'))

        mainLayout = QHBoxLayout()
        mainLayout.addLayout(navigation)
        mainLayout.addLayout(content)
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)

    def addPages(self, content, pages):
        if self.stackKind == 'widget':
            stack = QStackedWidget()
            for page in pages:
                stack.addWidget(page)
            content.addWidget(stack)
            return
        if self.stackKind == 'vertical':
            layout = QVBoxLayout()
            for page in pages:
                layout.addWidget(page)
            content.addLayout(layout)
            return
        stack = QStackedLayout()
        for page in pages:
            stack.addWidget(page)
        content.addLayout(stack)

    def downloadPage(self, first):
        if includes(self.stage, 'pages'):
            return Page()
        if first and includes(self.stage, 'firstPage'):
            return Page()
        if includes(self.stage, 'scrollAreas'):
            area = QScrollArea()
            area.setWidgetResizable(True)
            page = QWidget()
            page.setLayout(QVBoxLayout())
            area.setWidget(page)
            return area
        return QWidget()

    def controlIcon(self, name):
        if not includes(self.stage, 'icons'):
            return QIcon()
        return QIcon(str(RESOURCE_DIR / 'static/icon/functionIcons' / name))


class HandoffProbe(QObject):
    def __init__(self, app, stage, handoff, splashDelay, stackKind):
        super().__init__(app)
        self.app = app
        self.stage = stage
        self.handoff = handoff
        self.splashDelay = splashDelay
        self.stackKind = stackKind
        self.themeManager = ThemeManager(app, self)
        self.themeManager.apply('system', '#5d795f')
        self.splash = None
        self.window = None

    def start(self):
        print(
            f'Window handoff probe: stage={self.stage}, handoff={self.handoff}, '
            f'stack={self.stackKind}',
            flush=True)
        if self.handoff == 'direct':
            QTimer.singleShot(0, self.showDirect)
            return
        self.splash = StartupWindow(RESOURCE_DIR / 'static/img/cover.png')
        self.splash.firstPainted.connect(self.buildFromSplash)
        self.splash.show()

    def buildWindow(self):
        self.window = ProbeWindow(self.stage, self.stackKind)

    def showDirect(self):
        self.buildWindow()
        self.window.show()
        print('Main window shown directly', flush=True)

    def buildFromSplash(self):
        print('Splash first paint completed', flush=True)
        self.buildWindow()
        QTimer.singleShot(self.splashDelay, self.finishSplash)

    def finishSplash(self):
        self.splash.finish(self.window)
        print('Splash handed off to main window', flush=True)


def buildParser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--stage', choices=[stage.name for stage in WINDOW_STAGES],
        default='controls')
    parser.add_argument('--handoff', choices=('direct', 'splash'), default='direct')
    parser.add_argument(
        '--stack-kind', dest='stackKind',
        choices=('layout', 'widget', 'vertical'), default='layout',
        help='container used for the page tiers')
    parser.add_argument(
        '--splash-delay', dest='splashDelay', type=int, default=900,
        help='milliseconds between splash paint and main-window handoff')
    return parser


def main(arguments=None):
    options = buildParser().parse_args(
        sys.argv[1:] if arguments is None else arguments)
    app = AshoreApplication([sys.argv[0]])
    probe = HandoffProbe(
        app, options.stage, options.handoff, max(0, options.splashDelay),
        options.stackKind)
    app.handoffProbe = probe
    probe.start()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
