"""aria2 JSON-RPC client and download task normalization."""

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from core.configStore import readOptions
from core.downloadRequest import (
    DownloadItem,
    DownloadRequest,
    ITEM_LOCAL_TORRENT,
    classifyInput,
)
from core.fileOperations import deleteTaskFiles, deleteTaskSidecars
from core.missionNames import MissionNames
from paths import ensureConfig

RPC_TIMEOUT = 1
RPC_METHODS = {
    'getGlobalStat': 'aria2.getGlobalStat',
    'add': 'aria2.addUri',
    'addTorrent': 'aria2.addTorrent',
    'remove': 'aria2.remove',
    'removeResult': 'aria2.removeDownloadResult',
    'pause': 'aria2.pause',
    'unpause': 'aria2.unpause',
    'pauseAll': 'aria2.pauseAll',
    'unpauseAll': 'aria2.unpauseAll',
    'tellActive': 'aria2.tellActive',
    'tellStatus': 'aria2.tellStatus',
    'tellWaiting': 'aria2.tellWaiting',
    'tellStopped': 'aria2.tellStopped',
    'getVersion': 'aria2.getVersion',
    'getGlobalOption': 'aria2.getGlobalOption',
    'changeGlobalOption': 'aria2.changeGlobalOption',
    'saveSession': 'aria2.saveSession',
    'shutdown': 'aria2.shutdown',
}
ERROR_MESSAGES = {
    -4: 'Mission Not Found',
}

