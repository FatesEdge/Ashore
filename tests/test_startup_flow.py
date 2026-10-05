import os
import unittest
from unittest.mock import Mock, patch

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from Ashore import Ashore, AshoreApplication, StartupController, configureApplication
from interface.startupWindow import ExitWindow, StartupWindow
from paths import RESOURCE_DIR


class StartupFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or AshoreApplication([])

    def test_application_identity_is_stable(self):
        configureApplication()
        self.assertEqual(QCoreApplication.applicationName(), 'Ashore')
        self.assertEqual(self.app.desktopFileName(), 'ashore')

    def test_splash_reports_only_after_its_first_paint(self):
        splash = StartupWindow(RESOURCE_DIR / 'static/img/cover.png')
        painted = Mock()
        splash.firstPainted.connect(painted)
        self.assertFalse(splash.hasPainted)
        splash.show()
        self.app.processEvents()
        self.app.processEvents()
        self.assertTrue(splash.hasPainted)
        painted.assert_called_once_with()
        splash.close()

    def test_startup_requires_snapshot_and_tracker_before_finish(self):
        controller = StartupController(self.app, ['Ashore.py'])
        controller.MIN_VISIBLE_MS = 0
        controller.window = object()
        controller.clock.start()
        controller.finish = Mock()

        controller.trackerReady = True
        controller.tryFinish()
        controller.finish.assert_not_called()

        controller.firstSnapshotReady = True
        controller.tryFinish()
        controller.finish.assert_called_once_with()

    def test_runtime_services_wait_for_main_window_first_paint(self):
        controller = StartupController(self.app, ['Ashore.py'])
        controller.window = Mock()
        controller.window.showTray = Mock()
        controller.window.offerDownloadMigration = Mock()

        controller.mainPainted()
        self.app.processEvents()

        controller.window.showTray.assert_called_once_with()

    def test_tray_action_runs_after_popup_closes(self):
        window = Mock()
        callback = Mock()

        with patch('Ashore.QTimer.singleShot') as singleShot:
            Ashore.deferTrayAction(window, callback)

        window.trayMenu.close.assert_called_once_with()
        singleShot.assert_called_once_with(0, callback)

    def test_lifecycle_window_ready_requires_activation_and_paint(self):
        window = ExitWindow(
            RESOURCE_DIR / 'static/icon/functionIcons/icon0.png', 'Exiting')
        ready = Mock()
        window.ready.connect(ready)

        window.hasActivated = True
        window.checkReady()
        self.app.processEvents()
        ready.assert_not_called()

        window.hasPainted = True
        window.checkReady()
        self.app.processEvents()
        ready.assert_called_once_with()
        window.close()

    def test_tray_quit_uses_exit_window(self):
        window = Mock()
        window.quitting = False
        window.exitWindow = None
        window.resourcePath = str(RESOURCE_DIR) + '/'
        window.tr.return_value = 'Exiting'
        exitWindow = Mock()

        with patch('Ashore.ExitWindow', return_value=exitWindow) as factory:
            Ashore.requestTrayQuit(window)

        factory.assert_called_once_with(
            str(RESOURCE_DIR) + '/static/icon/functionIcons/icon0.png', 'Exiting')
        exitWindow.ready.connect.assert_called_once_with(window.slotQuit)
        exitWindow.showActive.assert_called_once_with()
        self.assertIs(window.exitWindow, exitWindow)

if __name__ == '__main__':
    unittest.main()
