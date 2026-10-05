import unittest

from diagnostics.cursorProbe import PROBE_STAGES, buildParser, includes, stageIndex


class CursorProbeTests(unittest.TestCase):
    def test_stage_names_are_unique_and_cumulative(self):
        names = [stage.name for stage in PROBE_STAGES]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(stageIndex('base'), 0)
        self.assertLess(stageIndex('tray'), stageIndex('trayWindowHide'))
        self.assertLess(stageIndex('trayWindowHide'), stageIndex('trayIconHide'))
        self.assertTrue(includes('startupWindow', 'tray'))
        self.assertFalse(includes('tray', 'startupWindow'))

    def test_parser_accepts_named_stage(self):
        options = buildParser().parse_args(['--stage', 'webSocket'])
        self.assertEqual(options.stage, 'webSocket')


if __name__ == '__main__':
    unittest.main()