class Aria2Client:

    def __init__(self) -> None:
        self.missions = {key: {} for key in ('active', 'waiting', 'paused', 'completed', 'error')}
        self.missionNames = MissionNames()
        self.globalStatus = {}
        self.confPath = ensureConfig('aria2.conf')
        self.readRpcOptions()

    def readRpcOptions(self):
        options = readOptions(self.confPath)
        self.rpcPort = int(options.get('rpc-listen-port', '6801'))
        self.rpcSecret = options.get('rpc-secret', '')


    def addUrl(
            self, item: DownloadItem, targetDir: str,
            options: dict | None = None) -> dict:
        """Add one validated download item."""
        requestOptions = dict(options or {})
        requestOptions['dir'] = targetDir

        if item.kind == ITEM_LOCAL_TORRENT:
            try:
                content = base64.b64encode(
                    Path(item.source).read_bytes()).decode('ascii')
            except OSError as exc:
                return {'ResultError': str(exc)}
            requestOptions.pop('out', None)
            result = self.call(data=self.makeRequest(
                RPC_METHODS['addTorrent'],
                [content, [], requestOptions]))
            return (
                result
                if isinstance(result, dict) and 'ResultError' in result
                else {})

        if item.supportsHttpOptions:
            requestOptions.setdefault('referer', '*')
            if not item.supportsOutputName:
                requestOptions.pop('out', None)
        else:
            requestOptions = {'dir': targetDir}

        result = self.call(data=self.makeRequest(
            RPC_METHODS['add'],
            [[item.source], requestOptions]))
        return (
            result
            if isinstance(result, dict) and 'ResultError' in result
            else {})

    def addUrls(self, request: DownloadRequest) -> dict:
        """Add all items from one validated download request."""
        errors = []
        for item in request.items:
            options = request.options if item.supportsHttpOptions else {}
            result = self.addUrl(item, request.targetDir, options)
            if 'ResultError' in result:
                errors.append(
                    f'{item.source}: {result["ResultError"]}')
        return {'ResultError': '\n'.join(errors)} if errors else {}
    def taskCommand(self, method, expected, params=None):
        result = self.call(data=self.makeRequest(
            RPC_METHODS[method], params))
        return {} if result == expected else result

    def pause(self, gid: str) -> dict:
        return self.taskCommand('pause', gid, [gid])

    def unpause(self, gid: str) -> dict:
        return self.taskCommand('unpause', gid, [gid])

    def pauseAll(self) -> dict:
        return self.taskCommand('pauseAll', 'OK')

    def unpauseAll(self) -> dict:
        return self.taskCommand('unpauseAll', 'OK')

    def retry(self, gid: str) -> dict:
        """Remove and recreate one task from its normalized source URL."""
        missionResult = self.getMission(gid)
        if 'ResultError' in missionResult:
            return missionResult
        else:
            url = missionResult['url']
            targetDir = missionResult['dir']
            delResult = self.removeMission(gid, False)
            if 'ResultError' in delResult:
                return delResult
            else:
                item = classifyInput(url)
                if item is None:
                    return {'ResultError': 'Unable to recognize the original download source'}
                return self.addUrl(item, targetDir)

    def getGlobalStatus(self) -> dict:
        jsonData = self.makeRequest(method=RPC_METHODS['getGlobalStat'])
        globalResult = self.call(data=jsonData)
        if 'ResultError' in globalResult:
            return globalResult
        else:
            self.globalStatus = globalResult
            return globalResult

    def getMissions(self) -> dict:
        statusResult = self.getGlobalStatus()
        self.lastPollGlobalStatus = statusResult
        if 'ResultError' in statusResult:
            return statusResult
        activeData = self.makeRequest(method=RPC_METHODS['tellActive'])
        activeResult = self.call(data=activeData)
        if 'ResultError' in activeResult:
            return activeResult
        else:
            activeGids = []
            for item in activeResult:
                gid = item['gid']
                activeGids.append(gid)
                self.updateMission(item, gid, 'active')
            self.trimMissions(newGids=activeGids, status='active')
        waitingData = self.makeRequest(method=RPC_METHODS['tellWaiting'], params=[0, 2000])
        waitingResult = self.call(data=waitingData)
        if 'ResultError' in waitingResult:
            return waitingResult
        else:
            waitingGids = []
            pausedGids = []
            for item in waitingResult:
                gid = item['gid']
                if item['status'] == 'waiting':
                    waitingGids.append(gid)
                    self.updateMission(item, gid, 'waiting')
                elif item['status'] == 'paused':
                    pausedGids.append(gid)
                    self.updateMission(item, gid, 'paused')
            self.trimMissions(newGids=waitingGids, status='waiting')
            self.trimMissions(newGids=pausedGids, status='paused')
        stoppedData = self.makeRequest(method=RPC_METHODS['tellStopped'], params=[0, 2000])
        stoppedResult = self.call(data=stoppedData)
        if 'ResultError' in stoppedResult:
            return stoppedResult
        else:
            completedGids = []
            errorGids = []
            for item in stoppedResult:
                gid = item['gid']
                if item['status'] == 'complete':
                    completedGids.append(gid)
                    self.updateMission(item, gid, 'completed')
                elif item['status'] == 'error':
                    errorGids.append(gid)
                    self.updateMission(item, gid, 'error')
            self.trimMissions(newGids=completedGids, status='completed')
            self.trimMissions(newGids=errorGids, status='error')
        self.mergeFollowedTasks()
        self.missionNames.sync(gid for group in self.missions.values() for gid in group)
        return self.missions

    def mergeFollowedTasks(self):
        """Use aria2's parent/child relation to display a torrent as one task."""
        byGid = {gid: (status, task) for status, group in self.missions.items()
                  for gid, task in group.items()}
        for gid, (status, task) in list(byGid.items()):
            parent = task.get('following')
            if parent and parent in byGid:
                parentStatus, parentTask = byGid[parent]
                task['url'] = parentTask.get('url') or task['url']
                if not task['filename']:
                    task['filename'] = parentTask['filename']
                self.missions[parentStatus].pop(parent, None)
        for gid, (status, task) in byGid.items():
            if task.get('followedBy'):
                self.missions[status].pop(gid, None)

    def getMission(self, gid: str) -> dict:
        """Return one normalized mission, including its current status."""
        for status, missionList in self.missions.items():
            mission = missionList.get(gid)
            if mission is not None:
                return {**mission, 'status': status}
        return {'ResultError' : -4}

    def getAria2Version(self) -> str:
        result = self.call(data=self.makeRequest(RPC_METHODS['getVersion']))
        return result.get('version', '—') if isinstance(result, dict) else '—'

    def seekFileName(self, item: dict, bittorrent: bool) -> tuple[str, bool]:
        """Return the best current name and whether it is worth retaining."""
        files = item.get('files') or []
        first = files[0] if files else {}
        uris = first.get('uris') or []
        url = uris[0].get('uri', '') if uris else ''
        if bittorrent:
            name = item.get('bittorrent', {}).get('info', {}).get('name')
            if name:
                return name, True
            if first.get('path') and not Path(first['path']).name.startswith('[METADATA]'):
                return Path(first['path']).name, True
            magnetName = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get('dn', [])
            if magnetName:
                return magnetName[0], True
            return item.get('infoHash', '…'), False
        if first.get('path'):
            return urllib.parse.unquote(Path(first['path']).name), True
        name = self.urlName(first.get('path') or url)
        return urllib.parse.unquote(name) or '…', False

    def urlName(self, url:str) -> str:
        string = url.split('?', 1)[0]
        string = string.split('/')[-1]
        string = string.split('[METADATA]')[-1]
        return string

    def updateMission(self, item: dict, gid: str, status: str) -> None:
        first = (item.get('files') or [{}])[0]
        uris = first.get('uris') or []
        sourceUrl = uris[0].get('uri', '') if uris else ''
        isTorrent = 'bittorrent' in item or bool(item.get('infoHash'))
        url = ('magnet:?xt=urn:btih:' + item['infoHash']) if item.get('infoHash') else sourceUrl
        filename, retain = self.seekFileName(item, isTorrent)
        filename = self.missionNames.resolve(gid, filename, retain)
        self.missions[status][gid] = {
            'totalLength'       : int(item.get('totalLength', 0)),
            'completedLength'   : int(item.get('completedLength', 0)),
            'dir'               : item.get('dir', ''),
            'url'               : url,
            'downloadSpeed'     : int(item.get('downloadSpeed', 0)),
            'uploadSpeed'       : int(item.get('uploadSpeed', 0)),
            'filename'          : filename,
            'isTorrent'         : isTorrent,
            'following'         : item.get('following'),
            'followedBy'        : item.get('followedBy'),
            'files'             : [file.get('path', '') for file in item.get('files', [])],
            }

    def trimMissions(self, newGids:set, status:str) -> None:
        removeGids = set(self.missions[status].keys()).difference(set(newGids))
        for gid in removeGids:
            del self.missions[status][gid]

    def getUrl(self, gid: str) -> dict:
        """Return the normalized source URL for one mission."""
        mission = self.getMission(gid)
        if 'ResultError' in mission:
            return mission
        else:
            return {'url' : mission['url']}


    def removeMission(self, gid: str, delFile: bool = False) -> dict:
        """Remove a task from aria2, then clean its control/payload files."""
        mission = self.getMission(gid)
        if 'ResultError' in mission:
            return mission

        if mission['status'] in ('active', 'waiting', 'paused'):
            result = self.call(data=self.makeRequest(
                RPC_METHODS['remove'], [gid]))
            if isinstance(result, dict) and 'ResultError' in result:
                return result

        # aria2.remove() already transitions an in-progress task to "removed".
        # Querying tellStatus() in between is racy: some aria2 builds may no
        # longer expose the GID by the time that follow-up request arrives.
        result = self.call(data=self.makeRequest(
            RPC_METHODS['removeResult'], [gid]))
        if isinstance(result, dict) and 'ResultError' in result:
            message = str(result['ResultError'])
            if 'is not found' not in message:
                return result

        try:
            if delFile:
                deleteTaskFiles(mission)
            else:
                deleteTaskSidecars(mission)
        except (OSError, ValueError) as exc:
            return {'ResultError': str(exc)}
        return {}
    def getFilePath(self, gid: str) -> dict:
        mission = self.getMission(gid)
        if 'ResultError' in mission:
            return mission
        files = [path for path in mission.get('files', []) if path]
        if len(files) == 1:
            path = Path(files[0])
            if not path.is_absolute():
                path = Path(mission['dir']) / path
            return {'filePath': str(path)}
        return {
            'filePath': str(Path(mission['dir']) / mission['filename'])
        }
    def getGlobalConfig(self) -> dict:
        jsonData = self.makeRequest(method=RPC_METHODS['getGlobalOption'])
        result = self.call(data=jsonData)
        return result

    def setGlobalConfig(self, conf: dict | None = None) -> dict:
        jsonData = self.makeRequest(
            method=RPC_METHODS['changeGlobalOption'], params=[conf])
        result = self.call(data=jsonData)
        return {} if result == 'OK' else result

    def makeRequest(self, method: str, params: list | None = None) -> str:
        data = json.dumps({
            'jsonrpc': '2.0',
            'id': 'ashore',
            'method': method,
            'params': params or [],
        })
        return data

    def call(self, data: str = '{}') -> dict:
        payload = json.loads(data)
        if self.rpcSecret:
            payload['params'].insert(0, 'token:' + self.rpcSecret)
        url = f'http://127.0.0.1:{self.rpcPort}/jsonrpc'
        try:
            request = urllib.request.Request(url, json.dumps(payload).encode('utf-8'),
                                             {'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=RPC_TIMEOUT) as response:
                result = json.load(response)
            if 'error' in result:
                return {'ResultError': result['error'].get('message', 'aria2 RPC error')}
            return result['result']
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode('utf-8', errors='replace').strip()
                payload = json.loads(body) if body else {}
                message = payload.get('error', {}).get('message')
                if message:
                    return {'ResultError': message}
            except (OSError, ValueError, UnicodeDecodeError, AttributeError):
                pass
            return {'ResultError': f'HTTP {exc.code}: {exc.reason}'}
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            return {'ResultError': str(exc)}

    def isRpcReady(self) -> bool:
        return 'ResultError' not in self.getGlobalStatus()

    def saveSession(self):
        jsonData = self.makeRequest(method=RPC_METHODS['saveSession'])
        saveResult = self.call(data=jsonData)
        return {} if saveResult == 'OK' else saveResult
