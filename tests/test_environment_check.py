from pathlib import Path
import unittest
from unittest.mock import patch

from core.aria2Service import Aria2Service
from core.environmentCheck import (
    EnvironmentIssue,
    aria2ExecutableCandidates,
    findAria2Executable,
    recommendedAria2Install,
)


class EnvironmentCheckTests(unittest.TestCase):
    def test_missing_aria2_returns_structured_issue(self):
        service = Aria2Service()
        with patch.object(
                service.client, 'isRpcReady', return_value=False), \
             patch('core.aria2Service.findAria2Executable', return_value=None):
            issue = service.ensureReady()

        self.assertIsInstance(issue, EnvironmentIssue)
        self.assertEqual(issue.code, 'aria2_missing')
        self.assertTrue(issue.systemName)
        self.assertTrue(issue.installCommand)

    def test_macos_finds_homebrew_and_macports_aria2_outside_path(self):
        with patch('core.environmentCheck.platform.system', return_value='Darwin'), \
             patch('core.environmentCheck.shutil.which', return_value=None), \
             patch('core.environmentCheck.Path.home', return_value=Path('/Users/test')), \
             patch('core.environmentCheck.Path.is_file', autospec=True) as isFile, \
             patch('core.environmentCheck.os.access', return_value=True):
            candidates = aria2ExecutableCandidates()
            self.assertIn(Path('/usr/local/bin/aria2c'), candidates)
            self.assertIn(Path('/opt/homebrew/bin/aria2c'), candidates)
            self.assertIn(Path('/opt/local/bin/aria2c'), candidates)

            target = Path('/opt/local/bin/aria2c')
            isFile.side_effect = lambda path: path == target
            self.assertEqual(findAria2Executable(), str(target))

    def test_windows_and_linux_common_locations_are_covered(self):
        with patch('core.environmentCheck.platform.system', return_value='Windows'), \
             patch.dict('core.environmentCheck.os.environ', {
                 'LOCALAPPDATA': 'C:/Users/test/AppData/Local',
                 'PROGRAMDATA': 'C:/ProgramData',
             }):
            candidates = tuple(str(path).replace('\\\\', '/') for path in aria2ExecutableCandidates())
            self.assertTrue(any('WinGet/Links/aria2c.exe' in path for path in candidates))
            self.assertTrue(any('scoop/shims/aria2c.exe' in path for path in candidates))
            self.assertTrue(any('chocolatey/bin/aria2c.exe' in path for path in candidates))

        with patch('core.environmentCheck.platform.system', return_value='Linux'):
            candidates = aria2ExecutableCandidates()
            self.assertIn(Path('/usr/bin/aria2c'), candidates)
            self.assertIn(Path('/usr/local/bin/aria2c'), candidates)
            self.assertIn(Path('/snap/bin/aria2c'), candidates)

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
