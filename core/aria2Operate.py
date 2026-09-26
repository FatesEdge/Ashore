#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Time    :   2023/03/25 15:06:43
@File    :   aria2Operate.py
@Software:   VSCode
@Author  :   PPPPAN 
@Version :   0.7.66
@Contact :   for_freedom_x64@live.com
'''

import urllib.request, urllib.error, urllib.parse, json, os, platform, subprocess, time, shutil, base64
from pathlib import Path
from paths import CONFIG_DIR, ensure_config
from core.missionNames import MissionNames

class Aria2Operate():
    totalNum = 1
    missions = {}
    globalStatus = {
        'downloadSpeed'     : None,
        'numActive'         : None,     #正在下载及暂停的任务数量
        'numStopped'        : None,     #已完成及失败的任务数量
        'numStoppedTotal'   : None,     #所有任务？？？
        'numWaiting'        : None,     #排队等待的任务数量
        'uploadSpeed'       : None
        }
    missionStatusList = ['totalLength','completedLength','downloadSpeed']
    TIMEOUTSED = 1
    ARIA2METHOD = {
        'getGlobalStat'         : 'aria2.getGlobalStat',
        'add'                   : 'aria2.addUri',
        'addTorrent'            : 'aria2.addTorrent',
        'addMetalink'           : 'aria2.addMetalink',
        'remove'                : 'aria2.remove',
        'removeResult'          : 'aria2.removeDownloadResult',
        'pause'                 : 'aria2.pause',
        'unpause'               : 'aria2.unpause',
        'pauseAll'              : 'aria2.pauseAll',
        'unpauseAll'            : 'aria2.unpauseAll',
        'tellActive'            : 'aria2.tellActive',
        'tellWaiting'           : 'aria2.tellWaiting',
        'tellStopped'           : 'aria2.tellStopped',
        # 'tellWaiting': 'aria2.tellWaiting',
        'getVersion'            : 'aria2.getVersion',
        'getFiles'              : 'aria2.getFiles',
        'tellStatus'            : 'aria2.tellStatus',
        'getGlobalOption'       : 'aria2.getGlobalOption',
        'changeGlobalOption'    : 'aria2.changeGlobalOption',
        'saveSession'           : 'aria2.saveSession',
        }

    ERRORLIST = {
         0  : "succeed",
        -1  : "HTTP Error",
        -2  : "URL Error",
        -3  : "WebSocket Error",
        -4  : 'Mission Not Found',
        -5  : 'Exception Error"',
        -6  : 'Unknow Error',
    }

    #搞清当前系统
    PlatformSystem = 'unknow'
    if platform.system() == 'Darwin':
        PlatformSystem = 'MacOS'
    elif platform.system() == 'Linux':
        PlatformSystem = 'Linux'
    elif platform.system() == 'Windows':
        PlatformSystem = 'Windows'

    def __init__(self, BASEPATH:str=None, QuitWithAria2:bool=False) -> None:
        self.isRelease = bool(getattr(__import__('sys'), 'frozen', False))
        self.missions = {key: {} for key in ('active', 'waiting', 'paused', 'completed', 'error')}
        self.missionNames = MissionNames()
        self.globalStatus = {}
        self.QuitWithAria2 = QuitWithAria2
        self.process = None
        self.conf_path = ensure_config('aria2.conf')
        ensure_config('aria2.session')
        self._read_rpc_options()
        if 'ResultError' in self.getGlobalStatus():
            if not self.isAria2Installed():
                raise RuntimeError('未检测到 aria2c。请先安装 aria2，再启动 Ashore。')
            self.startAria2(BASEPATH)

    def _read_rpc_options(self):
        options = {}
        for line in self.conf_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith(('#', ';', '[')) and '=' in line:
                key, value = line.split('=', 1)
                options[key.strip()] = value.strip()
        self.rpc_port = int(options.get('rpc-listen-port', '6801'))
        self.rpc_secret = options.get('rpc-secret', '')

    def addUrl(self, url:str, targetDir:str, rename:str=None, isTorrent:bool=None) -> dict:
        """添加单个下载任务
        :param url: str类型下载url
        :param targetDir: str类型下载路径
        :param rename: str类型重命名文件名
        :param isTorrent: bool类型是否为种子或bt链接
        :returns: 成功返回{}空字典,失败返回异常{'ResultError' : int}
        """
        local_torrent = urllib.parse.urlsplit(url).scheme == 'file' or (not urllib.parse.urlsplit(url).scheme and url.lower().endswith('.torrent'))
        if local_torrent:
            path = Path(urllib.request.url2pathname(urllib.parse.urlsplit(url).path)) if url.startswith('file:') else Path(url)
            try:
                content = base64.b64encode(path.read_bytes()).decode('ascii')
            except OSError as exc:
                return {'ResultError': str(exc)}
            return self.performan(data=self.produceJson(self.ARIA2METHOD['addTorrent'],
                                                         [content, [], {'dir': targetDir}]))
        jsonData = None
        if isTorrent == None:
            if url.startswith('magnet:?xt=urn:btih:') or urllib.parse.urlsplit(url).path.lower().endswith('.torrent'):
                isTorrent = True
            else:
                isTorrent = False
        if isTorrent == True:
            #种子或磁链
            params = [[url], {'dir': targetDir, 'referer': '*'}]
            jsonData = self.produceJson(method = self.ARIA2METHOD['add'], params = params)
        else:
            #非种子或磁链
            options = {'dir': targetDir, 'referer': '*'}
            if rename:
                options['out'] = rename
            params = [[url], options]
            jsonData = self.produceJson(method = self.ARIA2METHOD['add'], params = params)
        addReslut = self.performan(data=jsonData)   #执行添加操作得到返回结果
        return addReslut if 'ResultError' in addReslut else {}

    def addUrls(self, data:tuple=None, rename:str=None) -> None:
        """添加多个下载任务
        :param data传入元组类型,[0]为urls,格式为字典分为'urlList'和'torrentList'两个列表,[1]为下载目录
        :param name暂未设置,后续考虑加入为data[2]
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


    def addTorrent(self):
        """还未想好

        """

    def pause(self, gid:str) -> dict:
        jsonData = self.produceJson(method = self.ARIA2METHOD['pause'], params=[gid])
        result = self.performan(data=jsonData)   #执行添加操作得到返回结果。成功返回gid
        if result == gid:
            return {}       #设置成功返回空字典表示0
        else:
            return result   #设置失败返回带错误字典

    def unpause(self, gid:str) -> dict:
        jsonData = self.produceJson(method = self.ARIA2METHOD['unpause'], params=[gid])
        result = self.performan(data=jsonData)   #执行添加操作得到返回结果。成功返回gid
        if result == gid:
            return {}       #设置成功返回空字典表示0
        else:
            return result   #设置失败返回带错误字典

    def pauseAll(self) -> dict:
        jsonData = self.produceJson(method = self.ARIA2METHOD['pauseAll'])
        result = self.performan(data=jsonData)   #执行添加操作得到返回结果。成功返回'OK'
        if result == 'OK':
            return {}       #设置成功返回空字典表示0
        else:
            return result   #设置失败返回带错误字典

    def unpauseAll(self) -> dict:
        jsonData = self.produceJson(method = self.ARIA2METHOD['unpauseAll'])
        result = self.performan(data=jsonData)   #执行添加操作得到返回结果。成功返回'OK'
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
            delResult = self.delRemoveMission(gid, False)
            if 'ResultError' in delResult:
                return delResult
            else:
                return self.addUrl(url, targetDir, isTorrent=isTorrent)

    def getGlobalStatus(self) -> dict:
        jsonData = self.produceJson(method = self.ARIA2METHOD['getGlobalStat'])
        globalResult = self.performan(data=jsonData)   #执行添加操作得到返回结果
        if 'ResultError' in globalResult:
            return globalResult
        else:
            self.globalStatus = globalResult
            return globalResult

    def getMissions(self) -> dict:
        status_result = self.getGlobalStatus()
        self.lastPollGlobalStatus = status_result
        if 'ResultError' in status_result:
            return status_result
        #对active队列进行处理
        activeData = self.produceJson(method = self.ARIA2METHOD['tellActive'])
        activeResult = self.performan(data = activeData)   #执行添加操作得到返回结果
        self.totalNum = 0
        if 'ResultError' in activeResult:
            return activeResult
        else:
            activeGids = []
            for item in activeResult:
                gid = item['gid']
                activeGids.append(gid)
                self.setAttribute(item, gid, 'active') # 添加或修正mission字典中的任务信息
                # self.myPrint(item['status'])
                # self.myPrint(item['files'][0]['path'])
            self.removeSuperfluous(newGids = activeGids, status = 'active')     #删除多余任务
        #对waiting队列进行处理,分别进入waiting等待队列和paused暂停队列
        waitingData = self.produceJson(method = self.ARIA2METHOD['tellWaiting'],params=[0, 2000])
        waitingResult = self.performan(data = waitingData)   #执行添加操作得到返回结果
        if 'ResultError' in waitingResult:
            return waitingResult
        else:
            waitingGids = []
            pausedGids = []
            for item in waitingResult:
                gid = item['gid']
                if item['status'] == 'waiting':
                    waitingGids.append(gid)
                    self.setAttribute(item, gid, 'waiting')
                elif item['status'] == 'paused':
                    pausedGids.append(gid)
                    self.setAttribute(item, gid, 'paused')  # 添加或修正mission字典中的任务信息
                # self.myPrint(item['status'])
                # self.myPrint(item['files'][0]['path'])
            self.removeSuperfluous(newGids = waitingGids, status = 'waiting')     #删除多余任务
            self.removeSuperfluous(newGids = pausedGids, status = 'paused')     #删除多余任务
        #对stopped队列进行处理
        stoppedData = self.produceJson(method = self.ARIA2METHOD['tellStopped'],params=[0, 2000])
        stoppedResult = self.performan(data = stoppedData)   #执行添加操作得到返回结果
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
                    self.setAttribute(item, gid, 'completed')
                elif item['status'] == 'error':
                    errorGids.append(gid)
                    self.setAttribute(item, gid, 'error')   # 添加或修正mission字典中的任务信息
                # self.myPrint(item['status'])
                # self.myPrint(item['files'][0]['path'])
            self.removeSuperfluous(newGids = completedGids, status = 'completed')     #删除多余任务
            self.removeSuperfluous(newGids = errorGids, status = 'error')     #删除多余任务
        # print(len(self.missions['active'])+len(self.missions['waiting'])+len(self.missions['paused'])+len(self.missions['completed'])+len(self.missions['error']))
        self._merge_followed_tasks()
        self.missionNames.sync(gid for group in self.missions.values() for gid in group)
        return self.missions

    def _merge_followed_tasks(self):
        """Use aria2's parent/child relation to display a torrent as one task."""
        by_gid = {gid: (status, task) for status, group in self.missions.items()
                  for gid, task in group.items()}
        for gid, (status, task) in list(by_gid.items()):
            parent = task.get('following')
            if parent and parent in by_gid:
                parent_status, parent_task = by_gid[parent]
                task['url'] = parent_task.get('url') or task['url']
                if not task['filename']:
                    task['filename'] = parent_task['filename']
                self.missions[parent_status].pop(parent, None)
        for gid, (status, task) in by_gid.items():
            if task.get('followedBy'):
                self.missions[status].pop(gid, None)

    def getMissionFromAria2(self, gid:str) -> dict:
        jsonData = self.produceJson(method = self.ARIA2METHOD['getFiles'], params=[gid])
        result = self.performan(data=jsonData)   #执行添加操作得到返回结果
        return result

    def updateMissionsFromAria2(self, neededStatus:list) -> dict:
        #对于不同页面有不同neddedStatus需要，精简获取信息加速程序运行，属于信息内容小更新
        for status in neededStatus:
            for gid in self.missions[status]:
                jsonData = self.produceJson(method = self.ARIA2METHOD['tellStatus'], params=[gid, self.missionStatusList])
                result = self.performan(data=jsonData)   #执行添加操作得到返回结果
                if 'ResultError' in result:
                    return result
                for item in self.missionStatusList:
                    #按照missionStatusList的内容['totalLength','completedLength','downloadSpeed']逐一更新状态
                    self.missions[status][gid][item] = result[item]
        return self.missions

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
        jsonData = self.produceJson(method = self.ARIA2METHOD['getVersion'])
        result = self.performan(data=jsonData)   #执行添加操作得到返回结果
        if 'version' in result:
            return result['version']
        else:       #先回复一个好久不更新版本代替下
            return '1.36.0'

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
            magnet_name = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get('dn', [])
            if magnet_name:
                return magnet_name[0], True
            return item.get('infoHash', '正在获取 BT 元数据'), False
        if first.get('path'):
            return urllib.parse.unquote(Path(first['path']).name), True
        name = self.splitUrlToName(first.get('path') or url)
        return urllib.parse.unquote(name) or '正在获取文件名', False

    def splitUrlToName(self, url:str) -> str:
        #从url中提取文件名
        string = url.split('?', 1)[0]
        string = string.split('/')[-1]
        string = string.split('[METADATA]')[-1]
        return string

    def setAttribute(self, item:dict, gid:str, status:str) -> None: # 添加或修正mission字典中的任务信息
        first = (item.get('files') or [{}])[0]
        uris = first.get('uris') or []
        source_url = uris[0].get('uri', '') if uris else ''
        isTorrent = 'bittorrent' in item or bool(item.get('infoHash'))
        url = ('magnet:?xt=urn:btih:' + item['infoHash']) if item.get('infoHash') else source_url
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

    def removeSuperfluous(self, newGids:set, status:str) -> None:
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

    def delRemoveMission(self, gid:str, delFile:bool=False) -> dict:
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
                jsonData = self.produceJson(method = self.ARIA2METHOD['remove'], params=[gid])
                result = self.performan(data=jsonData)   #执行添加操作得到返回结果
                if 'ResultError' in result:
                    return result       #若报错直接返回错误
                # 这段有点迷惑 elif mission['status'] == 'completed' or mission['status'] == 'error' or mission['status'] == 'removed':这段有点迷惑
            time.sleep(0.1)

            # 具体删除任务removes a completed/error/removed download
            jsonData = self.produceJson(method = self.ARIA2METHOD['removeResult'], params=[gid])
            result = self.performan(data=jsonData)   #执行添加操作得到返回结果
            if 'ResultError' in result:
                return result       #若报错直接返回错误

            if delFile:
                try:
                    self._delete_task_files(mission)
                except (OSError, ValueError) as exc:
                    return {'ResultError': str(exc)}
            return {}

    def _delete_task_files(self, mission):
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
            platformSystem = self.PlatformSystem
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
        jsonData = self.produceJson(method = self.ARIA2METHOD['getGlobalOption'])
        result = self.performan(data=jsonData)   #执行添加操作得到返回结果
        return result

    def setGlobalConfig(self, conf:dict=None) -> dict:
        jsonData = self.produceJson(method = self.ARIA2METHOD['changeGlobalOption'], params = [conf])
        result = self.performan(data=jsonData)   #执行添加操作得到返回结果
        if result == 'OK':
            return {}       #设置成功返回空字典表示0
        else:
            return result   #设置失败返回带错误字典

    def produceJson(self, method:str, params:list=None) -> str:
        #生成json格式数据
        data = json.dumps({'jsonrpc' : '2.0', 'id' : 'qwer', 'method' : method, 'params' : params or []})
        return data

    def performan(self, data:str='{}') -> dict:
        payload = json.loads(data)
        if self.rpc_secret:
            payload['params'].insert(0, 'token:' + self.rpc_secret)
        url = f'http://127.0.0.1:{self.rpc_port}/jsonrpc'
        try:
            request = urllib.request.Request(url, json.dumps(payload).encode('utf-8'),
                                             {'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=self.TIMEOUTSED) as response:
                result = json.load(response)
            if 'error' in result:
                return {'ResultError': result['error'].get('message', 'aria2 RPC 错误')}
            return result['result']
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
            return {'ResultError': str(exc)}

    def loadConfig(self, BASEPATH:str=None) -> str:
        return str(self.conf_path)

    def isAria2Installed(self) -> bool:
        return shutil.which('aria2c') is not None

    def isAria2rpcRunning(self) -> bool:
        return 'ResultError' not in self.getGlobalStatus()

    def myPrint(self, data, end=None):
        # getattr 函数判断第一参数中是否含有第二参数这个属性：有则返回True，若没有：当第三参数为空时返回error，第三参数存在则返回第三参数
        if not self.isRelease:
            #当程序处于coding阶段时允许输出，当为release时禁止输出
                print(data, end=end)

    def saveSession(self):
        jsonData = self.produceJson(method = self.ARIA2METHOD['saveSession'])
        saveResult = self.performan(data=jsonData)   #执行添加操作得到返回结果
        if saveResult == 'OK':
            return {}       #设置成功返回空字典表示0
        else:
            return saveResult   #设置失败返回带错误字典

    def startAria2(self, BASEPATH:str) -> None:
        executable = shutil.which('aria2c')
        if not executable:
            raise RuntimeError('未检测到 aria2c。请先安装 aria2，再启动 Ashore。')
        self._read_rpc_options()
        with open(CONFIG_DIR / 'aria2-startup.log', 'ab') as log:
            self.process = subprocess.Popen([executable, f'--conf-path={self.conf_path}'],
                                            stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.isAria2rpcRunning():
                return
            if self.process.poll() is not None:
                break
            time.sleep(0.25)
        if self.process.poll() is None:
            self.killAria2()
        raise RuntimeError(f'aria2 RPC 未能在端口 {self.rpc_port} 启动。请检查 {CONFIG_DIR / "aria2-startup.log"} 和 aria2.conf。')

    def restartAria2(self, BASEPATH:str):
        if self.process is None or self.process.poll() is not None:
            raise RuntimeError('当前 aria2 不是由 Ashore 启动，不能替你重启其他进程。')
        self.saveSession()
        self.killAria2()
        self.startAria2(BASEPATH)

    def killAria2(self) -> bool:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process = None
        return True

    def mainKillAria2(self) -> bool:
        """结束主程序时运行,通过self.QuitWithAria2自行判断是否在关闭程序时结束aria2
        """
        if self.QuitWithAria2:
            return self.killAria2()
        else:
            return True
