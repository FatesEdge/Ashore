import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication, QStackedWidget

import paths
from interface.mainWindow import Ashore
from core.applicationInfo import configureApplication
from core.applicationRuntime import AshoreApplication, StartupController
from core.environmentCheck import makeEnvironmentIssue
from interface.startupWindow import RecoveryWindow
from interface.settingPage import SettingPage
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
        controller = StartupController(self.app, ['Ashore.py'], Ashore)
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
        controller = StartupController(self.app, ['Ashore.py'], Ashore)
        controller.window = Mock()
        controller.window.showTray = Mock()
        controller.window.offerDownloadMigration = Mock()

        controller.mainPainted()
        self.app.processEvents()

        controller.window.showTray.assert_called_once_with()

    def test_main_window_uses_widget_page_stack(self):
        service = Mock()
        service.client.rpcPort = 6800
        events = Mock()
        events.state = 'unavailable'
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(paths, 'CONFIG_DIR', Path(folder)), \
             patch.object(SettingPage, 'ashoreConfDir', folder), \
             patch.object(SettingPage, 'aria2ConfPath', str(Path(folder) / 'aria2.conf')), \
             patch('interface.mainWindow.Aria2Events', return_value=events):
            window = Ashore(service, Mock())

        self.assertIsInstance(window.pageStack, QStackedWidget)
        self.assertEqual(window.pageStack.count(), 3)
        self.assertTrue(window.titleBar.property('titleBar'))
        self.assertTrue(
            window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(
            window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(window.windowSurface.property('windowSurface'))
        self.assertTrue(window.pageSurface.property('pageSurface'))
        self.assertTrue(window.pageStack.property('pageStack'))
        self.assertIs(window.moreBtn.menu(), window.moreMenu)
        self.assertIs(window.titleBar.overflowButton.menu(), window.moreMenu)
        self.assertEqual(window.tabDownloading.text(), '')
        self.assertEqual(window.tabDownloaded.text(), '')
        self.assertEqual(window.tabSetting.text(), '')
        self.assertEqual(window.navigationRail.width(), 46)
        self.assertEqual(
            window.navigationRail.layout().contentsMargins().right(), 0)
        self.assertEqual(window.tabDownloading.height(), 52)
        self.assertEqual(window.tabDownloading.iconSize().width(), 32)
        self.assertEqual(window.tabSetting.iconSize().width(), 28)
        self.assertEqual(window.titleBar.height(), 36)
        self.assertEqual(window.titleBar.titleLabel.text(), 'Ashore')
        self.assertFalse(window.titleBar.appIconLabel.pixmap().isNull())
        self.assertEqual(window.titleBar.minimizeButton.width(), 20)
        self.assertEqual(window.titleBar.minimizeButton.height(), 20)
        self.assertTrue(window.statusStrip.property('statusStrip'))
        self.assertEqual(window.statusStrip.height(), 30)
        self.assertTrue(window.aria2StateText.property('statusMetricText'))
        self.assertTrue(window.downSpeedLabel.property('statusMetricText'))
        self.assertTrue(window.upSpeedLabel.property('statusMetricText'))
        self.assertIs(
            window.aria2StateWidget.parentWidget(), window.statusStrip)
        self.assertFalse(window.aria2StateWidget.isHidden())
        window.aria2Poller.timer.stop()
        window.close()

    def test_startup_controller_dispose_breaks_application_cycle(self):
        controller = StartupController(self.app, ['Ashore.py'], Ashore)
        controller.window = None
        controller.recovery = None
        controller.startup = None

        controller.dispose()

        self.assertIsNone(controller.app)
        self.assertIsNone(controller.window)
        self.assertIsNone(controller.themeManager)

    def test_instance_messages_are_queued_until_main_window_is_ready(self):
        app = Mock()
        app.pendingInstanceMessages = []
        app.instanceRoutingReady = False

        AshoreApplication.routeInstanceMessage(
            app, ['magnet:?xt=urn:btih:abc'])
        self.assertEqual(
            app.pendingInstanceMessages,
            [['magnet:?xt=urn:btih:abc']])
        app.instanceMessage.emit.assert_not_called()

        AshoreApplication.enableInstanceRouting(app)
        app.instanceMessage.emit.assert_called_once_with(
            ['magnet:?xt=urn:btih:abc'])
        self.assertEqual(app.pendingInstanceMessages, [])


    def test_tray_action_runs_after_popup_closes(self):
        window = Mock()
        callback = Mock()

        with patch('interface.mainWindow.QTimer.singleShot') as singleShot:
            Ashore.deferTrayAction(window, callback)

        window.trayMenu.close.assert_called_once_with()
        singleShot.assert_called_once_with(0, callback)

    def test_lifecycle_window_ready_requires_activation_and_paint(self):
        window = ExitWindow(
            RESOURCE_DIR / 'static/icon/functionIcons/appIcon.png', 'Exiting')
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

        with patch('interface.mainWindow.ExitWindow', return_value=exitWindow) as factory:
            Ashore.requestTrayQuit(window)

        factory.assert_called_once_with(
            str(RESOURCE_DIR) + '/static/icon/functionIcons/appIcon.png', 'Exiting')
        exitWindow.ready.connect.assert_called_once_with(window.slotQuit)
        exitWindow.showActive.assert_called_once_with()
        self.assertIs(window.exitWindow, exitWindow)
    def test_notification_click_restores_window_and_focuses_task(self):
        window = Mock()
        window.notificationTarget = 'gid'
        window.pageDownloaded.focusSection.return_value = True

        Ashore.slotNotificationClicked(window, 'gid')

        window.slotShowWindow.assert_called_once_with()
        window.pageDownloaded.focusSection.assert_called_once_with('gid')
        window.showCompleted.assert_called_once_with()
        window.pageDownloading.focusSection.assert_not_called()


    def test_aria2_status_visibility_can_change_at_runtime(self):
        service = Mock()
        service.client.rpcPort = 6800
        service.quitWithAshore = False
        events = Mock()
        events.state = 'unavailable'
        theme = Mock()
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(paths, 'CONFIG_DIR', Path(folder)), \
             patch.object(SettingPage, 'ashoreConfDir', folder), \
             patch.object(
                 SettingPage, 'aria2ConfPath',
                 str(Path(folder) / 'aria2.conf')), \
             patch('interface.mainWindow.Aria2Events', return_value=events):
            window = Ashore(service, theme)

        window.applyAshoreConfig({
            'quit_with_aria2': 'false',
            'update_interval': '2000',
            'show_aria2_status': 'false',
            'isSaved': 'saved',
        })
        self.assertFalse(window.aria2StateWidget.isVisible())
        window.aria2Poller.timer.stop()
        window.close()


    def test_recovery_window_shows_system_command_without_main_window(self):
        issue = makeEnvironmentIssue('aria2_missing')
        controller = StartupController(self.app, ['Ashore.py'], Ashore)
        controller.settings = {'language': 'en'}
        controller.splash.close()

        controller.showRecovery(issue)
        self.app.processEvents()

        self.assertIsNone(controller.window)
        self.assertIsInstance(controller.recovery, RecoveryWindow)
        self.assertIn(issue.systemName, controller.recovery.systemLabel.text())
        self.assertIn(
            issue.installCommand,
            controller.recovery.commandBox.toPlainText())
        controller.recovery.close()

    def test_main_status_uses_colored_dot_and_normal_text_separately(self):
        service = Mock()
        service.client.rpcPort = 6800
        service.quitWithAshore = False
        events = Mock()
        events.state = 'unavailable'
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(paths, 'CONFIG_DIR', Path(folder)), \
             patch.object(SettingPage, 'ashoreConfDir', folder), \
             patch.object(
                 SettingPage, 'aria2ConfPath',
                 str(Path(folder) / 'aria2.conf')), \
             patch('interface.mainWindow.Aria2Events', return_value=events):
            window = Ashore(service, Mock())

        window.setMainAria2State('connected')
        dotColor = window.aria2StateDot.palette().color(
            QPalette.ColorRole.WindowText)
        textColor = window.aria2StateText.palette().color(
            QPalette.ColorRole.WindowText)
        self.assertNotEqual(dotColor, textColor)
        self.assertIn('aria2', window.aria2StateText.text())
        window.aria2Poller.timer.stop()
        window.close()


    def test_hidden_settings_connection_status_waits_for_first_paint(self):
        service = Mock()
        service.client.rpcPort = 6800
        events = Mock()
        events.state = 'unavailable'
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(paths, 'CONFIG_DIR', Path(folder)), \
             patch.object(SettingPage, 'ashoreConfDir', folder), \
             patch.object(
                 SettingPage, 'aria2ConfPath',
                 str(Path(folder) / 'aria2.conf')), \
             patch('interface.mainWindow.Aria2Events', return_value=events):
            window = Ashore(service, Mock())

        window.pageSetting.setConnectionStatus = Mock()
        window.hasPainted = False
        window.updateConnection('已连接')
        window.pageSetting.setConnectionStatus.assert_not_called()

        window.hasPainted = True
        window.flushConnectionStatus()
        window.pageSetting.setConnectionStatus.assert_called_once()
        window.aria2Poller.timer.stop()
        window.close()


    def test_custom_status_strip_replaces_qstatusbar_messages(self):
        service = Mock()
        service.client.rpcPort = 6800
        events = Mock()
        events.state = 'unavailable'
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(paths, 'CONFIG_DIR', Path(folder)), \
             patch.object(SettingPage, 'ashoreConfDir', folder), \
             patch.object(
                 SettingPage, 'aria2ConfPath',
                 str(Path(folder) / 'aria2.conf')), \
             patch('interface.mainWindow.Aria2Events', return_value=events):
            window = Ashore(service, Mock())

        window.showStatus('status message')
        self.assertEqual(
            window.statusMessageLabel.text(), 'status message')
        self.assertTrue(window.statusMessageTimer.isActive())
        window.aria2Poller.timer.stop()
        window.close()



if __name__ == '__main__':
    unittest.main()
