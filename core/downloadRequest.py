"""Validated download-request model shared by UI and RPC layers."""

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from urllib.request import url2pathname

NETWORK_SCHEMES = {'http', 'https', 'ftp'}
ITEM_NETWORK = 'network'
ITEM_REMOTE_TORRENT = 'remote-torrent'
ITEM_MAGNET = 'magnet'
ITEM_LOCAL_TORRENT = 'local-torrent'


@dataclass(frozen=True)
class DownloadItem:
    source: str
    kind: str

    @property
    def isTorrent(self):
        return self.kind in {
            ITEM_REMOTE_TORRENT, ITEM_MAGNET, ITEM_LOCAL_TORRENT}

    @property
    def supportsHttpOptions(self):
        return self.kind in {ITEM_NETWORK, ITEM_REMOTE_TORRENT}

    @property
    def supportsOutputName(self):
        return self.kind == ITEM_NETWORK


@dataclass(frozen=True)
class ParsedDownloadInputs:
    items: tuple[DownloadItem, ...] = ()
    invalid: tuple[str, ...] = ()

    @property
    def validCount(self):
        return len(self.items)


@dataclass
class DownloadRequest:
    items: tuple[DownloadItem, ...]
    targetDir: str
    options: dict = field(default_factory=dict)


def splitRawInputs(rawInputs):
    if rawInputs is None:
        return []
    if isinstance(rawInputs, str):
        rawInputs = [rawInputs]
    lines = []
    for value in rawInputs:
        lines.extend(
            line.strip()
            for line in str(value).splitlines()
            if line.strip())
    return lines


def expandAshoreUri(value):
    parsed = urlsplit(value)
    if parsed.scheme.lower() != 'ashore':
        return None
    endpoint = (parsed.netloc or parsed.path.strip('/')).lower()
    if endpoint != 'add':
        return []
    return [
        item.strip()
        for item in parse_qs(parsed.query).get('url', [])
        if item.strip()
    ]


def classifyInput(value):
    localPath = Path(value).expanduser()
    try:
        if localPath.is_file() and localPath.suffix.lower() == '.torrent':
            return DownloadItem(str(localPath.resolve()), ITEM_LOCAL_TORRENT)
    except OSError:
        pass

    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()

    if scheme == 'file':
        path = Path(url2pathname(unquote(parsed.path)))
        if path.is_file() and path.suffix.lower() == '.torrent':
            return DownloadItem(str(path), ITEM_LOCAL_TORRENT)
        return None

    if scheme == 'magnet':
        if 'xt=urn:btih:' in parsed.query.lower():
            return DownloadItem(value, ITEM_MAGNET)
        return None

    if scheme in NETWORK_SCHEMES and parsed.netloc:
        kind = (
            ITEM_REMOTE_TORRENT
            if unquote(parsed.path).lower().endswith('.torrent')
            else ITEM_NETWORK)
        return DownloadItem(value, kind)

    return None




def outputNameForItem(item, options=None):
    """Return the predictable output filename for a normal network download."""
    if item.kind != ITEM_NETWORK:
        return ''
    configured = str((options or {}).get('out') or '').strip()
    if configured:
        return Path(configured).name
    return Path(unquote(urlsplit(item.source).path)).name


def existingOutputConflict(item, targetDir, options=None):
    """Return an existing payload path that has no aria2 resume control file."""
    name = outputNameForItem(item, options)
    if not name:
        return None
    path = Path(targetDir).expanduser() / name
    sidecar = Path(str(path) + '.aria2')
    return path if path.is_file() and not sidecar.exists() else None


def nextAvailableOutputName(path):
    """Choose a numbered sibling filename without overwriting an existing file."""
    path = Path(path)
    suffix = ''.join(path.suffixes)
    stem = path.name[:-len(suffix)] if suffix else path.name
    index = 1
    while True:
        candidate = path.with_name(f'{stem}.{index}{suffix}')
        if not candidate.exists() and not Path(str(candidate) + '.aria2').exists():
            return candidate.name
        index += 1

def parseDownloadInputs(rawInputs):
    items = []
    invalid = []
    seen = set()

    for raw in splitRawInputs(rawInputs):
        expanded = expandAshoreUri(raw)
        candidates = expanded if expanded is not None else [raw]
        if expanded == []:
            invalid.append(raw)
            continue

        for candidate in candidates:
            if urlsplit(candidate).scheme.lower() == 'ashore':
                invalid.append(candidate)
                continue
            item = classifyInput(candidate)
            if item is None:
                invalid.append(candidate)
                continue
            key = (item.kind, item.source)
            if key not in seen:
                items.append(item)
                seen.add(key)

    return ParsedDownloadInputs(tuple(items), tuple(invalid))
