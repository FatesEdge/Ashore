import unittest
from unittest.mock import Mock, patch

from core.desktopIntegration import DesktopIntegration


class DesktopIntegrationTests(unittest.TestCase):
    def test_falls_back_without_a_session_bus(self):
        integration = DesktopIntegration()
        callback = Mock()
        bus = Mock()
        bus.isConnected.return_value = False

        with patch('core.desktopIntegration.QDBusConnection') as connection:
            connection.sessionBus.return_value = bus
            integration.startRoundTrip(callback)

        callback.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
