"""
File with the language class.
"""

import os
from enum import auto, Enum
from typing import Optional, Tuple


class Language(Enum):
    """
    Class for supported languages.
    """

    EN = auto()
    RU = auto()


class Translator:
    """
    Class for supported languages.
    """

    _FILES = {Language.EN: os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gui",
                                        "super_translate_en.qm"),
              Language.RU: ""}
    _LANGUAGES = {Language.EN: "English",
                  Language.RU: "Русский"}

    @classmethod
    def get_language_name(cls, value: Language) -> str:
        """
        :param value: value of language.
        :return: name of language.
        """

        return cls._LANGUAGES.get(value)

    @classmethod
    def get_language_value(cls, language: str) -> Optional[Language]:
        """
        :param language: name of language.
        :return: value of language.
        """

        for value, name in cls._LANGUAGES.items():
            if name == language:
                return value
        return None

    @classmethod
    def get_languages(cls) -> Tuple[Language, str]:
        """
        :return: names and values of languages.
        """

        for value, name in cls._LANGUAGES.items():
            yield value, name

    @classmethod
    def get_translator_file(cls, value: Language) -> str:
        """
        :param value: value of language.
        :return: path to file with translation for given language.
        """

        return cls._FILES.get(value)
