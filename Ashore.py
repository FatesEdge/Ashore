"""Ashore desktop application entry point."""

import platform
import signal
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont, QIcon

from core.applicationRuntime import AshoreApplication, StartupController
from interface.mainWindow import Ashore
from paths import RESOURCE_DIR


def main():
    resourcePath = str(RESOURCE_DIR) + '/'
    app = AshoreApplication(sys.argv)

    if platform.system() == 'Darwin':
        app.setFont(QFont('Hiragino Sans GB'))
        app.setWindowIcon(QIcon(
            resourcePath + 'static/icon/functionIcons/icon.icns'))
    else:
        app.setWindowIcon(QIcon(
            resourcePath + 'static/icon/functionIcons/icon0.png'))

    app.startupController = StartupController(app, sys.argv, Ashore)
    app.startupController.start()

    signal.signal(signal.SIGINT, lambda *_: app.startupController.quit())
    signalTimer = QTimer()
    signalTimer.timeout.connect(lambda: None)
    signalTimer.start(250)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
