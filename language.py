"""
File with class for dialog window for language selection.
"""

from enum import Enum, auto
from typing import Tuple
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import QCoreApplication as qApp


class Language(Enum):
    ru = auto()
    en = auto()

    @classmethod
    def get_language(cls, value: "Language") -> str:
        """
        Method returns name of language for given value.
        :param value: value of language.
        :return: name of language.
        """

        return _LANGUAGES.get(value)

    @classmethod
    def get_languages(cls) -> Tuple:
        """
        Method returns names and values of languages.
        :return: names and values of languages.
        """

        for value, name in _LANGUAGES.items():
            yield value, name


_LANGUAGES = {Language.ru: "Русский",
              Language.en: "English"}

_FILES = {Language.ru: "",
          Language.en: "gui/super_translate_en.qm"}


class LanguageSelectionWindow(qt.QDialog):
    """
    Class for window to select language.
    """

    def __init__(self, parent=None):
        """
        :param parent: parent window.
        """

        super().__init__(parent=parent)
        self._init_ui()

    def _init_ui(self):
        """
        Method initializes widgets in dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "Выбор языка"))
        v_box = qt.QVBoxLayout()
        label = qt.QLabel(qApp.translate("t", "Выберите язык:"))
        v_box.addWidget(label)
        self.combo_box_languages = qt.QComboBox()
        for value, language in Language.get_languages():
            self.combo_box_languages.addItem(language, value)
        language = Language.get_language(qApp.instance().property("language"))
        self.combo_box_languages.setCurrentText(language)
        v_box.addWidget(self.combo_box_languages)
        btns = qt.QDialogButtonBox.Ok | qt.QDialogButtonBox.Cancel
        self.buttonBox = qt.QDialogButtonBox(btns)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        v_box.addWidget(self.buttonBox)
        self.adjustSize()
        self.setLayout(v_box)

    def get_language(self) -> Language:
        """
        Method returns selected language.
        :return: language.
        """

        return self.combo_box_languages.currentData()

    def get_translator(self) -> str:
        """
        Method returns file with translation for selected language.
        :return: path to file with required translation.
        """

        return _FILES.get(self.combo_box_languages.currentData())
