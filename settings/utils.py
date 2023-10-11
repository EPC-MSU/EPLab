import logging
from typing import Any, Callable
from PyQt5.QtCore import QCoreApplication as qApp, QSettings


logger = logging.getLogger("eplab")


class InvalidParameterValueError(ValueError):
    pass


class MissingParameterError(RuntimeError):
    pass


def float_to_str(value: float) -> str:
    """
    :param value: real number to be converted to string.
    :return: string.
    """

    # 2 is recommended value for double-precision
    # https://docs.python.org/3.6/tutorial/floatingpoint.html#representation-error
    return format(value, ".2f")


def get_parameter(settings: QSettings, parameter: str, convert: Callable[[str], Any] = None, required: bool = False,
                  default: Any = None):
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
                error_message = qApp.translate("settings", "Параметр '{}' имеет недопустимое значение '{}'.").format(
                    parameter, value)
                raise InvalidParameterValueError(error_message) from exc
            else:
                value = converted_value
        return value

    if required:
        logger.error("The parameter '%s' is missing from the configuration file", parameter)
        raise MissingParameterError(qApp.translate("settings", "Значение параметра '{}' не задано в конфигурационном "
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
