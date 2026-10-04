"""aria2 JSON-RPC client and download task normalization."""

import base64
import json
import os
import platform
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

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
PLATFORM_NAME = {
    'Darwin': 'MacOS',
    'Linux': 'Linux',
    'Windows': 'Windows',
}.get(platform.system(), 'unknown')


class Aria2Client:

    def __init__(self) -> None:
        self.missions = {key: {} for key in ('active', 'waiting', 'paused', 'completed', 'error')}
        self.missionNames = MissionNames()
        self.globalStatus = {}
        self.confPath = ensureConfig('aria2.conf')
        ensureConfig('aria2.session')
        self.readRpcOptions()

    def readRpcOptions(self):
        options = {}
        for line in self.confPath.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith(('#', ';', '[')) and '=' in line:
                key, value = line.split('=', 1)
                options[key.strip()] = value.strip()
        self.rpcPort = int(options.get('rpc-listen-port', '6801'))
        self.rpcSecret = options.get('rpc-secret', '')

    def addUrl(
            self, url: str, targetDir: str, rename: str | None = None,
            isTorrent: bool | None = None) -> dict:
        """添加单个下载任务
        :param url: str类型下载url
        :param targetDir: str类型下载路径
        :param rename: str类型重命名文件名
        :param isTorrent: bool类型是否为种子或bt链接
        :returns: 成功返回{}空字典,失败返回异常{'ResultError' : int}
        """
        localTorrent = urllib.parse.urlsplit(url).scheme == 'file' or (not urllib.parse.urlsplit(url).scheme and url.lower().endswith('.torrent'))
        if localTorrent:
            path = Path(urllib.request.url2pathname(urllib.parse.urlsplit(url).path)) if url.startswith('file:') else Path(url)
            try:
                content = base64.b64encode(path.read_bytes()).decode('ascii')
            except OSError as exc:
                return {'ResultError': str(exc)}
            return self.call(data=self.makeRequest(RPC_METHODS['addTorrent'],
                                                         [content, [], {'dir': targetDir}]))
        jsonData = None
        if isTorrent is None:
            if url.startswith('magnet:?xt=urn:btih:') or urllib.parse.urlsplit(url).path.lower().endswith('.torrent'):
                isTorrent = True
            else:
                isTorrent = False
        if isTorrent:
            #种子或磁链
            params = [[url], {'dir': targetDir, 'referer': '*'}]
            jsonData = self.makeRequest(method = RPC_METHODS['add'], params = params)
        else:
            #非种子或磁链
            options = {'dir': targetDir, 'referer': '*'}
            if rename:
                options['out'] = rename
            params = [[url], options]
            jsonData = self.makeRequest(method = RPC_METHODS['add'], params = params)
        addResult = self.call(data=jsonData)   #执行添加操作得到返回结果
        return addResult if 'ResultError' in addResult else {}

    def addUrls(self, data: tuple, rename: str | None = None) -> dict:
        """添加多个下载任务
        :param data传入元组类型,[0]为urls,格式为字典分为'urlList'和'torrentList'两个列表,[1]为下载目录
        :param rename: 单个普通链接的目标文件名
        """
        urlList = data[0]['urlList']
        torrentList = data[0]['torrentList']
        targetDir = data[1]
        #添加普通url列表
        errors = []
        for url in urlList + torrentList:
            result = self.addUrl(url, targetDir, rename if len(urlList) == 1 and url == urlList[0] else None)
            if 'ResultError' in result:
                errors.append(f'{url}: {result["ResultError"]}')
        return {'ResultError': '\n'.join(errors)} if errors else {}


    def pause(self, gid:str) -> dict:
        jsonData = self.makeRequest(method = RPC_METHODS['pause'], params=[gid])
        result = self.call(data=jsonData)   #执行添加操作得到返回结果。成功返回gid
        if result == gid:
            return {}       #设置成功返回空字典表示0
        else:
            return result   #设置失败返回带错误字典

    def unpause(self, gid:str) -> dict:
        jsonData = self.makeRequest(method = RPC_METHODS['unpause'], params=[gid])
        result = self.call(data=jsonData)   #执行添加操作得到返回结果。成功返回gid
        if result == gid:
            return {}       #设置成功返回空字典表示0
        else:
            return result   #设置失败返回带错误字典

    def pauseAll(self) -> dict:
        jsonData = self.makeRequest(method = RPC_METHODS['pauseAll'])
        result = self.call(data=jsonData)   #执行添加操作得到返回结果。成功返回'OK'
        if result == 'OK':
            return {}       #设置成功返回空字典表示0
        else:
            return result   #设置失败返回带错误字典

    def unpauseAll(self) -> dict:
        jsonData = self.makeRequest(method = RPC_METHODS['unpauseAll'])
        result = self.call(data=jsonData)   #执行添加操作得到返回结果。成功返回'OK'
        if result == 'OK':
            return {}       #设置成功返回空字典表示0
        else:
            return result   #设置失败返回带错误字典

    def retry(self, gid:str) -> None:
        """重试就是先删除，再新建
        :param gid: 类型的下载任务gid
        :returns: 返回str类型下载任务url,或返回异常{'ResultError' : int}
        """
        missionResult = self.getMission(gid)#获取任务
        if 'ResultError' in missionResult:
            return missionResult    #任务不存在
        else:
            url = missionResult['url']
            isTorrent = missionResult['isTorrent']
            targetDir = missionResult['dir']
            delResult = self.removeMission(gid, False)
            if 'ResultError' in delResult:
                return delResult
            else:
                return self.addUrl(url, targetDir, isTorrent=isTorrent)

    def getGlobalStatus(self) -> dict:
        jsonData = self.makeRequest(method = RPC_METHODS['getGlobalStat'])
        globalResult = self.call(data=jsonData)   #执行添加操作得到返回结果
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
        #对active队列进行处理
        activeData = self.makeRequest(method = RPC_METHODS['tellActive'])
        activeResult = self.call(data = activeData)   #执行添加操作得到返回结果
        if 'ResultError' in activeResult:
            return activeResult
        else:
            activeGids = []
            for item in activeResult:
                gid = item['gid']
                activeGids.append(gid)
                self.updateMission(item, gid, 'active') # 添加或修正mission字典中的任务信息
            self.trimMissions(newGids = activeGids, status = 'active')     #删除多余任务
        #对waiting队列进行处理,分别进入waiting等待队列和paused暂停队列
        waitingData = self.makeRequest(method = RPC_METHODS['tellWaiting'],params=[0, 2000])
        waitingResult = self.call(data = waitingData)   #执行添加操作得到返回结果
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
                    self.updateMission(item, gid, 'paused')  # 添加或修正mission字典中的任务信息
            self.trimMissions(newGids = waitingGids, status = 'waiting')     #删除多余任务
            self.trimMissions(newGids = pausedGids, status = 'paused')     #删除多余任务
        #对stopped队列进行处理
        stoppedData = self.makeRequest(method = RPC_METHODS['tellStopped'],params=[0, 2000])
        stoppedResult = self.call(data = stoppedData)   #执行添加操作得到返回结果
        if 'ResultError' in stoppedResult:
            return stoppedResult
        else:
            completedGids = []
            errorGids = []
            for item in stoppedResult:
                gid = item['gid']
                #这里原作写错了吧，并没有加complete过去式的ed
                if item['status'] == 'complete':
                    completedGids.append(gid)
                    self.updateMission(item, gid, 'completed')
                elif item['status'] == 'error':
                    errorGids.append(gid)
                    self.updateMission(item, gid, 'error')   # 添加或修正mission字典中的任务信息
            self.trimMissions(newGids = completedGids, status = 'completed')     #删除多余任务
            self.trimMissions(newGids = errorGids, status = 'error')     #删除多余任务
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

    def getMission(self, gid:str) -> dict:
        """获取该任务信息,包括 filename、url、dir、isTorrent、totalLength、completedLength、downloadSpeed、uploadSpeed
        :param gid: 类型的下载任务gid
        :returns: 返回dict类型下载任务信息字典,或返回异常{'ResultError' : int}
        """
        for status,missionList in self.missions.items():
            mission = missionList.get(gid)
            if mission is not None:
                return {**mission, 'status': status}
        return {'ResultError' : -4}

    def getAria2Version(self) -> str:
        result = self.call(data=self.makeRequest(RPC_METHODS['getVersion']))
        return result.get('version', '未知') if isinstance(result, dict) else '未知'

    def seekFileName(self, item:dict, bittorrent:bool) -> tuple[str, bool]:
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
            return item.get('infoHash', '正在获取 BT 元数据'), False
        if first.get('path'):
            return urllib.parse.unquote(Path(first['path']).name), True
        name = self.urlName(first.get('path') or url)
        return urllib.parse.unquote(name) or '正在获取文件名', False

    def urlName(self, url:str) -> str:
        #从url中提取文件名
        string = url.split('?', 1)[0]
        string = string.split('/')[-1]
        string = string.split('[METADATA]')[-1]
        return string

    def updateMission(self, item:dict, gid:str, status:str) -> None: # 添加或修正mission字典中的任务信息
        first = (item.get('files') or [{}])[0]
        uris = first.get('uris') or []
        sourceUrl = uris[0].get('uri', '') if uris else ''
        isTorrent = 'bittorrent' in item or bool(item.get('infoHash'))
        url = ('magnet:?xt=urn:btih:' + item['infoHash']) if item.get('infoHash') else sourceUrl
        filename, retain = self.seekFileName(item, isTorrent)
        filename = self.missionNames.resolve(gid, filename, retain)
        # 设置进任务mission字典
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
        #比较新gid列表中已经删除、完成的任务，但原始列表仍存在的，进行删除
        removeGids = set(self.missions[status].keys()).difference(set(newGids))
        for gid in removeGids:
            del self.missions[status][gid]

    def getUrl(self, gid:str) -> dict:
        """通过任务gid获取下载地址url
        :returns: 返回str类型下载任务url,或返回异常{'ResultError' : int}
        """
        mission = self.getMission(gid)
        if 'ResultError' in mission:
            #若未找到所给gid的任务，返回含错误代码字典{'ResultError' : -4}
            return mission
        else:
            return {'url' : mission['url']}

    def removeMission(self, gid:str, delFile:bool=False) -> dict:
        """从任务列表中移除任务&彻底删除任务(包括下载文件)两个功能
        :param gid: str类型任务gid
        :param delFile: bool类型标志符:False列表中移除任务不删文件,True彻底删除
        :returns: 成功返回{}空字典,失败返回异常{'ResultError' : int}
        """
        mission = self.getMission(gid)
        if 'ResultError' in mission:
            #若未找到所给gid的任务，返回含错误代码字典{'ResultError' : -4}
            return mission
        else:
            #找到任务开始处理
            if mission['status'] == 'active' or mission['status'] == 'waiting' or mission['status'] == 'paused':
                #若任务进行中，则先用方法使任务进入remove列表掉再删除
                jsonData = self.makeRequest(method = RPC_METHODS['remove'], params=[gid])
                result = self.call(data=jsonData)   #执行添加操作得到返回结果
                if 'ResultError' in result:
                    return result       #若报错直接返回错误
                # 这段有点迷惑 elif mission['status'] == 'completed' or mission['status'] == 'error' or mission['status'] == 'removed':这段有点迷惑
            time.sleep(0.1)

            # 具体删除任务removes a completed/error/removed download
            jsonData = self.makeRequest(method = RPC_METHODS['removeResult'], params=[gid])
            result = self.call(data=jsonData)   #执行添加操作得到返回结果
            if 'ResultError' in result:
                return result       #若报错直接返回错误

            if delFile:
                try:
                    self.deleteTaskFiles(mission)
                except (OSError, ValueError) as exc:
                    return {'ResultError': str(exc)}
            return {}

    def deleteTaskFiles(self, mission):
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
            # Validate the complete set before touching any files.
            if candidate.is_symlink() or not candidate.resolve().is_relative_to(root) or candidate.resolve() == root:
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

    def openFileDir(self, gid:str) -> dict:
        mission = self.getMission(gid)
        if 'ResultError' in mission:
            #若未找到所给gid的任务，返回含错误代码字典{'ResultError' : -4}
            return mission
        else:
            platformSystem = PLATFORM_NAME
            filePath = mission['dir'] + '/' + mission['filename']
            if platformSystem == 'MacOS':           # MacOS
                cmd = ['open', '-R', filePath]
            elif platformSystem == 'Linux':         # Linux
                if shutil.which('nautilus') and os.path.exists(filePath):
                    cmd = ['nautilus', '--select', filePath]
                else:
                    return {'dir' : mission['dir']}
            elif platformSystem == 'Windows':       # Windows
                cmd = ['explorer', '/select,', filePath]
            else:           #防止其他情况
                return {'dir' : mission['dir']}
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {} #返回空字典表示0成功

    def getFilePath(self, gid:str) -> dict:
        mission = self.getMission(gid)
        if 'ResultError' in mission:
            #若未找到任务，返回含错误代码-4的字典
            return mission
        else:
            #若存在返回目录+文件名
            return {'filePath' : mission['dir'] + '/' + mission['filename']}

    def getGlobalConfig(self) -> dict:
        jsonData = self.makeRequest(method = RPC_METHODS['getGlobalOption'])
        result = self.call(data=jsonData)   #执行添加操作得到返回结果
        return result

    def setGlobalConfig(self, conf: dict | None = None) -> dict:
        jsonData = self.makeRequest(method = RPC_METHODS['changeGlobalOption'], params = [conf])
        result = self.call(data=jsonData)   #执行添加操作得到返回结果
        if result == 'OK':
            return {}       #设置成功返回空字典表示0
        else:
            return result   #设置失败返回带错误字典

    def makeRequest(self, method: str, params: list | None = None) -> str:
        #生成json格式数据
        data = json.dumps({'jsonrpc' : '2.0', 'id' : 'qwer', 'method' : method, 'params' : params or []})
        return data

    def call(self, data:str='{}') -> dict:
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
                return {'ResultError': result['error'].get('message', 'aria2 RPC 错误')}
            return result['result']
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            return {'ResultError': str(exc)}

    def isRpcReady(self) -> bool:
        return 'ResultError' not in self.getGlobalStatus()

    def saveSession(self):
        jsonData = self.makeRequest(method = RPC_METHODS['saveSession'])
        saveResult = self.call(data=jsonData)   #执行添加操作得到返回结果
        if saveResult == 'OK':
            return {}       #设置成功返回空字典表示0
        else:
            return saveResult   #设置失败返回带错误字典
