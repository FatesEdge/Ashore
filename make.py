#!/usr/bin/env python3
"""Build Ashore distributions from any working directory."""

import argparse
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'


def build(kind):
    system = platform.system()
    supported = {'Linux': ('onefile', 'onedir'), 'Darwin': ('app', 'dmg')}
    if kind not in supported.get(system, ()):
        raise ValueError(f'{system} 不支持 {kind} 打包')
    target = DIST / f'Ashore.{system}.{kind}'
    target.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
               '--name', 'Ashore', '--windowed',
               '--onedir' if system == 'Darwin' or kind == 'onedir' else '--onefile',
               '--distpath', str(target), '--workpath', str(ROOT / 'build' / f'{system}.{kind}'),
               '--specpath', str(ROOT / 'build' / f'{system}.{kind}'),
               '--add-data', f'{ROOT / "static"}{os.pathsep}static',
               '--add-data', f'{ROOT / "config"}{os.pathsep}config', str(ROOT / 'Ashore.py')]
    subprocess.run(command, cwd=ROOT, check=True)
    if system == 'Linux':
        for source, name in [(ROOT / 'static/icon/icon.funtion/icon0.png', 'icon.png'),
                             (ROOT / 'bale/ashore.desktop', 'ashore.desktop'),
                             (ROOT / 'bale/install.sh', 'install.sh')]:
            shutil.copy2(source, target / name)
        (target / 'install.sh').chmod(0o755)
    else:
        app = target / 'Ashore.app'
        plist = app / 'Contents/Info.plist'
        with plist.open('rb') as file:
            info = plistlib.load(file)
        with (ROOT / 'bale/Info.plist').open('rb') as file:
            template = plistlib.load(file)
        for key in ('CFBundleURLTypes', 'CFBundleDocumentTypes'):
            info[key] = template[key]
        info['CFBundleIconFile'] = 'icon.icns'
        with plist.open('wb') as file:
            plistlib.dump(info, file)
        shutil.copy2(ROOT / 'static/icon/icon.funtion/icon.icns', app / 'Contents/Resources/icon.icns')
        if kind == 'dmg':
            stage = target / 'dmg-stage'
            stage.mkdir(exist_ok=True)
            shutil.copytree(app, stage / 'Ashore.app', dirs_exist_ok=True)
            (stage / 'Applications').symlink_to('/Applications')
            subprocess.run(['hdiutil', 'create', '-volname', 'Ashore', '-srcfolder', str(stage),
                            '-format', 'UDZO', str(target / 'Ashore.dmg')], check=True)
            shutil.rmtree(stage)
    print(f'打包完成：{target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='构建 Ashore 发布包')
    parser.add_argument('kind', choices=('onefile', 'onedir', 'app', 'dmg'))
    arguments = parser.parse_args()
    try:
        build(arguments.kind)
    except (ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'打包失败：{exc}\n')
