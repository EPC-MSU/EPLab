"""
File with functions to open device and read its library and firmware versions.
"""

import os
try:
    import configparser
except ImportError:
    import ConfigParser as configparser


def _check_config(file_name: str, log, port) -> str:
    """
    Checks right path to config file.
    :param file_name: name of config file;
    :param log:
    :param port: port of device.
    :return: name of config file.
    """

    if not os.path.exists(file_name):
        _log_runtime(log, f"Try to open device on port {port.decode()}. Config file "
                          f"{file_name} not found:")
    return file_name


def _log_runtime(log, message: str, error: bool = True):
    """
    Function logs message and raises exception if error is True.
    :param log:
    :param message: message about error;
    :param error: raise error if True.
    """

    log(2, message, 0)
    if error:
        raise RuntimeError(message)


def _read_conf(file_name: str, log, port) -> configparser.ConfigParser:
    """
    Reads config file and returns content, raises error if content is empty.
    :param file_name: name of config file;
    :param log:
    :param port: port of device.
    :return: object with data from config file.
    """

    config = configparser.ConfigParser()
    config.read(file_name)
    name = config.has_option("Global", "Name")
    if not name:
        _log_runtime(log, f"Try to open {name}-device on port {port.decode()}. There is "
                          f"no Name field in the config file {file_name}")
    return config


def open_device_safely(device, config_file: str, log):
    """
    Function opens device safely: checks versions of firmware, library and
    program soft.
    :param device: device object;
    :param config_file: name of config file;
    :param log: log level.
    """

    config = _read_conf(_check_config(config_file, log, device.uri), log, device.uri)
    version = device.lib_version()  # reading the library version
    name = config.get("Global", "Name")
    msg_base = f"Try to open {name}-device on port {device.uri.decode()}."
    if not config.has_section(version):  # checking for a library partition
        _log_runtime(log, f"{msg_base} Library version error {version}")
    try:
        device.open()
    except Exception:
        _log_runtime(log, f"{msg_base} Device not found or cannot be opened")

    device_name = ""  # Read controller_name. Eyepoint-devices hasn't correct name!!!
    firmware = ""  # software version.
    try:
        identity = device.get_identity_information()
        for i in identity._controller_name:
            if i != 0:
                device_name = device_name + chr(i)
        firmware = (f"{identity._firmware_major}.{identity._firmware_minor}."
                    f"{identity._firmware_bugfix}")
    except Exception:
        _log_runtime(log, f"{msg_base} Undefined device. GINF command not implemented")
    device.close()
    if name.lower() != device_name.lower():
        _log_runtime(log, f"{msg_base} The device is not open because it is {device_name.lower()}")
    # Information comparison
    ind = 0
    for opt in config.options(version):
        if config.get(version, opt) == firmware:
            ind = 1
    if ind == 0:
        _log_runtime(log, f"{msg_base} Version of the device {firmware} does not match the version "
                          f"of the library {version}", False)
    _log_runtime(log, f"Device - {name}, library - {version}, firmware - {firmware}", False)
