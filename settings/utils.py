__all__ = ["get_parameter", "set_parameter", "remove_parameter", "to_bool", "float_to_str"]


def get_parameter(settings, parameter, convert=None, required=True, default=None):
    value = settings.value(parameter)
    if value is not None:
        if convert is None:
            return value
        else:
            return convert(value)
    elif required:
        raise RuntimeError("Parameter \"{}\" missed in config file: \'{}\'".format(parameter, settings.fileName()))
    else:
        return default


def set_parameter(settings, parameter, value):
    settings.setValue(parameter, value)


def remove_parameter(settings, parameter):
    settings.remove(parameter)


def to_bool(value):
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        return value.lower() == "true"
    else:
        return bool(value)


def float_to_str(value):
    # 2 is recommended value for double-precision
    # https://docs.python.org/3.6/tutorial/floatingpoint.html#representation-error
    return format(value, ".2f")
