"""Small, atomic helpers for Ashore and aria2 configuration files."""

import configparser
import os
import tempfile
from pathlib import Path


def readOptions(path):
    """Read an aria2-style ``key=value`` file without interpreting comments."""
    options = {}
    try:
        lines = Path(path).read_text(encoding='utf-8').splitlines()
    except OSError:
        return options
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', ';', '[')) or '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        options[key.strip()] = os.path.expandvars(value.strip())
    return options


def writeOptions(path, values, removeKeys=()):
    """Atomically update selected aria2 options while preserving comments."""
    path = Path(path)
    remaining = {str(key): str(value) for key, value in values.items()}
    removeKeys = set(removeKeys)
    lines = []
    try:
        for line in path.read_text(encoding='utf-8').splitlines(keepends=True):
            stripped = line.strip()
            key = stripped.split('=', 1)[0].strip() if '=' in stripped else ''
            if key in removeKeys:
                continue
            if key in remaining:
                lines.append(f'{key}={remaining.pop(key)}\n')
            else:
                lines.append(line)
        lines.extend(f'{key}={value}\n' for key, value in remaining.items())
        atomicWrite(path, ''.join(lines))
    except OSError:
        return False
    return True


def readAshore(path, defaultsPath=None):
    """Return the merged ``[global]`` Ashore configuration."""
    parser = configparser.ConfigParser()
    files = [str(item) for item in (defaultsPath, path) if item]
    parser.read(files, encoding='utf-8')
    return dict(parser['global']) if parser.has_section('global') else {}


def writeAshore(path, values):
    """Atomically update Ashore's ``[global]`` section."""
    path = Path(path)
    parser = configparser.ConfigParser()
    parser.read(path, encoding='utf-8')
    if not parser.has_section('global'):
        parser.add_section('global')
    for key, value in values.items():
        parser.set('global', str(key), boolText(value) if isinstance(value, bool) else str(value))
    try:
        with tempfile.NamedTemporaryFile(
                'w', encoding='utf-8', dir=path.parent, delete=False) as file:
            parser.write(file)
            temporary = Path(file.name)
        temporary.replace(path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except (OSError, UnboundLocalError):
            pass
        return False
    return True


def atomicWrite(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
            'w', encoding='utf-8', dir=path.parent, delete=False) as file:
        file.write(content)
        temporary = Path(file.name)
    temporary.replace(path)


def boolValue(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() == 'true'


def boolText(value):
    return 'true' if boolValue(value) else 'false'
