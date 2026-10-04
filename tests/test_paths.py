import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import paths


class PathTests(unittest.TestCase):
    def test_first_run_uses_system_download_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            configRoot = Path(folder) / 'config'
            expected = Path(folder) / '系统下载目录'
            with patch.object(paths, 'CONFIG_DIR', configRoot), \
                 patch.object(paths, 'systemDownloadDirectory', return_value=expected):
                configPath = paths.ensureConfig('aria2.conf')
            content = configPath.read_text(encoding='utf-8')
            self.assertIn(f'dir={expected}', content)
            self.assertNotIn('${DOWNLOAD_DIR}', content)
            self.assertIn('force-save=false', content)

    def test_only_legacy_default_is_offered_for_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            systemDirectory = root / '下载'
            legacyConfig = root / 'legacy.conf'
            legacyConfig.write_text(
                f'dir={Path.home() / "Downloads"}\n', encoding='utf-8')
            customConfig = root / 'custom.conf'
            customConfig.write_text(
                f'dir={root / "MyDownloads"}\n', encoding='utf-8')
            with patch.object(paths, 'systemDownloadDirectory', return_value=systemDirectory):
                migration = paths.legacyDownloadDirectoryMigration(legacyConfig)
                self.assertEqual(migration, (Path.home() / 'Downloads', systemDirectory))
                self.assertIsNone(paths.legacyDownloadDirectoryMigration(customConfig))


if __name__ == '__main__':
    unittest.main()
