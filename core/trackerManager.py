"""Automatic BitTorrent tracker refresh and persistence."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from core.configStore import (
    boolValue,
    readAshore,
    readOptions,
    writeAshore,
    writeOptions,
)
from core.trackerSources import fetchTrackers, parseTrackers

AUTO_UPDATE_KEY = 'trackers_auto_update'
LAST_SUCCESS_KEY = 'trackers_list_time'
SOURCE_KEY = 'trackers_list_source'
UPDATE_AGE = timedelta(days=1)


def isoNow():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def parseTime(value):
    if not value or value == '尚未更新':
        return None
    for parser in (
            lambda: datetime.fromisoformat(value),
            lambda: datetime.strptime(value, '%Y.%m.%d %H:%M').astimezone()):
        try:
            parsed = parser()
            return parsed if parsed.tzinfo else parsed.astimezone()
        except (ValueError, TypeError):
            continue
    return None


def displayTime(value):
    parsed = parseTime(value)
    return parsed.astimezone().strftime('%Y.%m.%d %H:%M') if parsed else '尚未更新'


def updateDue(lastSuccess, now=None):
    parsed = parseTime(lastSuccess)
    if parsed is None:
        return True
    now = now or datetime.now(timezone.utc).astimezone()
    return now.astimezone(timezone.utc) - parsed.astimezone(timezone.utc) >= UPDATE_AGE


class TrackerWorker(QThread):
    completed = pyqtSignal(list, str)

    def run(self):
        trackers, source = fetchTrackers()
        self.completed.emit(trackers, source)


class TrackerManager(QObject):
    statusChanged = pyqtSignal(str)
    updated = pyqtSignal(list, str, str)
    failed = pyqtSignal(str)

    def __init__(self, ashorePath, aria2Path, defaultsPath=None, parent=None):
        super().__init__(parent)
        self.ashorePath = Path(ashorePath)
        self.aria2Path = Path(aria2Path)
        self.defaultsPath = defaultsPath
        self.worker = None

    def shouldUpdate(self, force=False):
        if force:
            return True
        settings = readAshore(self.ashorePath, self.defaultsPath)
        trackers = parseTrackers(readOptions(self.aria2Path).get('bt-tracker', ''))
        firstRun = not trackers
        automatic = boolValue(settings.get(AUTO_UPDATE_KEY), True)
        return firstRun or (automatic and updateDue(settings.get(LAST_SUCCESS_KEY)))

    def start(self, force=False):
        if self.worker and self.worker.isRunning():
            return False
        if not self.shouldUpdate(force):
            self.statusChanged.emit('BT Tracker 已是最新')
            return False
        self.statusChanged.emit('正在更新 BT Tracker')
        self.worker = TrackerWorker(self)
        self.worker.completed.connect(self.finish)
        self.worker.finished.connect(self.clearWorker)
        self.worker.start()
        return True

    def clearWorker(self):
        worker = self.worker
        self.worker = None
        if worker:
            worker.deleteLater()

    def finish(self, trackers, sourceOrError):
        if not trackers:
            self.statusChanged.emit('BT Tracker 更新失败，继续使用现有列表')
            self.failed.emit(sourceOrError)
            return
        timestamp = isoNow()
        oldTracker = readOptions(self.aria2Path).get('bt-tracker', '')
        oldSettings = readAshore(self.ashorePath, self.defaultsPath)
        aria2Saved = writeOptions(self.aria2Path, {'bt-tracker': ','.join(trackers)})
        ashoreSaved = writeAshore(self.ashorePath, {
            LAST_SUCCESS_KEY: timestamp,
            SOURCE_KEY: sourceOrError,
        })
        if not aria2Saved or not ashoreSaved:
            writeOptions(self.aria2Path, {'bt-tracker': oldTracker})
            writeAshore(self.ashorePath, {
                LAST_SUCCESS_KEY: oldSettings.get(LAST_SUCCESS_KEY, '尚未更新'),
                SOURCE_KEY: oldSettings.get(SOURCE_KEY, ''),
            })
            self.statusChanged.emit('BT Tracker 保存失败，继续使用现有列表')
            self.failed.emit('无法写入配置目录')
            return
        self.statusChanged.emit('BT Tracker 更新完成')
        self.updated.emit(trackers, sourceOrError, timestamp)
