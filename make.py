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


def build(kind):
    system = platform.system()
    supported = {'Linux': ('onefile', 'onedir'), 'Darwin': ('app', 'dmg')}
    if kind not in supported.get(system, ()):
        raise ValueError(f'{system} 不支持 {kind} 打包')
    target = DIST / f'Ashore.{system}.{kind}'
    DIST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f'.Ashore.{system}.{kind}.', dir=DIST) as directory:
        staging = Path(directory) / 'package'
        staging.mkdir()
        command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                   '--name', 'Ashore', '--windowed',
                   '--onedir' if system == 'Darwin' or kind == 'onedir' else '--onefile',
                   '--distpath', str(staging), '--workpath', str(ROOT / 'build' / f'{system}.{kind}'),
                   '--specpath', str(ROOT / 'build' / f'{system}.{kind}'),
                   '--add-data', f'{ROOT / "static"}{os.pathsep}static',
                   '--add-data', f'{ROOT / "config"}{os.pathsep}config', str(ROOT / 'Ashore.py')]
        subprocess.run(command, cwd=ROOT, check=True)
        if system == 'Linux':
            program = staging / 'Ashore'
            executable = program / 'Ashore' if kind == 'onedir' else program
            if not executable.is_file():
                raise ValueError('PyInstaller 未生成完整的 Ashore Linux 安装包')
            for source, name in [(ROOT / 'static/icon/functionIcons/icon0.png', 'icon.png'),
                                 (ROOT / 'bale/ashore.desktop', 'ashore.desktop'),
                                 (ROOT / 'bale/install.sh', 'install.sh')]:
                shutil.copy2(source, staging / name)
            (staging / 'install.sh').chmod(0o755)
        else:
            app = staging / 'Ashore.app'
            plist = app / 'Contents/Info.plist'
            with plist.open('rb') as file:
                info = plistlib.load(file)
            with (ROOT / 'bale/Info.plist').open('rb') as file:
                template = plistlib.load(file)
            for key in ('CFBundleURLTypes', 'CFBundleDocumentTypes'):
                info[key] = template[key]
            info['CFBundleShortVersionString'] = APP_VERSION
            info['CFBundleVersion'] = APP_VERSION
            info['CFBundleIconFile'] = 'icon.icns'
            with plist.open('wb') as file:
                plistlib.dump(info, file)
            shutil.copy2(ROOT / 'static/icon/functionIcons/icon.icns', app / 'Contents/Resources/icon.icns')
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
    print(f'打包完成：{target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='构建 Ashore 发布包')
    parser.add_argument('kind', choices=('onefile', 'onedir', 'app', 'dmg'))
    arguments = parser.parse_args()
    try:
        build(arguments.kind)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'打包失败：{exc}\n')
