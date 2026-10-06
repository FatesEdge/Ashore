import unittest

from interface.languageManager import LANGUAGES, TEXT, resolveLanguage, systemLanguage, translate


class LanguageManagerTests(unittest.TestCase):
    def test_shell_has_three_complete_language_choices(self):
        self.assertEqual(set(LANGUAGES), {'zh_CN', 'zh_TW', 'en'})
        for language in LANGUAGES:
            self.assertNotEqual(translate(language, 'new'), 'new')
            self.assertNotEqual(translate(language, 'settings'), 'settings')

    def test_all_supported_languages_define_the_same_keys(self):
        englishKeys = set(TEXT['en'])
        for language in LANGUAGES:
            self.assertEqual(set(TEXT[language]), englishKeys)


    def test_system_language_prefers_supported_locale_and_falls_back_to_english(self):
        self.assertEqual(systemLanguage('zh_CN'), 'zh_CN')
        self.assertEqual(systemLanguage('zh_TW'), 'zh_TW')
        self.assertEqual(systemLanguage('zh_HK'), 'zh_TW')
        self.assertEqual(systemLanguage('en_AU'), 'en')
        self.assertEqual(systemLanguage('ja_JP'), 'en')

    def test_configured_language_overrides_system_default(self):
        self.assertEqual(resolveLanguage('zh_TW', 'en_AU'), 'zh_TW')
        self.assertEqual(resolveLanguage('system', 'zh_CN'), 'zh_CN')
        self.assertEqual(resolveLanguage(None, 'fr_FR'), 'en')
        self.assertEqual(resolveLanguage('unsupported', 'zh_CN'), 'en')
    def test_translate_falls_back_to_english_for_unknown_language(self):
        self.assertEqual(translate('unsupported', 'settings'), 'Settings')
        self.assertEqual(
            translate('unsupported', 'startupLoadingConfig'),
            'Loading configuration')


if __name__ == '__main__':
    unittest.main()
