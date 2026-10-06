"""Local file deletion and platform file-manager integration."""

import os
import platform
import shutil
import subprocess
from pathlib import Path


def deleteTaskFiles(mission):
    root = Path(mission['dir']).resolve()
    if not root.is_dir():
        raise ValueError('下载目录不存在，未删除任何文件')

    files = mission.get('files') or [str(root / mission['filename'])]
    targets = []
    for name in files:
        if not name:
            continue
        candidate = Path(name)
        if not candidate.is_absolute():
            candidate = root / candidate
        resolved = candidate.resolve()
        if (candidate.is_symlink()
                or not resolved.is_relative_to(root)
                or resolved == root):
            raise ValueError('任务文件超出下载目录，拒绝删除')
        targets.append(candidate)

    if not targets:
        raise ValueError('无法确定任务文件，拒绝删除')

    for path in targets:
        for item in (path, Path(str(path) + '.aria2')):
            if item.is_file() and not item.is_symlink():
                item.unlink()
        parent = path.parent
        while parent != root and parent.is_relative_to(root):
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def revealDownloadedFile(mission):
    directory = mission.get('dir', '')
    filePath = str(Path(directory) / mission.get('filename', ''))
    system = platform.system()

    if system == 'Darwin':
        command = ['open', '-R', filePath]
    elif system == 'Linux':
        if not shutil.which('nautilus') or not os.path.exists(filePath):
            return {'dir': directory}
        command = ['nautilus', '--select', filePath]
    elif system == 'Windows':
        command = ['explorer', '/select,', filePath]
    else:
        return {'dir': directory}

    try:
        subprocess.Popen(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return {'dir': directory}
    return {}
