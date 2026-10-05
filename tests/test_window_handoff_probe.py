import unittest

from diagnostics.windowHandoffProbe import (
    WINDOW_STAGES,
    buildParser,
    includes,
    stageIndex,
)


class WindowHandoffProbeTests(unittest.TestCase):
    def test_stages_are_unique_and_cumulative(self):
        names = [stage.name for stage in WINDOW_STAGES]
        self.assertEqual(len(names), len(set(names)))
        self.assertLess(stageIndex('controls'), stageIndex('icons'))
        self.assertLess(stageIndex('icons'), stageIndex('pages'))
        self.assertTrue(includes('settings', 'controls'))
        self.assertFalse(includes('icons', 'pages'))

    def test_parser_accepts_ab_options(self):
        options = buildParser().parse_args([
            '--stage', 'controls', '--handoff', 'splash',
            '--splash-delay', '1200'])
        self.assertEqual(options.stage, 'controls')
        self.assertEqual(options.handoff, 'splash')
        self.assertEqual(options.splashDelay, 1200)


if __name__ == '__main__':
    unittest.main()
