"""Locations shared by the source checkout and frozen application."""

import os
from pathlib import Path
import secrets
import sys


RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ashore"


def ensure_config(name):
    """Install a bundled default once, preserving the user's existing settings."""
    target = CONFIG_DIR / name
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        source = RESOURCE_DIR / "config" / name
        content = source.read_bytes()
        if name == 'aria2.conf':
            content = content.replace(b'${HOME}/.config/ashore', os.fsencode(CONFIG_DIR))
        target.write_bytes(content)
    if name == 'aria2.conf':
        content = target.read_text(encoding='utf-8')
        enabled = any(line.strip() == 'rpc-listen-all=true' for line in content.splitlines())
        secret = any(line.strip().startswith('rpc-secret=') for line in content.splitlines())
        if enabled and not secret:
            with target.open('a', encoding='utf-8') as file:
                file.write('\nrpc-secret=' + secrets.token_urlsafe(32) + '\n')
        target.chmod(0o600)
    return target
