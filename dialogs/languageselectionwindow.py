"""
File with the language selection dialog box class.
"""

import os
from typing import Optional
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QLayout, QVBoxLayout
from window import utils as ut
from window.language import get_language, Language, Translator
from window.scaler import update_scale_of_class


@update_scale_of_class
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
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
        self.label: QLabel = QLabel(qApp.translate("dialogs", "Выберите язык:"))
        self.combo_box_languages: QComboBox = QComboBox()
        for value, language in Translator.get_languages():
            self.combo_box_languages.addItem(language, value)
        language = Translator.get_language_name(get_language())
        self.combo_box_languages.setCurrentText(language)
        self.button_box: QDialogButtonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Cancel).setText(qApp.translate("dialogs", "Отмена"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        v_box = QVBoxLayout()
        v_box.addWidget(self.label)
        v_box.addWidget(self.combo_box_languages)
        v_box.addWidget(self.button_box)
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

        return Translator.get_translator_file(self.combo_box_languages.currentData())


def show_language_selection_window() -> Optional[Language]:
    """
    :return: user's chosen language.
    """

    window = LanguageSelectionWindow()
    if window.exec():
        return window.get_language_value()
