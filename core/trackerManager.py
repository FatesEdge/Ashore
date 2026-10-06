"""Automatic BitTorrent tracker refresh and persistence."""

import json
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
from core.trackerSources import DEFAULT_SOURCE_KEYS, fetchTrackers, parseTrackers, sourceUrls

AUTO_UPDATE_KEY = 'trackers_auto_update'
LAST_SUCCESS_KEY = 'trackers_list_time'
SOURCE_KEY = 'trackers_list_source'
SOURCE_KEYS_KEY = 'tracker_source_keys'
CUSTOM_SOURCES_KEY = 'tracker_custom_sources'
UPDATE_AGE = timedelta(days=1)
LEGACY_EMPTY_TIMESTAMPS = {'尚未更新'}


def isoNow():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def parseTime(value):
    if not value or value in LEGACY_EMPTY_TIMESTAMPS:
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
    return parsed.astimezone().strftime('%Y.%m.%d %H:%M') if parsed else ''


def updateDue(lastSuccess, now=None):
    parsed = parseTime(lastSuccess)
    if parsed is None:
        return True
    now = now or datetime.now(timezone.utc).astimezone()
    return now.astimezone(timezone.utc) - parsed.astimezone(timezone.utc) >= UPDATE_AGE


def jsonList(value, default):
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        parsed = None
    return parsed if isinstance(parsed, list) else list(default)


class TrackerWorker(QThread):
    completed = pyqtSignal(list, object)

    def __init__(self, sources, parent=None):
        super().__init__(parent)
        self.sources = list(sources)

    def run(self):
        trackers, sourceResult = fetchTrackers(self.sources)
        self.completed.emit(trackers, sourceResult)


class TrackerManager(QObject):
    statusChanged = pyqtSignal(str)
    updated = pyqtSignal(list, list, str)
    failed = pyqtSignal(str)

    def __init__(self, ashorePath, aria2Path, defaultsPath=None, parent=None):
        super().__init__(parent)
        self.ashorePath = Path(ashorePath)
        self.aria2Path = Path(aria2Path)
        self.defaultsPath = defaultsPath
        self.worker = None

    def configuredSources(self):
        settings = readAshore(self.ashorePath, self.defaultsPath)
        keys = jsonList(settings.get(SOURCE_KEYS_KEY), DEFAULT_SOURCE_KEYS)
        custom = jsonList(settings.get(CUSTOM_SOURCES_KEY), ())
        return sourceUrls(keys, custom)

    def shouldUpdate(self, force=False):
        if force:
            return True
        settings = readAshore(self.ashorePath, self.defaultsPath)
        trackers = parseTrackers(readOptions(self.aria2Path).get('bt-tracker', ''))
        firstRun = not trackers
        automatic = boolValue(settings.get(AUTO_UPDATE_KEY), True)
        return firstRun or (automatic and updateDue(settings.get(LAST_SUCCESS_KEY)))

    def start(self, force=False, sources=None):
        if self.worker and self.worker.isRunning():
            return False
        if not self.shouldUpdate(force):
            self.statusChanged.emit('trackerUpToDate')
            return False
        selectedSources = list(sources if sources is not None else self.configuredSources())
        if not selectedSources:
            self.failed.emit('noTrackerSources')
            return False
        self.statusChanged.emit('trackerUpdatingStatus')
        self.worker = TrackerWorker(selectedSources, self)
        self.worker.completed.connect(self.finish)
        self.worker.finished.connect(self.clearWorker)
        self.worker.start()
        return True

    def clearWorker(self):
        worker = self.worker
        self.worker = None
        if worker:
            worker.deleteLater()

    def finish(self, trackers, sourceResult):
        if not trackers:
            self.statusChanged.emit('trackerUpdateFailedKeeping')
            self.failed.emit(str(sourceResult))
            return
        successfulSources = list(sourceResult)
        timestamp = isoNow()
        oldTracker = readOptions(self.aria2Path).get('bt-tracker', '')
        oldSettings = readAshore(self.ashorePath, self.defaultsPath)
        aria2Saved = writeOptions(
            self.aria2Path, {'bt-tracker': ','.join(trackers)})
        ashoreSaved = writeAshore(self.ashorePath, {
            LAST_SUCCESS_KEY: timestamp,
            SOURCE_KEY: json.dumps(successfulSources, ensure_ascii=False),
        })
        if not aria2Saved or not ashoreSaved:
            writeOptions(self.aria2Path, {'bt-tracker': oldTracker})
            writeAshore(self.ashorePath, {
                LAST_SUCCESS_KEY: oldSettings.get(LAST_SUCCESS_KEY, ''),
                SOURCE_KEY: oldSettings.get(SOURCE_KEY, ''),
            })
            self.statusChanged.emit('trackerSaveFailedKeeping')
            self.failed.emit('trackerConfigWriteFailed')
            return
        self.statusChanged.emit('trackerUpdateComplete')
        self.updated.emit(trackers, successfulSources, timestamp)
