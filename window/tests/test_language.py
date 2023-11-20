import os
import unittest
from window.language import Language, Translator


class TestLanguage(unittest.TestCase):

    def test_get_language_name(self) -> None:
        self.assertEqual(Translator.get_language_name(Language.EN), "English")
        self.assertEqual(Translator.get_language_name(Language.RU), "Русский")

    def test_get_language_value(self) -> None:
        self.assertEqual(Translator.get_language_value("English"), Language.EN)
        self.assertEqual(Translator.get_language_value("Русский"), Language.RU)

    def test_get_translator_file(self) -> None:
        self.assertEqual(Translator.get_translator_file(Language.RU), "")
        self.assertEqual(Translator.get_translator_file(Language.EN),
                         os.path.abspath(os.path.join("gui", "super_translate_en.qm")))
