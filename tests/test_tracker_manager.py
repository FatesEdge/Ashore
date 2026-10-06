import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.configStore import readAshore, readOptions
from core.trackerManager import TrackerManager, displayTime, isoNow, updateDue


class TrackerManagerTests(unittest.TestCase):
    def test_recent_success_is_not_due_and_old_success_is_due(self):
        self.assertFalse(updateDue(isoNow()))
        old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        self.assertTrue(updateDue(old))
        self.assertTrue(updateDue(''))
        self.assertTrue(updateDue('尚未更新'))
        self.assertEqual(displayTime(''), '')

    def test_first_run_updates_even_when_automatic_refresh_is_disabled(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ashore = root / 'ashore.conf'
            aria2 = root / 'aria2.conf'
            ashore.write_text('[global]\ntrackers_auto_update=false\ntrackers_list_time=\n', encoding='utf-8')
            aria2.write_text('bt-tracker=\n', encoding='utf-8')
            self.assertTrue(TrackerManager(ashore, aria2).shouldUpdate())

    def test_success_is_saved_immediately_and_failure_preserves_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ashore = root / 'ashore.conf'
            aria2 = root / 'aria2.conf'
            ashore.write_text('[global]\ntrackers_auto_update=true\ntrackers_list_time=\ntrackers_list_source=\n', encoding='utf-8')
            aria2.write_text('# tracker\nbt-tracker=udp://old.example/announce\n', encoding='utf-8')
            manager = TrackerManager(ashore, aria2)
            manager.finish(['udp://new.example/announce'], ['https://source.example/list.txt'])
            self.assertEqual(readOptions(aria2)['bt-tracker'], 'udp://new.example/announce')
            saved = readAshore(ashore)
            self.assertEqual(json.loads(saved['trackers_list_source']), ['https://source.example/list.txt'])
            timestamp = saved['trackers_list_time']
            manager.finish([], 'timeout')
            self.assertEqual(readOptions(aria2)['bt-tracker'], 'udp://new.example/announce')
            self.assertEqual(readAshore(ashore)['trackers_list_time'], timestamp)


if __name__ == '__main__':
    unittest.main()
