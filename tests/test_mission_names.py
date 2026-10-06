import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.aria2Client import Aria2Client
from core.missionNames import MissionNames


class MissionNamesTests(unittest.TestCase):
    def test_failed_poll_preserves_names_on_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'names.json'
            client = Aria2Client.__new__(Aria2Client)
            client.missionNames = MissionNames(path)
            client.missions = {key: {} for key in ('active', 'waiting', 'paused', 'completed', 'error')}
            active = {'gid': 'gid', 'status': 'active',
                      'files': [{'path': '/downloads/已知名称.pdf'}]}
            with patch.object(client, 'getGlobalStatus', return_value={'downloadSpeed': '0'}), \
                 patch.object(client, 'call', side_effect=[[active], [], []]):
                self.assertEqual(client.getMissions()['active']['gid']['filename'], '已知名称.pdf')
            with patch.object(client, 'getGlobalStatus', return_value={'ResultError': '断线'}):
                self.assertIn('ResultError', client.getMissions())
            self.assertEqual(MissionNames(path).names, {'gid': '已知名称.pdf'})

    def test_name_survives_restart_and_new_metadata_replaces_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'names.json'
            client = Aria2Client.__new__(Aria2Client)
            client.missions = {key: {} for key in ('active', 'waiting', 'paused', 'completed', 'error')}
            client.missionNames = MissionNames(path)
            client.updateMission({'files': [{'path': '/downloads/真实文件.mkv'}]}, 'gid', 'active')
            client.missionNames.sync(['gid'])

            restarted = Aria2Client.__new__(Aria2Client)
            restarted.missions = {key: {} for key in client.missions}
            restarted.missionNames = MissionNames(path)
            restarted.updateMission({'files': [{'uris': [{'uri': 'https://example.org/fallback'}]}]}, 'gid', 'active')
            self.assertEqual(restarted.missions['active']['gid']['filename'], '真实文件.mkv')
            restarted.updateMission({'files': [{'path': '/downloads/更新的名字.mp4'}]}, 'gid', 'active')
            self.assertEqual(restarted.missions['active']['gid']['filename'], '更新的名字.mp4')
            restarted.missionNames.sync(['gid'])
            self.assertEqual(MissionNames(path).names, {'gid': '更新的名字.mp4'})
            restarted.missionNames.sync([])
            self.assertEqual(MissionNames(path).names, {})

    def test_magnet_display_name_waits_for_real_metadata(self):
        client = Aria2Client.__new__(Aria2Client)
        with tempfile.TemporaryDirectory() as folder:
            client.missionNames = MissionNames(Path(folder) / 'names.json')
            client.missions = {'active': {}}
            magnet = 'magnet:?xt=urn:btih:abc&dn=暂定名称'
            client.updateMission({'infoHash': 'abc', 'files': [{'uris': [{'uri': magnet}]}]}, 'gid', 'active')
            self.assertEqual(client.missions['active']['gid']['filename'], '暂定名称')
            client.updateMission({'infoHash': 'abc', 'files': []}, 'gid', 'active')
            self.assertEqual(client.missions['active']['gid']['filename'], '暂定名称')
            client.updateMission({'infoHash': 'abc', 'bittorrent': {'info': {'name': '真实名称'}},
                                 'files': []}, 'gid', 'active')
            self.assertEqual(client.missions['active']['gid']['filename'], '真实名称')


if __name__ == '__main__':
    unittest.main()
