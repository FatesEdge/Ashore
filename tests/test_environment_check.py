import unittest
from unittest.mock import patch

from core.aria2Service import Aria2Service
from core.environmentCheck import (
    EnvironmentIssue,
    recommendedAria2Install,
)


class EnvironmentCheckTests(unittest.TestCase):
    def test_missing_aria2_returns_structured_issue(self):
        service = Aria2Service()
        with patch.object(
                service.client, 'isRpcReady', return_value=False), \
             patch('core.aria2Service.shutil.which', return_value=None):
            issue = service.ensureReady()

        self.assertIsInstance(issue, EnvironmentIssue)
        self.assertEqual(issue.code, 'aria2_missing')
        self.assertTrue(issue.systemName)
        self.assertTrue(issue.installCommand)

    def test_recommended_command_uses_linux_package_manager(self):
        def which(name):
            return '/usr/bin/apt' if name == 'apt' else None

        with patch('core.environmentCheck.platform.system', return_value='Linux'), \
             patch('core.environmentCheck.shutil.which', side_effect=which):
            self.assertEqual(
                recommendedAria2Install(),
                'sudo apt install aria2')

    def test_recommended_commands_cover_macos_and_windows(self):
        with patch(
                'core.environmentCheck.platform.system',
                return_value='Darwin'):
            self.assertEqual(
                recommendedAria2Install(), 'brew install aria2')
        with patch(
                'core.environmentCheck.platform.system',
                return_value='Windows'):
            self.assertEqual(
                recommendedAria2Install(),
                'winget install aria2.aria2')


if __name__ == '__main__':
    unittest.main()
