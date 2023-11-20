import os
import sys
import unittest
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtWidgets import QApplication
from dialogs.languageselectionwindow import LanguageSelectionWindow
from window.language import Language


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
