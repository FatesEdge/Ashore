import unittest

from interface.languageManager import LANGUAGES, translate


class LanguageManagerTests(unittest.TestCase):
    def test_shell_has_three_complete_language_choices(self):
        self.assertEqual(set(LANGUAGES), {'zh_CN', 'zh_TW', 'en'})
        for language in LANGUAGES:
            self.assertNotEqual(translate(language, 'new'), 'new')
            self.assertNotEqual(translate(language, 'settings'), 'settings')


if __name__ == '__main__':
    unittest.main()
