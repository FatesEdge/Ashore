import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PyQt6.QtWidgets import QApplication

import paths
from core.fileOperations import deleteTaskFiles
from core.aria2Client import Aria2Client
from core.downloadRequest import DownloadItem, DownloadRequest, ITEM_LOCAL_TORRENT, ITEM_MAGNET, ITEM_NETWORK
from core.aria2Service import Aria2Poller, Aria2Service, Aria2Shutdown
from core.trackerSources import parseTrackers
from interface.settingPage import SettingPage


class Aria2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def test_tracker_response_requires_announce_urls(self):
        self.assertEqual(parseTrackers('<html>down</html>'), [])
        self.assertEqual(parseTrackers('udp://host:80/announce\n\nhttps://example.org/announce,udp://host:80/announce'),
                         ['udp://host:80/announce', 'https://example.org/announce'])

    def test_settings_page_reloads_saved_tracker_date(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(paths, 'CONFIG_DIR', Path(folder)), \
                 patch.object(SettingPage, 'ashoreConfDir', folder):
                page = SettingPage()
                page.saveAshoreConf({'trackers_list_time': '2026.09.26 16:55',
                                     'quit_with_aria2': 'false', 'update_interval': '2000',
                                     'rpc_port_changeable': 'false'})
                page.AshoreConfig = {'trackers_list_time': '2023.04.01 11:03'}
                with patch.object(page, 'loadAria2'):
                    page.loadSettings({})
                self.assertIn('2026.09.26 16:55', page.trackerInfo.text())

    def test_user_agent_presets_are_full_and_custom_value_is_allowed(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(paths, 'CONFIG_DIR', Path(folder)), \
                 patch.object(SettingPage, 'ashoreConfDir', folder):
                page = SettingPage()
                presets = page.ashoreConfig['user_agent_presets']
                self.assertGreaterEqual(len(presets), 5)
                self.assertTrue(all(item.startswith('Mozilla/5.0 (') for item in presets))
                self.assertTrue(page.userAgentComboBox.isEditable())
                page.userAgentComboBox.setCurrentText('Custom Agent/1.0')
                self.assertEqual(page.userAgentComboBox.currentText(), 'Custom Agent/1.0')

    def test_tray_icon_style_has_colorful_and_gray_choices(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(paths, 'CONFIG_DIR', Path(folder)), \
                 patch.object(SettingPage, 'ashoreConfDir', folder):
                page = SettingPage()
                choices = {page.trayIconStyleComboBox.itemData(index)
                           for index in range(page.trayIconStyleComboBox.count())}
                self.assertEqual(choices, {'colorful', 'gray'})

    def test_first_run_rpc_is_local_and_has_no_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(paths, 'CONFIG_DIR', Path(folder)):
                conf = paths.ensureConfig('aria2.conf')
                first = conf.read_text(encoding='utf-8')
                self.assertIn('rpc-listen-all=false', first)
                self.assertNotIn('\nrpc-secret=', first)
                self.assertEqual(conf.stat().st_mode & 0o777, 0o600)
                self.assertEqual(paths.ensureConfig('aria2.conf').read_text(encoding='utf-8'), first)

    def test_external_rpc_token_is_generated_readonly_and_removable(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        self.app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(paths, 'CONFIG_DIR', root), \
                 patch.object(SettingPage, 'ashoreConfDir', folder), \
                 patch.object(SettingPage, 'aria2ConfPath', str(root / 'aria2.conf')):
                conf = paths.ensureConfig('aria2.conf')
                page = SettingPage()
                page.rpcListenAllComboBox.setCurrentIndex(0)
                token = page.rpcSecret
                self.assertGreater(len(token), 30)
                self.assertTrue(page.rpcSecretLineEdit.isReadOnly())
                self.assertEqual(page.rpcSecretLineEdit.text(), '●' * 12)
                self.assertEqual(page.saveAria2Conf(
                    {'rpc-listen-all': 'true', 'rpc-secret': token}), 0)
                self.assertIn(f'rpc-secret={token}', conf.read_text(encoding='utf-8'))
                self.assertEqual(page.saveAria2Conf(
                    {'rpc-listen-all': 'false'}, {'rpc-secret'}), 0)
                self.assertNotIn(f'rpc-secret={token}', conf.read_text(encoding='utf-8'))

    def test_missing_aria2_returns_recovery_issue(self):
        with patch('core.aria2Service.Aria2Client') as clientType, \
             patch('core.aria2Service.shutil.which', return_value=None):
            clientType.return_value.isRpcReady.return_value = False
            service = Aria2Service()
            issue = service.ensureReady()

        self.assertEqual(issue.code, 'aria2_missing')
        self.assertTrue(issue.installCommand)

    def test_rpc_uses_configured_port_and_secret_and_returns_rpc_error(self):
        client = Aria2Client.__new__(Aria2Client)
        client.rpcPort = 6808
        client.rpcSecret = 'private-token'

        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def read(self):
                return b'{"jsonrpc":"2.0","error":{"message":"denied"}}'

        with patch('core.aria2Client.urllib.request.urlopen', return_value=Reply()) as call:
            result = client.call(data=client.makeRequest('aria2.getVersion'))
        self.assertEqual(result, {'ResultError': 'denied'})
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:6808/jsonrpc')
        self.assertEqual(json.loads(request.data)['params'], ['token:private-token'])

    def test_restart_gracefully_takes_over_external_aria2(self):
        client = Aria2Client.__new__(Aria2Client)
        service = Aria2Service.__new__(Aria2Service)
        service.client = client
        service.process = None
        with patch.object(client, 'saveSession', return_value={}), \
             patch.object(client, 'call', return_value='OK') as rpc, \
             patch.object(client, 'isRpcReady', return_value=False), \
             patch.object(service, 'start', return_value=None) as start:
            service.restart()
        payload = json.loads(rpc.call_args.args[0])
        self.assertEqual(payload['method'], 'aria2.shutdown')
        start.assert_called_once_with()

    def test_poller_fetches_version_with_the_background_snapshot(self):
        class Client:
            def __init__(self):
                self.lastPollGlobalStatus = {
                    'downloadSpeed': '0', 'uploadSpeed': '0'}

            def getMissions(self):
                return {'active': {}, 'waiting': {}, 'paused': {},
                        'completed': {}, 'error': {}}

            def getAria2Version(self):
                return '1.37.0'

        poller = Aria2Poller(Client())
        poller.timer.stop()
        snapshots = []
        poller.updated.connect(snapshots.append)
        poller.run()
        self.assertEqual(snapshots[0]['aria2Version'], '1.37.0')

    def test_shutdown_waits_and_closes_outside_the_window(self):
        service = Mock()
        poller = Mock()
        shutdown = Aria2Shutdown(service, poller)

        shutdown.run()

        poller.wait.assert_called_once_with()
        service.close.assert_called_once_with()

    def test_parent_torrent_and_payload_display_as_one(self):
        client = Aria2Client.__new__(Aria2Client)
        client.missions = {key: {} for key in ('active', 'waiting', 'paused', 'completed', 'error')}
        client.missions['completed']['parent'] = {'url': 'https://example.org/a.torrent', 'filename': 'a.torrent', 'followedBy': ['child']}
        client.missions['active']['child'] = {'following': 'parent', 'url': 'magnet:?xt=urn:btih:abc', 'filename': 'payload'}
        client.mergeFollowedTasks()
        self.assertEqual(client.missions['completed'], {})
        self.assertEqual(client.missions['active']['child']['url'], 'https://example.org/a.torrent')

    def test_local_torrent_uses_add_torrent(self):
        client = Aria2Client.__new__(Aria2Client)
        with tempfile.TemporaryDirectory() as folder:
            torrent = Path(folder) / 'a.torrent'
            torrent.write_bytes(b'torrent bytes')
            with patch.object(client, 'call', return_value='gid') as call:
                client.addUrl(
                    DownloadItem(str(torrent), ITEM_LOCAL_TORRENT), folder)
            payload = json.loads(call.call_args.kwargs['data'])
            self.assertEqual(payload['method'], 'aria2.addTorrent')
            self.assertEqual(payload['params'][2]['dir'], folder)

    def test_per_download_http_options_are_sent_only_to_http_items(self):
        client = Aria2Client.__new__(Aria2Client)
        request = DownloadRequest(
            items=(
                DownloadItem('https://example.org/file.bin', ITEM_NETWORK),
                DownloadItem(
                    'magnet:?xt=urn:btih:0123456789abcdef',
                    ITEM_MAGNET),
            ),
            targetDir='/tmp',
            options={
                'out': 'renamed.bin',
                'referer': 'https://example.org/',
                'user-agent': 'Ashore Test',
                'header': ['X-Test: one', 'Cookie: session=abc'],
                'checksum': 'sha-256=abcd',
            },
        )
        payloads = []

        def capture(data):
            payloads.append(json.loads(data))
            return 'gid'

        with patch.object(client, 'call', side_effect=capture):
            result = client.addUrls(request)

        self.assertEqual(result, {})
        httpOptions = payloads[0]['params'][1]
        self.assertEqual(httpOptions['dir'], '/tmp')
        self.assertEqual(httpOptions['out'], 'renamed.bin')
        self.assertEqual(httpOptions['header'][1], 'Cookie: session=abc')
        magnetOptions = payloads[1]['params'][1]
        self.assertEqual(magnetOptions, {'dir': '/tmp'})


    def test_deletion_only_removes_listed_download_files(self):
        client = Aria2Client.__new__(Aria2Client)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'My download' / 'part.bin'
            target.parent.mkdir()
            target.write_bytes(b'payload')
            other = root / 'keep.txt'
            other.write_bytes(b'keep')
            deleteTaskFiles({'dir': folder, 'filename': 'My download', 'files': [str(target)]})
            self.assertFalse(target.exists())
            self.assertTrue(other.exists())
            with self.assertRaisesRegex(ValueError, '拒绝删除'):
                deleteTaskFiles({'dir': folder, 'filename': '', 'files': [str(root.parent / 'outside')]})

    def test_running_task_removal_waits_for_removed_status_before_cleanup(self):
        client = Aria2Client.__new__(Aria2Client)
        mission = {
            'status': 'active',
            'dir': '/tmp',
            'filename': 'file.bin',
            'files': ['/tmp/file.bin'],
        }
        payloads = []

        def call(data):
            payload = json.loads(data)
            payloads.append(payload)
            method = payload['method']
            if method == 'aria2.remove':
                return 'gid'
            if method == 'aria2.tellStatus':
                return {'status': 'removed'}
            if method == 'aria2.removeDownloadResult':
                return 'OK'
            self.fail(f'unexpected RPC method: {method}')

        with patch.object(client, 'getMission', return_value=mission), \
             patch.object(client, 'call', side_effect=call):
            result = client.removeMission('gid', delFile=False)

        self.assertEqual(result, {})
        self.assertEqual(
            [payload['method'] for payload in payloads],
            [
                'aria2.remove',
                'aria2.tellStatus',
                'aria2.removeDownloadResult',
            ])



if __name__ == '__main__':
    unittest.main()
