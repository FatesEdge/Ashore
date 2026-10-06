"""Ashore application identity."""

APP_VERSION = '0.7.89'
APP_AUTHOR = 'PanZK'
PROJECT_URL = 'https://github.com/FatesEdge/Ashore'


def configureApplication():
    """Set the desktop identity before Qt initializes its platform plugin."""
    from PyQt6.QtWidgets import QApplication

    QApplication.setApplicationVersion(APP_VERSION)
    QApplication.setOrganizationName(APP_AUTHOR)
    QApplication.setApplicationName('Ashore')
    QApplication.setDesktopFileName('ashore')
