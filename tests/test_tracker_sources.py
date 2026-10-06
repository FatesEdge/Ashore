import unittest
from unittest.mock import patch

from core.trackerSources import fetchTrackers, parseTrackers, sourceUrls


class TrackerSourceTests(unittest.TestCase):
    def test_rejects_page_content_and_deduplicates_valid_addresses(self):
        self.assertEqual(parseTrackers('<html>down</html>'), [])
        self.assertEqual(
            parseTrackers(
                'udp://host:80/announce\n'
                'https://example.org/announce,udp://host:80/announce'),
            ['udp://host:80/announce', 'https://example.org/announce'])

    def test_selected_and_custom_sources_are_resolved_without_duplicates(self):
        urls = sourceUrls(
            ['ngosang'],
            [
                {'url': 'https://custom.example/list.txt', 'enabled': True},
                {'url': 'https://disabled.example/list.txt', 'enabled': False},
            ])
        self.assertEqual(len(urls), 2)
        self.assertIn('https://custom.example/list.txt', urls)
        self.assertNotIn('https://disabled.example/list.txt', urls)
        self.assertEqual(sourceUrls([], []), [])

    def test_multiple_sources_merge_and_deduplicate(self):
        class Response:
            def __init__(self, data):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def read(self):
                return self.data

        sources = ['https://a.example/list', 'https://b.example/list']
        with patch(
                'core.trackerSources.urllib.request.urlopen',
                side_effect=[
                    Response(b'udp://one.example:80/announce\n'
                             b'https://same.example/announce'),
                    Response(b'https://same.example/announce\n'
                             b'udp://two.example:80/announce'),
                ]):
            trackers, successful = fetchTrackers(sources)

        self.assertEqual(
            trackers,
            [
                'udp://one.example:80/announce',
                'https://same.example/announce',
                'udp://two.example:80/announce',
            ])
        self.assertEqual(successful, sources)


if __name__ == '__main__':
    unittest.main()
