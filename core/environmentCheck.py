"""Operating-system-aware aria2 startup guidance."""

from dataclasses import dataclass
import platform
from pathlib import Path
import shutil


@dataclass(frozen=True)
class EnvironmentIssue:
    code: str
    systemName: str
    detail: str
    installCommand: str


def _linuxRelease():
    values = {}
    try:
        for rawLine in Path('/etc/os-release').read_text(
                encoding='utf-8').splitlines():
            if '=' not in rawLine:
                continue
            key, value = rawLine.split('=', 1)
            values[key] = value.strip().strip('"')
    except OSError:
        pass
    return values


def currentSystem():
    system = platform.system()
    if system == 'Linux':
        release = _linuxRelease()
        pretty = release.get('PRETTY_NAME')
        if pretty:
            return pretty
        return 'Linux'
    if system == 'Darwin':
        version = platform.mac_ver()[0]
        return f'macOS {version}'.strip()
    if system == 'Windows':
        release = platform.release()
        return f'Windows {release}'.strip()
    return system or 'Unknown system'


def recommendedAria2Install():
    system = platform.system()
    if system == 'Darwin':
        return 'brew install aria2'
    if system == 'Windows':
        return 'winget install aria2.aria2'
    if system == 'Linux':
        managers = (
            ('apt', 'sudo apt install aria2'),
            ('dnf', 'sudo dnf install aria2'),
            ('pacman', 'sudo pacman -S aria2'),
            ('zypper', 'sudo zypper install aria2'),
            ('apk', 'sudo apk add aria2'),
        )
        for executable, command in managers:
            if shutil.which(executable):
                return command

        release = _linuxRelease()
        distro = ' '.join((
            release.get('ID', ''),
            release.get('ID_LIKE', ''),
        )).lower()
        if any(name in distro for name in ('debian', 'ubuntu')):
            return 'sudo apt install aria2'
        if any(name in distro for name in ('fedora', 'rhel', 'centos')):
            return 'sudo dnf install aria2'
        if 'arch' in distro:
            return 'sudo pacman -S aria2'
        if any(name in distro for name in ('suse', 'opensuse')):
            return 'sudo zypper install aria2'
        if 'alpine' in distro:
            return 'sudo apk add aria2'
        return 'aria2c --version'
    return 'aria2c --version'


def makeEnvironmentIssue(code, detail=''):
    return EnvironmentIssue(
        code=code,
        systemName=currentSystem(),
        detail=detail,
        installCommand=recommendedAria2Install(),
    )
