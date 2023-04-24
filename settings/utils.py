from typing import Any, Callable
from PyQt5.QtCore import QSettings


def get_parameter(settings: QSettings, parameter: str, convert: Callable = None, required: bool = True,
                  default: Any = None) -> Any:
    value = settings.value(parameter)
    if value is not None:
        if convert is None:
            return value
        return convert(value)
    if required:
        raise RuntimeError("Parameter '{}' missed in config file '{}'".format(parameter, settings.fileName()))
    return default


def float_to_str(value: float) -> str:
    # 2 is recommended value for double-precision
    # https://docs.python.org/3.6/tutorial/floatingpoint.html#representation-error
    return format(value, ".2f")


def set_parameter(settings: QSettings, parameter: str, value: Any) -> None:
    settings.setValue(parameter, value)


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)
