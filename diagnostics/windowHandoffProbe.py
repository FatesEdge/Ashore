"""Compare direct display with Ashore's splash-to-window handoff."""

import argparse
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from Ashore import AshoreApplication
from interface.startupWindow import StartupWindow
from interface.themeManager import ThemeManager
from paths import RESOURCE_DIR


class ProbeWindow(QMainWindow):
    def __init__(self, stage):
        super().__init__()
        self.setWindowTitle(f'Ashore Handoff Probe — {stage}')
        self.setMinimumSize(1000, 520)
        if stage == 'controls':
            self.buildControls()
        else:
            self.setCentralWidget(QLabel('Empty main window'))

    def buildControls(self):
        navigation = QVBoxLayout()
        navigationGroup = QButtonGroup(self)
        navigationGroup.setExclusive(True)
        for index, name in enumerate(('Downloading', 'Completed', 'Settings')):
            button = QPushButton(name)
            button.setFlat(True)
            button.setCheckable(True)
            button.setProperty('navigationTab', True)
            button.setProperty('toolbarButton', True)
            navigationGroup.addButton(button)
            navigation.addWidget(button)
            if index == 0:
                button.setChecked(True)
        navigation.addStretch()

        toolbar = QHBoxLayout()
        for name in ('Add', 'Start', 'Pause'):
            button = QPushButton(name)
            button.setFlat(True)
            button.setProperty('toolbarButton', True)
            toolbar.addWidget(button)
        toolbar.addStretch()

        content = QVBoxLayout()
        content.addLayout(toolbar)
        content.addWidget(QLabel('Empty content area'))

        mainLayout = QHBoxLayout()
        mainLayout.addLayout(navigation)
        mainLayout.addLayout(content)
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)


class HandoffProbe(QObject):
    def __init__(self, app, stage, handoff, splashDelay):
        super().__init__(app)
        self.app = app
        self.stage = stage
        self.handoff = handoff
        self.splashDelay = splashDelay
        self.themeManager = ThemeManager(app, self)
        self.themeManager.apply('system', '#5d795f')
        self.splash = None
        self.window = None

    def start(self):
        print(
            f'Window handoff probe: stage={self.stage}, handoff={self.handoff}',
            flush=True)
        if self.handoff == 'direct':
            QTimer.singleShot(0, self.showDirect)
            return
        self.splash = StartupWindow(RESOURCE_DIR / 'static/img/cover.png')
        self.splash.firstPainted.connect(self.buildFromSplash)
        self.splash.show()

    def buildWindow(self):
        self.window = ProbeWindow(self.stage)

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
    parser.add_argument('--stage', choices=('base', 'controls'), default='controls')
    parser.add_argument('--handoff', choices=('direct', 'splash'), default='direct')
    parser.add_argument(
        '--splash-delay', dest='splashDelay', type=int, default=900,
        help='milliseconds between splash paint and main-window handoff')
    return parser


def main(arguments=None):
    options = buildParser().parse_args(
        sys.argv[1:] if arguments is None else arguments)
    app = AshoreApplication([sys.argv[0]])
    probe = HandoffProbe(
        app, options.stage, options.handoff, max(0, options.splashDelay))
    app.handoffProbe = probe
    probe.start()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
