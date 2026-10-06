"""Named BitTorrent tracker-list sources and merge helpers."""

import time
import urllib.parse
import urllib.request

TRACKER_SOURCE_CATALOG = (
    {
        'key': 'ngosang',
        'name': 'ngosang / trackerslist',
        'url': 'https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best_ip.txt',
    },
    {
        'key': 'xiu2',
        'name': 'XIU2 / TrackersListCollection',
        'url': 'https://cdn.jsdelivr.net/gh/XIU2/TrackersListCollection/best_aria2.txt',
    },
    {
        'key': 'trackerslist',
        'name': 'TrackersList.com',
        'url': 'https://trackerslist.com/best_aria2.txt',
    },
)
DEFAULT_SOURCE_KEYS = ('ngosang', 'xiu2')


def parseTrackers(text):
    """Accept newline or comma separated announce URLs, without duplicates."""
    trackers = []
    seen = set()
    for value in text.replace(',', '\n').splitlines():
        url = value.strip()
        try:
            parsed = urllib.parse.urlsplit(url)
        except ValueError:
            continue
        if (parsed.scheme in ('udp', 'http', 'https') and parsed.netloc
                and not any(char.isspace() for char in url) and url not in seen):
            trackers.append(url)
            seen.add(url)
    return trackers


def validSourceUrl(value):
    """Return a normalized HTTP(S) list URL, or an empty string."""
    url = str(value or '').strip()
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return ''
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return ''
    if any(char.isspace() for char in url):
        return ''
    return url


def sourceUrls(selectedKeys=None, customSources=None):
    """Resolve selected built-in source keys plus enabled custom sources."""
    selected = set(DEFAULT_SOURCE_KEYS if selectedKeys is None else selectedKeys)
    urls = [
        item['url'] for item in TRACKER_SOURCE_CATALOG
        if item['key'] in selected
    ]
    for item in customSources or ():
        if isinstance(item, dict):
            if not item.get('enabled', True):
                continue
            value = item.get('url', '')
        else:
            value = item
        url = validSourceUrl(value)
        if url and url not in urls:
            urls.append(url)
    return urls


def fetchTrackers(sources=None, totalTimeout=12, requestTimeout=3):
    """Fetch every selected list and return one merged, deduplicated result."""
    urls = list(sources or sourceUrls())
    if not urls:
        return [], '没有启用 Tracker 来源'

    deadline = time.monotonic() + max(0.1, totalTimeout)
    trackers = []
    seen = set()
    successfulSources = []
    errors = []

    for url in urls:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            errors.append('Tracker 更新超时')
            break
        try:
            request = urllib.request.Request(
                url, headers={'User-Agent': 'Ashore'})
            with urllib.request.urlopen(
                    request, timeout=min(requestTimeout, remaining)) as response:
                values = parseTrackers(response.read().decode('utf-8'))
            if not values:
                errors.append(f'{url} 未返回有效的 Tracker 地址')
                continue
            successfulSources.append(url)
            for tracker in values:
                if tracker not in seen:
                    trackers.append(tracker)
                    seen.add(tracker)
        except (OSError, UnicodeError) as exc:
            errors.append(f'{url}: {exc}')

    if trackers:
        return trackers, successfulSources
    return [], '; '.join(errors) or '所有 Tracker 来源均不可用'
