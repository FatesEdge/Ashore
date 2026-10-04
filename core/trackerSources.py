"""Fetch and validate candidate BitTorrent tracker lists."""

import time
import urllib.parse
import urllib.request

TRACKER_SOURCES = (
    'https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best_ip.txt',
    'https://ngosang.github.io/trackerslist/trackers_best_ip.txt',
    'https://cdn.jsdelivr.net/gh/ngosang/trackerslist@master/trackers_best_ip.txt',
    'https://trackerslist.com/best_aria2.txt',
    'https://cdn.jsdelivr.net/gh/XIU2/TrackersListCollection/best_aria2.txt',
    'https://trackerslist.com/best.txt',
)


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


def fetchTrackers(sources=None, totalTimeout=10, requestTimeout=3):
    """Return the first valid list within one bounded overall refresh window."""
    error = '所有 Tracker 来源均不可用'
    deadline = time.monotonic() + max(0.1, totalTimeout)
    for url in sources or TRACKER_SOURCES:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return [], 'Tracker 更新超时'
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Ashore'})
            with urllib.request.urlopen(request, timeout=min(requestTimeout, remaining)) as response:
                trackers = parseTrackers(response.read().decode('utf-8'))
            if trackers:
                return trackers, url
            error = f'{url} 未返回有效的 Tracker 地址'
        except (OSError, UnicodeError) as exc:
            error = str(exc)
    return [], error
