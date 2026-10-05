"""Locations shared by the source checkout and frozen application."""

import os
import sys
from pathlib import Path

from core.configStore import readOptions, writeOptions

RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ashore"


def systemDownloadDirectory():
    """Return the desktop environment's download directory without creating it."""
    try:
        from PyQt6.QtCore import QStandardPaths

        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation)
    except (ImportError, RuntimeError):
        location = ''
    return Path(location).expanduser() if location else Path.home()


def legacyDownloadDirectoryMigration(configPath):
    """Return a safe legacy-default migration, or ``None`` for custom paths."""
    try:
        lines = Path(configPath).read_text(encoding='utf-8').splitlines()
    except OSError:
        return None
    rawValue = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', ';')) or '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        if key.strip() == 'dir':
            rawValue = value.strip()
    legacyValues = {'${HOME}/Downloads', '~/Downloads', str(Path.home() / 'Downloads')}
    if rawValue not in legacyValues:
        return None
    oldPath = Path(os.path.expandvars(rawValue)).expanduser()
    newPath = systemDownloadDirectory()
    if oldPath == newPath:
        return None
    return oldPath, newPath


def ensureConfig(name):
    """Install a bundled default once, preserving the user's existing settings."""
    target = CONFIG_DIR / name
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        source = RESOURCE_DIR / "config" / name
        content = source.read_bytes()
        if name == 'aria2.conf':
            content = content.replace(b'${HOME}/.config/ashore', os.fsencode(CONFIG_DIR))
            content = content.replace(b'${DOWNLOAD_DIR}', os.fsencode(systemDownloadDirectory()))
        target.write_bytes(content)
    if name == 'aria2.conf':
        options = readOptions(target)
        if ('check-integrity' not in options
                and not writeOptions(target, {'check-integrity': 'true'})):
            raise OSError(f'无法更新 aria2 配置：{target}')
        target.chmod(0o600)
    return target
