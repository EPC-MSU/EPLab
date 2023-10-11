"""
File with the language selection dialog box class.
"""

import os
from enum import Enum, auto
from typing import Optional, Tuple
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QLayout, QVBoxLayout


class Language(Enum):
    """
    Class for supported languages.
    """

    RU = auto()
    EN = auto()

    @classmethod
    def get_language_name(cls, value: "Language") -> str:
        """
        :param value: value of language.
        :return: name of language.
        """

        return _LANGUAGES.get(value)

    @classmethod
    def get_language_value(cls, language: str) -> Optional["Language"]:
        """
        :param language: name of language.
        :return: value of language.
        """

        for value, name in _LANGUAGES.items():
            if name == language:
                return value
        return None

    @classmethod
    def get_languages(cls) -> Tuple:
        """
        :return: names and values of languages.
        """

        for value, name in _LANGUAGES.items():
            yield value, name

    @classmethod
    def get_translator_file(cls, value: "Language") -> str:
        """
        :param value: value of language.
        :return: path to file with translation for given language.
        """

        return _FILES.get(value)


_LANGUAGES = {Language.RU: "Русский",
              Language.EN: "English"}
_DIR_NAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FILES = {Language.RU: "",
          Language.EN: os.path.join(_DIR_NAME, "gui", "super_translate_en.qm")}


class LanguageSelectionWindow(QDialog):
    """
    Class for window to select language.
    """

    def __init__(self, parent=None) -> None:
        """
        :param parent: parent window.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle(qApp.translate("dialogs", "Выбор языка"))
        self.label: QLabel = QLabel(qApp.translate("dialogs", "Выберите язык:"))
        self.combo_box_languages: QComboBox = QComboBox()
        for value, language in Language.get_languages():
            self.combo_box_languages.addItem(language, value)
        language = Language.get_language_name(qApp.instance().property("language"))
        self.combo_box_languages.setCurrentText(language)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        v_box = QVBoxLayout()
        v_box.addWidget(self.label)
        v_box.addWidget(self.combo_box_languages)
        v_box.addWidget(self.buttonBox)
        v_box.setSizeConstraint(QLayout.SetFixedSize)
        self.adjustSize()
        self.setLayout(v_box)

    def get_language_value(self) -> Language:
        """
        :return: value of language.
        """

        return self.combo_box_languages.currentData()

    def get_translator_file(self) -> str:
        """
        :return: path to file with translation for selected language.
        """

        return _FILES.get(self.combo_box_languages.currentData())
