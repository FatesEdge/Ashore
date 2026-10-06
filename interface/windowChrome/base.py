"""Platform window chrome contract."""

from PyQt6.QtCore import Qt


class NativeWindowChrome:
    """Use the platform's native window decoration and window manager behaviour."""

    platformName = 'generic'
    usesNativeDecoration = True

    def __init__(self, window):
        self.window = window

    def install(self):
        flags = self.window.windowFlags()
        if flags & Qt.WindowType.FramelessWindowHint:
            self.window.setWindowFlags(
                flags & ~Qt.WindowType.FramelessWindowHint)
        self.window.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, False)
