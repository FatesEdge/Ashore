#!/usr/bin/env python3
"""Build Ashore distributions from any working directory."""

import argparse
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from core.applicationInfo import APP_VERSION

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'

PYINSTALLER_EXCLUDES = (
    'cryptography',
    'matplotlib',
    'numpy',
    'pandas',
    'PIL',
    'scipy',
    'tkinter',
    'PyQt6.QtBluetooth',
    'PyQt6.QtDBus',
    'PyQt6.QtDesigner',
    'PyQt6.QtHelp',
    'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets',
    'PyQt6.QtNfc',
    'PyQt6.QtPdf',
    'PyQt6.QtPdfWidgets',
    'PyQt6.QtPositioning',
    'PyQt6.QtQml',
    'PyQt6.QtQuick',
    'PyQt6.QtQuickWidgets',
    'PyQt6.QtRemoteObjects',
    'PyQt6.QtSensors',
    'PyQt6.QtSerialPort',
    'PyQt6.QtSpatialAudio',
    'PyQt6.QtSql',
    'PyQt6.QtTest',
    'PyQt6.QtWebChannel',
    'PyQt6.QtWebEngineCore',
    'PyQt6.QtWebEngineWidgets',
)


def pyinstallerCommand(system, kind, staging):
    command = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm', '--clean',
        '--name', 'Ashore',
        '--windowed',
        '--onedir' if system == 'Darwin' or kind == 'onedir' else '--onefile',
        '--distpath', str(staging),
        '--workpath', str(ROOT / 'build' / f'{system}.{kind}'),
        '--specpath', str(ROOT / 'build' / f'{system}.{kind}'),
        '--add-data', f'{ROOT / "static"}{os.pathsep}static',
        '--add-data', f'{ROOT / "config"}{os.pathsep}config',
    ]
    if system == 'Linux':
        command.append('--strip')
    for module in PYINSTALLER_EXCLUDES:
        command.extend(('--exclude-module', module))
    command.append(str(ROOT / 'Ashore.py'))
    return command


def directorySize(path):
    return sum(
        file.stat().st_size
        for file in Path(path).rglob('*')
        if file.is_file())


def printPackageSize(target):
    target = Path(target)
    if not target.exists():
        return
    if target.is_file():
        size = target.stat().st_size
    else:
        size = directorySize(target)
    print(f'Package size: {size / (1024 * 1024):.1f} MiB')


def build(kind):
    system = platform.system()
    supported = {'Linux': ('onefile', 'onedir'), 'Darwin': ('app', 'dmg')}
    if kind not in supported.get(system, ()):
        raise ValueError(f'{system} does not support {kind} packaging')
    target = DIST / f'Ashore.{system}.{kind}'
    DIST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f'.Ashore.{system}.{kind}.', dir=DIST) as directory:
        staging = Path(directory) / 'package'
        staging.mkdir()
        command = pyinstallerCommand(system, kind, staging)
        subprocess.run(command, cwd=ROOT, check=True)
        if system == 'Linux':
            program = staging / 'Ashore'
            executable = program / 'Ashore' if kind == 'onedir' else program
            if not executable.is_file():
                raise ValueError('PyInstaller did not produce a complete Ashore Linux package')
            for source, name in [(ROOT / 'static/icon/functionIcons/appIcon.png', 'icon.png'),
                                 (ROOT / 'packaging/ashore.desktop', 'ashore.desktop'),
                                 (ROOT / 'packaging/install.sh', 'install.sh')]:
                shutil.copy2(source, staging / name)
            (staging / 'install.sh').chmod(0o755)
        else:
            app = staging / 'Ashore.app'
            plist = app / 'Contents/Info.plist'
            with plist.open('rb') as file:
                info = plistlib.load(file)
            with (ROOT / 'packaging/Info.plist').open('rb') as file:
                template = plistlib.load(file)
            for key in ('CFBundleURLTypes', 'CFBundleDocumentTypes'):
                info[key] = template[key]
            info['CFBundleShortVersionString'] = APP_VERSION
            info['CFBundleVersion'] = APP_VERSION
            info['CFBundleIconFile'] = 'icon.icns'
            with plist.open('wb') as file:
                plistlib.dump(info, file)
            shutil.copy2(ROOT / 'static/icon/functionIcons/appIcon.icns', app / 'Contents/Resources/icon.icns')
            if kind == 'dmg':
                dmg_stage = Path(directory) / 'dmg-stage'
                dmg_stage.mkdir()
                shutil.copytree(app, dmg_stage / 'Ashore.app')
                (dmg_stage / 'Applications').symlink_to('/Applications')
                subprocess.run(['hdiutil', 'create', '-volname', 'Ashore', '-srcfolder', str(dmg_stage),
                                '-format', 'UDZO', str(staging / 'Ashore.dmg')], check=True)
        previous = Path(directory) / 'previous'
        if target.exists():
            target.rename(previous)
        try:
            staging.rename(target)
        except OSError:
            if previous.exists():
                previous.rename(target)
            raise
    printPackageSize(target)
    print(f'Build complete: {target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build Ashore release packages')
    parser.add_argument('kind', choices=('onefile', 'onedir', 'app', 'dmg'))
    arguments = parser.parse_args()
    try:
        build(arguments.kind)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Packaging failed: {exc}\n')
