import os
import sys
import unittest
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtWidgets import QApplication
from dialogs.language import Language, LanguageSelectionWindow


class TestLanguage(unittest.TestCase):

    def test_get_language_name(self) -> None:
        self.assertEqual(Language.get_language_name(Language.EN), "English")
        self.assertEqual(Language.get_language_name(Language.RU), "Русский")

    def test_get_language_value(self) -> None:
        self.assertEqual(Language.get_language_value("English"), Language.EN)
        self.assertEqual(Language.get_language_value("Русский"), Language.RU)

    def test_get_translator_file(self) -> None:
        self.assertEqual(Language.get_translator_file(Language.RU), "")
        self.assertEqual(Language.get_translator_file(Language.EN),
                         os.path.abspath(os.path.join("gui", "super_translate_en.qm")))


class TestLanguageSelectionWindow(unittest.TestCase):

    def setUp(self) -> None:
        self._app: QApplication = QApplication(sys.argv[1:])

    def test_get_language_value(self) -> None:
        qApp.instance().setProperty("language", Language.EN)
        window = LanguageSelectionWindow()
        self.assertEqual(window.get_language_value(), Language.EN)

        window.combo_box_languages.setCurrentText("Русский")
        self.assertEqual(window.get_language_value(), Language.RU)

    def test_get_translator_file(self) -> None:
        qApp.instance().setProperty("language", Language.RU)
        window = LanguageSelectionWindow()
        self.assertEqual(window.get_translator_file(), "")

        window.combo_box_languages.setCurrentText("English")
        self.assertEqual(window.get_translator_file(), os.path.abspath(os.path.join("gui", "super_translate_en.qm")))

    def test_language_selection_window(self) -> None:
        window = LanguageSelectionWindow()
        self.assertIsNotNone(window)
