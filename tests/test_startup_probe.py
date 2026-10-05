import unittest

from diagnostics.startupProbe import (
    STARTUP_STAGES,
    buildParser,
    includes,
    stageIndex,
)


class StartupProbeTests(unittest.TestCase):
    def test_stages_are_unique_and_cumulative(self):
        names = [stage.name for stage in STARTUP_STAGES]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(stageIndex('base'), 0)
        self.assertLess(stageIndex('ariaStartup'), stageIndex('windowBase'))
        self.assertLess(stageIndex('windowBase'), stageIndex('windowFrame'))
        self.assertLess(stageIndex('windowFrame'), stageIndex('windowControlsPlain'))
        self.assertLess(stageIndex('windowControlsPlain'), stageIndex('windowControls'))
        self.assertLess(stageIndex('windowControls'), stageIndex('windowContent'))
        self.assertLess(stageIndex('windowContent'), stageIndex('windowMenus'))
        self.assertLess(stageIndex('windowSignals'), stageIndex('mainWindow'))
        self.assertTrue(includes('tray', 'ariaStartup'))
        self.assertTrue(includes('mainWindow', 'windowStatus'))
        self.assertFalse(includes('windowTray', 'windowSignals'))
        self.assertFalse(includes('config', 'ariaStartup'))

    def test_parser_accepts_stage(self):
        options = buildParser().parse_args(['--stage', 'mainWindow'])
        self.assertEqual(options.stage, 'mainWindow')


if __name__ == '__main__':
    unittest.main()
