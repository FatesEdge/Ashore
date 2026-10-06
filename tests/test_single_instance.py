import os
import tempfile
import threading
import time
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
            received = []
            primary.messageReceived.connect(received.append)

            try:
                self.assertTrue(primary.claimOrForward([]))
                self.assertTrue(primary.server.isListening())

                outcome = {}
                def runSecondary():
                    secondary = SingleInstanceCoordinator(
                        name, lockDirectory=folder)
                    try:
                        outcome['claimed'] = secondary.claimOrForward([
                            'https://example.org/file.bin'])
                        outcome['server'] = secondary.server
                    finally:
                        secondary.close()

                thread = threading.Thread(target=runSecondary)
                thread.start()
                deadline = time.monotonic() + 5
                while thread.is_alive() and time.monotonic() < deadline:
                    self.app.processEvents()
                    thread.join(0.01)
                thread.join(timeout=0.1)

                self.assertFalse(thread.is_alive())
                self.assertFalse(outcome['claimed'])
                for _ in range(4):
                    self.app.processEvents()

                self.assertEqual(
                    received, [['https://example.org/file.bin']])
                self.assertIsNone(outcome['server'])
                self.assertTrue(primary.server.isListening())
            finally:
                primary.close()


if __name__ == '__main__':
    unittest.main()
