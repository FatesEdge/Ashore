import unittest

from interface.fileIcons import fileIconSpec


class FileIconTests(unittest.TestCase):
    def test_family_and_format_are_classified_independently(self):
        self.assertEqual((fileIconSpec('Movie.MKV').family, fileIconSpec('Movie.MKV').label), ('video', 'MKV'))
        self.assertEqual((fileIconSpec('photo.JPEG').family, fileIconSpec('photo.JPEG').label), ('image', 'JPEG'))
        self.assertEqual((fileIconSpec('backup.tar.gz').family, fileIconSpec('backup.tar.gz').label), ('archive', 'TGZ'))
        self.assertEqual((fileIconSpec('main.cpp').family, fileIconSpec('main.cpp').label), ('code', 'CPP'))

    def test_known_torrent_payload_keeps_its_file_family(self):
        self.assertEqual(fileIconSpec('Movie.MKV', True).family, 'video')

    def test_unknown_and_torrent_have_stable_fallbacks(self):
        generic = fileIconSpec('unknown.zzz')
        self.assertEqual((generic.family, generic.label), ('generic', 'ZZZ'))
        torrent = fileIconSpec('unknown.zzz', True)
        self.assertEqual((torrent.family, torrent.label), ('torrent', 'BT'))


if __name__ == '__main__':
    unittest.main()
