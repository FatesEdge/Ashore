"""macOS native window chrome."""

from .base import NativeWindowChrome


class MacOSWindowChrome(NativeWindowChrome):
    platformName = 'macos'
