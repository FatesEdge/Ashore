"""Choose a bundled icon for a download name."""

from pathlib import Path

from paths import RESOURCE_DIR


ICON_TYPES = {path.stem for path in (RESOURCE_DIR / 'static/icon/icon.ing').glob('*.png')}
ICON_ALIASES = {'jpeg': 'jpg', 'tif': 'tiff'}


def iconForFile(fileName, isTorrent=False):
    extension = Path(fileName.split('?', 1)[0]).suffix.lower().lstrip('.')
    extension = ICON_ALIASES.get(extension, extension)
    if extension in ICON_TYPES and extension not in ('paper', 'bt'):
        return extension
    return 'bt' if isTorrent else 'paper'
