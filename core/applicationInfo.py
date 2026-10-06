"""Ashore application identity."""

APP_VERSION = '1.0.0'
APP_AUTHOR = 'PanZK'
PROJECT_URL = 'https://github.com/Kai-x64/Ashore'


def configureApplication():
    """Set the desktop identity before Qt initializes its platform plugin."""
    from PyQt6.QtWidgets import QApplication

    QApplication.setApplicationVersion(APP_VERSION)
    QApplication.setOrganizationName(APP_AUTHOR)
    QApplication.setApplicationName('Ashore')
    QApplication.setDesktopFileName('ashore')
