"""Concurrent reachability checks for BitTorrent trackers."""

import socket
import ssl
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtCore import QThread, pyqtSignal

UDP_CONNECT_MAGIC = 0x41727101980
UDP_CONNECT_ACTION = 0


def probeHttpTracker(url, timeout):
    started = time.monotonic()
    request = urllib.request.Request(
        url, headers={'User-Agent': 'Ashore'}, method='GET')
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1)
    except urllib.error.HTTPError:
        # A tracker that rejects a query-less announce is still reachable.
        pass
    elapsed = round((time.monotonic() - started) * 1000)
    return True, elapsed, ''


def probeUdpTracker(url, timeout):
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname
    port = parsed.port
    if not host or not port:
        return False, None, '无效 UDP Tracker 地址'

    started = time.monotonic()
    transactionId = int(time.time_ns() & 0xffffffff)
    packet = struct.pack('!QII', UDP_CONNECT_MAGIC, UDP_CONNECT_ACTION, transactionId)
    try:
        addresses = socket.getaddrinfo(
            host, port, type=socket.SOCK_DGRAM)
        if not addresses:
            return False, None, '无法解析 Tracker 主机'
        family, socketType, protocol, _, address = addresses[0]
        with socket.socket(family, socketType, protocol) as sock:
            sock.settimeout(timeout)
            sock.sendto(packet, address)
            response, _ = sock.recvfrom(2048)
        if len(response) < 16:
            return False, None, 'UDP Tracker 响应过短'
        action, responseTransaction = struct.unpack('!II', response[:8])
        if action != UDP_CONNECT_ACTION or responseTransaction != transactionId:
            return False, None, 'UDP Tracker 响应无效'
    except OSError as exc:
        return False, None, str(exc)

    elapsed = round((time.monotonic() - started) * 1000)
    return True, elapsed, ''


def probeTracker(url, timeout=2.0):
    parsed = urllib.parse.urlsplit(url)
    try:
        if parsed.scheme == 'udp':
            return probeUdpTracker(url, timeout)
        if parsed.scheme in ('http', 'https'):
            return probeHttpTracker(url, timeout)
        return False, None, '不支持的 Tracker 协议'
    except (OSError, ValueError, urllib.error.URLError, ssl.SSLError) as exc:
        return False, None, str(exc)


class TrackerHealthWorker(QThread):
    resultReady = pyqtSignal(int, str, object, str)
    completed = pyqtSignal(int, int)

    def __init__(self, trackers, timeout=2.0, maxWorkers=8, parent=None):
        super().__init__(parent)
        self.trackers = list(trackers)
        self.timeout = timeout
        self.maxWorkers = max(1, min(int(maxWorkers), 16))

    def run(self):
        healthy = 0
        failed = 0
        executor = ThreadPoolExecutor(max_workers=self.maxWorkers)
        futureMap = {
            executor.submit(probeTracker, url, self.timeout): (index, url)
            for index, url in enumerate(self.trackers)
        }
        interrupted = False
        try:
            for future in as_completed(futureMap):
                if self.isInterruptionRequested():
                    interrupted = True
                    break
                index, _ = futureMap[future]
                try:
                    ok, latency, error = future.result()
                except Exception as exc:
                    ok, latency, error = False, None, str(exc)
                if ok:
                    healthy += 1
                    status = 'healthy'
                else:
                    failed += 1
                    status = 'failed'
                self.resultReady.emit(index, status, latency, error)
        finally:
            if interrupted:
                for future in futureMap:
                    future.cancel()
            executor.shutdown(
                wait=not interrupted, cancel_futures=interrupted)

        if not interrupted:
            self.completed.emit(healthy, failed)
