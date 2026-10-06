import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from PyQt6.QtWidgets import QApplication

from core.downloadRequest import (
    ITEM_LOCAL_TORRENT,
    ITEM_MAGNET,
    ITEM_NETWORK,
    ITEM_REMOTE_TORRENT,
    existingOutputConflict,
    nextAvailableOutputName,
    outputNameAvailable,
    outputNameForItem,
    parseDownloadInputs,
)
from interface.addNewDialog import AddNewDialog


class DownloadRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def test_supported_inputs_and_ashore_scheme_expand_to_items(self):
        with tempfile.TemporaryDirectory() as folder:
            torrent = Path(folder) / 'local.torrent'
            torrent.write_bytes(b'torrent')
            underlying = 'https://example.org/file.zip'
            ashore = 'ashore://add?url=' + quote(underlying, safe='')
            parsed = parseDownloadInputs([
                underlying,
                'https://example.org/file.torrent?token=1',
                'magnet:?xt=urn:btih:0123456789abcdef',
                str(torrent),
                ashore,
            ])

        self.assertEqual(parsed.invalid, ())
        self.assertEqual(
            [item.kind for item in parsed.items],
            [
                ITEM_NETWORK,
                ITEM_REMOTE_TORRENT,
                ITEM_MAGNET,
                ITEM_LOCAL_TORRENT,
            ])

    def test_invalid_input_is_not_silently_dropped(self):
        parsed = parseDownloadInputs([
            'https://example.org/ok.bin',
            'not a download address',
            'magnet:?dn=missing-infohash',
            'ashore://wrong?url=https%3A%2F%2Fexample.org%2Fx',
        ])
        self.assertEqual(parsed.validCount, 1)
        self.assertEqual(len(parsed.invalid), 3)

    def test_dialog_disables_submit_until_all_lines_are_valid(self):
        dialog = AddNewDialog('/tmp', language='zh_CN')
        dialog.text.setPlainText(
            'https://example.org/file.bin\ninvalid input')
        self.assertFalse(dialog.confirmBtn.isEnabled())
        self.assertIn('1 个输入无效', dialog.validationLabel.text())

        dialog.text.setPlainText('https://example.org/file.bin')
        self.assertTrue(dialog.confirmBtn.isEnabled())
        dialog.close()

    def test_advanced_options_build_headers_cookie_and_checksum(self):
        dialog = AddNewDialog(
            '/tmp', ['https://example.org/file.bin'], language='zh_CN')
        dialog.advancedToggle.setChecked(True)
        dialog.fileNameEdit.setText('renamed.bin')
        dialog.refererEdit.setText('https://example.org/')
        dialog.userAgentEdit.setText('Ashore Test/1.0')
        dialog.headersEdit.setPlainText('X-Test: one')
        dialog.cookieEdit.setText('session=abc')
        dialog.checksumEdit.setText('sha-256=abcd')
        dialog.validate()

        self.assertTrue(dialog.confirmBtn.isEnabled())
        self.assertEqual(
            dialog.buildOptions(),
            {
                'out': 'renamed.bin',
                'referer': 'https://example.org/',
                'user-agent': 'Ashore Test/1.0',
                'header': ['X-Test: one', 'Cookie: session=abc'],
                'checksum': 'sha-256=abcd',
            })
        dialog.close()


    def test_existing_plain_file_without_sidecar_is_an_ambiguous_target(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'ubuntu.iso'
            target.write_bytes(b'partial')
            item = parseDownloadInputs(
                ['https://example.org/ubuntu.iso']).items[0]

            self.assertEqual(outputNameForItem(item), 'ubuntu.iso')
            self.assertEqual(
                existingOutputConflict(item, folder), target)

            Path(str(target) + '.aria2').write_bytes(b'progress')
            self.assertIsNone(existingOutputConflict(item, folder))

    def test_existing_target_uses_explicit_output_name_and_numbered_alternative(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'archive.tar.gz'
            target.write_bytes(b'old')
            (root / 'archive.1.tar.gz').write_bytes(b'old numbered')
            item = parseDownloadInputs(
                ['https://example.org/download?id=1']).items[0]

            options = {'out': 'archive.tar.gz'}
            self.assertEqual(
                existingOutputConflict(item, folder, options), target)
            self.assertEqual(
                nextAvailableOutputName(target), 'archive.2.tar.gz')


    def test_manual_output_name_must_be_safe_and_unused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertTrue(outputNameAvailable(folder, 'custom.iso'))
            self.assertFalse(outputNameAvailable(folder, '../custom.iso'))
            self.assertFalse(outputNameAvailable(folder, ''))
            existing = root / 'custom.iso'
            existing.write_bytes(b'existing')
            self.assertFalse(outputNameAvailable(folder, 'custom.iso'))
            existing.unlink()
            Path(str(existing) + '.aria2').write_bytes(b'progress')
            self.assertFalse(outputNameAvailable(folder, 'custom.iso'))


if __name__ == '__main__':
    unittest.main()
