"""Select the platform window chrome implementation."""

import sys

from .base import NativeWindowChrome
from .linux import LinuxWindowChrome
from .macos import MacOSWindowChrome
from .windows import WindowsWindowChrome


def createWindowChrome(window):
    if sys.platform.startswith('linux'):
        return LinuxWindowChrome(window)
    if sys.platform == 'darwin':
        return MacOSWindowChrome(window)
    if sys.platform.startswith('win'):
        return WindowsWindowChrome(window)
    return NativeWindowChrome(window)
