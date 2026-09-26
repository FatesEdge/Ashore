import unittest
from unittest.mock import patch

from core.trackerSources import fetchTrackers, parseTrackers


class TrackerSourceTests(unittest.TestCase):
    def test_rejects_page_content_and_deduplicates_valid_addresses(self):
        self.assertEqual(parseTrackers('<html>down</html>'), [])
        self.assertEqual(parseTrackers('udp://host:80/announce\nhttps://example.org/announce,udp://host:80/announce'),
                         ['udp://host:80/announce', 'https://example.org/announce'])

    def test_invalid_source_falls_back_and_reports_actual_source(self):
        class Response:
            def __init__(self, data):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def read(self):
                return self.data

        with patch('core.trackerSources.TRACKER_SOURCES', ('https://a.example/list', 'https://b.example/list')), \
             patch('core.trackerSources.urllib.request.urlopen', side_effect=[Response(b'<html/>'),
                                                                    Response(b'udp://host:80/announce')]):
            self.assertEqual(fetchTrackers(), (['udp://host:80/announce'], 'https://b.example/list'))


if __name__ == '__main__':
    unittest.main()
