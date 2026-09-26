import unittest

from fileIcons import iconForFile


class FileIconTests(unittest.TestCase):
    def test_extension_matches_bundled_icons(self):
        self.assertEqual(iconForFile('Movie.MKV'), 'mkv')
        self.assertEqual(iconForFile('photo.PNG'), 'png')
        self.assertEqual(iconForFile('image.JPEG'), 'jpg')
        self.assertEqual(iconForFile('scan.TIF'), 'tiff')
        self.assertEqual(iconForFile('unknown.zzz', True), 'bt')
        self.assertEqual(iconForFile('unknown.zzz'), 'paper')


if __name__ == '__main__':
    unittest.main()
