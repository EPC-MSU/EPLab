"""
File with functions to open device and read its library and firmware versions.
"""

import configparser
import logging
import os
from eplab.urpcbase import UrpcbaseDeviceHandle


def _log_runtime(message: str, error: bool = True, warning: bool = False) -> None:
    """
    Function logs message and raises exception if error is True.
    :param message: message for logging;
    :param error: if True then exception should be raised;
    :param warning: if True then log is warning.
    """

    if error:
        raise RuntimeError(message)
    if warning:
        logging.warning(message)
    else:
        logging.info(message)


def _read_conf(file_name: str, port: bytes) -> configparser.ConfigParser:
    """
    Reads config file and returns content, raises error if content is empty.
    :param file_name: path to config file;
    :param port: port of device.
    :return: object with data from config file.
    """

    if not os.path.exists(file_name):
        _log_runtime(f"Try to open device on port {port.decode()}. Config file {file_name} not found")
    config = configparser.ConfigParser()
    config.read(file_name)
    name = config.has_option("Global", "Name")
    if not name:
        _log_runtime(f"Try to open device on port {port.decode()}. There is no Name field in the "
                     f"config file '{file_name}'")
    return config


def open_device_safely(device: UrpcbaseDeviceHandle, config_file: str) -> None:
    """
    Function opens device safely: checks versions of firmware, library and program soft.
    :param device: device object;
    :param config_file: path to config file.
    """

    config = _read_conf(config_file, device.uri)
    version = device.lib_version()  # reading the library version
    name = config.get("Global", "Name")
    msg_base = f"Try to open {name}-device on port {device.uri.decode()}."
    if not config.has_section(version):  # checking for a library partition
        _log_runtime(f"{msg_base} Library version error {version}")
    try:
        device.open_device()
    except Exception:
        _log_runtime(f"{msg_base} Device was not found or cannot be opened")

    device_name = ""  # read controller_name. EyePoint-devices hasn't correct name!
    firmware = ""  # software version
    try:
        identity = device.get_identity_information()
        for i in identity.controller_name:
            if i != 0:
                device_name = device_name + chr(i)
        firmware = f"{identity.firmware_major}.{identity.firmware_minor}.{identity.firmware_bugfix}"
    except Exception:
        _log_runtime(f"{msg_base} Undefined device. GINF command not implemented")
    device.close()
    if name.lower() != device_name.lower():
        _log_runtime(f"{msg_base} Device is not open because it is {device_name.lower()}")
    # Information comparison
    ind = 0
    for opt in config.options(version):
        if config.get(version, opt) == firmware:
            ind = 1
    if ind == 0:
        _log_runtime(f"{msg_base} Version of device {firmware} does not match version of the library {version}", False,
                     True)
    _log_runtime(f"Device - {name}, library - {version}, firmware - {firmware}", False)
