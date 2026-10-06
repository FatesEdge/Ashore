import os
import tempfile
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from core.singleInstance import SingleInstanceCoordinator


class SingleInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        cls.app = QApplication.instance() or QApplication([])

    def test_secondary_process_forwards_without_creating_second_server(self):
        with tempfile.TemporaryDirectory() as folder:
            name = 'AshoreTest-' + Path(folder).name
            primary = SingleInstanceCoordinator(
                name, lockDirectory=folder)
            secondary = SingleInstanceCoordinator(
                name, lockDirectory=folder)
            received = []
            primary.messageReceived.connect(received.append)

            try:
                self.assertTrue(primary.claimOrForward([]))
                self.assertTrue(primary.server.isListening())
                self.app.processEvents()
                self.assertFalse(secondary.claimOrForward([
                    'https://example.org/file.bin']))

                for _ in range(4):
                    self.app.processEvents()

                self.assertEqual(
                    received, [['https://example.org/file.bin']])
                self.assertIsNone(secondary.server)
                self.assertTrue(primary.server.isListening())
            finally:
                secondary.close()
                primary.close()


if __name__ == '__main__':
    unittest.main()
