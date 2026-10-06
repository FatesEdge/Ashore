"""Create Ashore's cross-platform client-side window chrome."""

from .base import WindowChrome


def createWindowChrome(window):
    return WindowChrome(window)
