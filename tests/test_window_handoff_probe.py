import unittest

from diagnostics.windowHandoffProbe import buildParser


class WindowHandoffProbeTests(unittest.TestCase):
    def test_parser_accepts_ab_options(self):
        options = buildParser().parse_args([
            '--stage', 'controls', '--handoff', 'splash',
            '--splash-delay', '1200'])
        self.assertEqual(options.stage, 'controls')
        self.assertEqual(options.handoff, 'splash')
        self.assertEqual(options.splashDelay, 1200)


if __name__ == '__main__':
    unittest.main()
