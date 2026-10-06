import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import QRectF
from PyQt6.QtWidgets import QApplication

from interface.fileIcons import TILE_HEIGHT, TILE_WIDTH, fileIconPixmap, fileIconSpec, fitSvgRect, iconColorForStatus, statusHasErrorBadge


class FileIconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_family_and_format_are_classified_independently(self):
        self.assertEqual((fileIconSpec('Movie.MKV').family, fileIconSpec('Movie.MKV').label), ('video', 'MKV'))
        self.assertEqual((fileIconSpec('photo.JPEG').family, fileIconSpec('photo.JPEG').label), ('image', 'JPEG'))
        self.assertEqual((fileIconSpec('backup.tar.gz').family, fileIconSpec('backup.tar.gz').label), ('archive', 'TGZ'))
        self.assertEqual((fileIconSpec('main.cpp').family, fileIconSpec('main.cpp').label), ('code', 'CPP'))

    def test_known_torrent_payload_keeps_its_file_family(self):
        self.assertEqual(fileIconSpec('Movie.MKV', True).family, 'video')

    def test_video_and_torrent_use_requested_release_colors(self):
        self.assertEqual(fileIconSpec('Movie.MKV').color, '#8b5cf6')
        self.assertEqual(fileIconSpec('download.torrent').color, '#38a9e8')

    def test_unknown_and_torrent_have_stable_fallbacks(self):
        generic = fileIconSpec('unknown.zzz')
        self.assertEqual((generic.family, generic.label), ('generic', 'ZZZ'))
        torrent = fileIconSpec('unknown.zzz', True)
        self.assertEqual((torrent.family, torrent.label), ('torrent', 'BT'))

    def test_download_status_changes_icon_treatment_without_duplicate_assets(self):
        base = fileIconSpec('Movie.MKV').color
        self.assertEqual(iconColorForStatus(base, 'active').name(), base)
        self.assertEqual(iconColorForStatus(base, 'completed').name(), base)
        paused = iconColorForStatus(base, 'paused')
        self.assertEqual(paused.red(), paused.green())
        self.assertEqual(paused.green(), paused.blue())
        self.assertNotEqual(iconColorForStatus(base, 'waiting').name(), base)
        self.assertTrue(statusHasErrorBadge('error'))
        self.assertFalse(statusHasErrorBadge('paused'))

    def test_svg_glyph_fit_preserves_viewbox_aspect_ratio(self):
        class Renderer:
            @staticmethod
            def viewBoxF():
                return QRectF(0, 0, 40, 20)

        fitted = fitSvgRect(Renderer(), QRectF(0, 0, 30, 30))
        self.assertAlmostEqual(fitted.width() / fitted.height(), 2.0)
        self.assertLessEqual(fitted.width(), 30)
        self.assertLessEqual(fitted.height(), 30)


    def test_file_tile_is_drawn_as_portrait_geometry(self):
        self.assertLess(TILE_WIDTH, TILE_HEIGHT)
        pixmap = fileIconPixmap('ubuntu.iso', status='paused')
        self.assertEqual(pixmap.width(), TILE_WIDTH)
        self.assertEqual(pixmap.height(), TILE_HEIGHT)
        self.assertEqual((TILE_WIDTH, TILE_HEIGHT), (44, 56))



if __name__ == '__main__':
    unittest.main()
