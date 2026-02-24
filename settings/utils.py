import locale
import logging
import os
from typing import Any, Callable, Optional
from PyQt5.QtCore import QByteArray, QCoreApplication as qApp, QSettings
from window.language import Language, Translator
from window.utils import get_user_documents_path


logger = logging.getLogger("eplab")


class InvalidParameterValueError(ValueError):
    """
    Exception for the case when a parameter has an invalid value.
    """


class MissingParameterError(RuntimeError):
    """
    Exception for the case when there is no parameter in the settings.
    """


def check_none(value: str) -> Optional[str]:
    return None if value and value.lower() == "none" else str(value)


def convert_geometry_to_value_for_qsettings(geometry: Optional[QByteArray]):
    if geometry is None:
        return str(geometry)

    return geometry


def convert_language_to_str(language: Language) -> str:
    """
    :param language: language.
    :return: language value in string format.
    """

    return str(Translator.get_language_name(language))


def convert_value_from_qsettings_to_geometry(value):
    if isinstance(value, QByteArray):
        return value

    return check_none(value)


def float_to_str(value: float) -> str:
    """
    :param value: real number to be converted to string.
    :return: string.
    """

    # 2 is recommended value for double-precision
    # https://docs.python.org/3.6/tutorial/floatingpoint.html#representation-error
    return format(value, ".2f")


def get_default_language() -> Language:
    """
    Method automatically determines the appropriate language based on the system locale. This method added at
    ticket #94289.
    :return: default language for the system.
    """

    code = locale.getdefaultlocale()[0]
    if code in ("ba_RU", "be", "be_BY", "ce", "ce_RU", "kk", "kk_KZ", "ru", "ru_BY", "ru_KG", "ru_KZ", "ru_MD", "ru_RU",
                "ru_UA", "sah_RU", "tt_RU"):
        return Language.RU

    return Language.EN


def get_dir_path_from_str(value: Optional[str]) -> str:
    """
    :param value: expected path to the folder.
    :return: path to directory.
    """

    if value is None or not os.path.isdir(value):
        return get_user_documents_path()

    return value


def get_language_from_str(value: str) -> Language:
    """
    :param value: language value in string format.
    :return: language.
    """

    language = Translator.get_language_value(value)
    return get_default_language() if language is None else language


def get_parameter(settings: QSettings, parameter: str, convert: Callable[[str], Any] = None, required: bool = False,
                  default: Any = None) -> Any:
    """
    :param settings: QSettings object from which to get the parameter value;
    :param parameter: parameter name;
    :param convert: function to be used to convert the value;
    :param required: if True, then the parameter must have a non-empty value;
    :param default: default value if parameter not found.
    :return: parameter value.
    """

    value = settings.value(parameter)
    if value is not None:
        if convert is not None:
            try:
                converted_value = convert(value)
            except ValueError as exc:
                logger.error("An error occurred while converting the value '%s' for the parameter '%s'", value,
                             parameter)
                error_message = qApp.translate("settings", 'Параметр "{}" имеет недопустимое значение "{}".').format(
                    parameter, value)
                raise InvalidParameterValueError(error_message) from exc
            else:
                value = converted_value
        return value

    if required:
        logger.error("The parameter '%s' is missing from the configuration file", parameter)
        raise MissingParameterError(qApp.translate("settings", 'Значение параметра "{}" не задано в конфигурационном '
                                                               "файле.").format(parameter))
    return default


def set_parameter(settings: QSettings, parameter: str, value: Any) -> None:
    """
    :param settings: QSettings object in which to save the parameter value;
    :param parameter: parameter name;
    :param value: parameter value.
    """

    settings.setValue(parameter, value)


def to_bool(value: Any) -> bool:
    """
    :param value: value to be converted to bool.
    :return: bool value.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() == "true"

    return bool(value)
