"""Windows native window chrome."""

from .base import NativeWindowChrome


class WindowsWindowChrome(NativeWindowChrome):
    platformName = 'windows'
