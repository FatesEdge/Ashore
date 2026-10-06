"""Linux native window chrome."""

from .base import NativeWindowChrome


class LinuxWindowChrome(NativeWindowChrome):
    platformName = 'linux'
