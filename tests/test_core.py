import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aria2Operate import Aria2Operate
import paths


class Aria2Tests(unittest.TestCase):
    def test_first_run_config_has_secret_and_is_persistent(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(paths, 'CONFIG_DIR', Path(folder)):
                conf = paths.ensure_config('aria2.conf')
                first = conf.read_text(encoding='utf-8')
                self.assertIn('rpc-secret=', first)
                self.assertEqual(conf.stat().st_mode & 0o777, 0o600)
                self.assertEqual(paths.ensure_config('aria2.conf').read_text(encoding='utf-8'), first)

    def test_missing_aria2_exits_with_clear_error(self):
        with tempfile.TemporaryDirectory() as folder:
            conf = Path(folder) / 'aria2.conf'
            conf.write_text('rpc-listen-port=6801\n', encoding='utf-8')
            with patch('aria2Operate.ensure_config', return_value=conf), \
                 patch.object(Aria2Operate, 'getGlobalStatus', return_value={'ResultError': 'offline'}), \
                 patch('aria2Operate.shutil.which', return_value=None):
                with self.assertRaisesRegex(RuntimeError, 'aria2c'):
                    Aria2Operate()

    def test_rpc_uses_configured_port_and_secret_and_returns_rpc_error(self):
        client = Aria2Operate.__new__(Aria2Operate)
        client.rpc_port = 6808
        client.rpc_secret = 'private-token'

        class Reply:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def read(self):
                return b'{"jsonrpc":"2.0","error":{"message":"denied"}}'

        with patch('aria2Operate.urllib.request.urlopen', return_value=Reply()) as call:
            result = client.performan(data=client.produceJson('aria2.getVersion'))
        self.assertEqual(result, {'ResultError': 'denied'})
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:6808/jsonrpc')
        self.assertEqual(json.loads(request.data)['params'], ['token:private-token'])

    def test_parent_torrent_and_payload_display_as_one(self):
        client = Aria2Operate.__new__(Aria2Operate)
        client.missions = {key: {} for key in ('active', 'waiting', 'paused', 'completed', 'error')}
        client.missions['completed']['parent'] = {'url': 'https://example.org/a.torrent', 'filename': 'a.torrent', 'followedBy': ['child']}
        client.missions['active']['child'] = {'following': 'parent', 'url': 'magnet:?xt=urn:btih:abc', 'filename': 'payload'}
        client._merge_followed_tasks()
        self.assertEqual(client.missions['completed'], {})
        self.assertEqual(client.missions['active']['child']['url'], 'https://example.org/a.torrent')

    def test_local_torrent_uses_add_torrent(self):
        client = Aria2Operate.__new__(Aria2Operate)
        with tempfile.TemporaryDirectory() as folder:
            torrent = Path(folder) / 'a.torrent'
            torrent.write_bytes(b'torrent bytes')
            with patch.object(client, 'performan', return_value='gid') as call:
                client.addUrl(str(torrent), folder)
            payload = json.loads(call.call_args.kwargs['data'])
            self.assertEqual(payload['method'], 'aria2.addTorrent')
            self.assertEqual(payload['params'][2]['dir'], folder)

    def test_deletion_only_removes_listed_download_files(self):
        client = Aria2Operate.__new__(Aria2Operate)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'My download' / 'part.bin'
            target.parent.mkdir()
            target.write_bytes(b'payload')
            other = root / 'keep.txt'
            other.write_bytes(b'keep')
            client._delete_task_files({'dir': folder, 'filename': 'My download', 'files': [str(target)]})
            self.assertFalse(target.exists())
            self.assertTrue(other.exists())
            with self.assertRaisesRegex(ValueError, '拒绝删除'):
                client._delete_task_files({'dir': folder, 'filename': '', 'files': [str(root.parent / 'outside')]})


if __name__ == '__main__':
    unittest.main()
