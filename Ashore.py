"""Ashore desktop application entry point."""

import platform
import signal
import sys

from PyQt6.QtCore import QCoreApplication, QEvent, QTimer
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
            resourcePath + 'static/icon/functionIcons/appIcon.icns'))
    else:
        app.setWindowIcon(QIcon(
            resourcePath + 'static/icon/functionIcons/appIcon.png'))

    app.startupController = StartupController(app, sys.argv, Ashore)
    app.startupController.start()

    signal.signal(signal.SIGINT, lambda *_: app.startupController.quit())
    signalTimer = QTimer()
    signalTimer.timeout.connect(lambda: None)
    signalTimer.start(250)

    exitCode = app.exec()

    signalTimer.stop()
    controller = app.startupController
    controller.dispose()
    app.startupController = None
    controller.deleteLater()
    QCoreApplication.sendPostedEvents(
        None, QEvent.Type.DeferredDelete)
    app.processEvents()
    return exitCode


if __name__ == '__main__':
    sys.exit(main())
