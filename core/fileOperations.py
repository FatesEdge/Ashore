"""Local file deletion and platform file-manager integration."""

import os
import platform
import shutil
import subprocess
from pathlib import Path


def taskPaths(mission):
    """Return validated task payload paths rooted inside the download directory."""
    root = Path(mission['dir']).resolve()
    if not root.is_dir():
        raise ValueError('The download directory does not exist; no files were deleted')

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
            raise ValueError('Task file is outside the download directory; refusing to delete')
        targets.append(candidate)

    if not targets:
        raise ValueError('Task files could not be determined; refusing to delete')
    return root, targets


def deleteTaskSidecars(mission):
    """Delete aria2 control files while preserving downloaded payload files."""
    root, targets = taskPaths(mission)
    candidates = {Path(str(path) + '.aria2') for path in targets}

    filename = str(mission.get('filename') or '').strip()
    if filename:
        topLevel = root / filename
        if topLevel.resolve().is_relative_to(root) and topLevel.resolve() != root:
            candidates.add(Path(str(topLevel) + '.aria2'))

    for sidecar in candidates:
        if sidecar.is_file() and not sidecar.is_symlink():
            sidecar.unlink()


def deleteTaskFiles(mission):
    root, targets = taskPaths(mission)
    deleteTaskSidecars(mission)

    for path in targets:
        if path.is_file() and not path.is_symlink():
            path.unlink()
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
