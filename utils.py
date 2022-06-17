"""
File with useful functions.
"""

import configparser
import json
import logging
import os
import re
import struct
import sys
from operator import itemgetter
from platform import system
from typing import Dict, Iterable, List, Optional, Tuple
import serial.tools.list_ports
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox
from epcore.elements import Board, MeasurementSettings
from epcore.ivmeasurer import IVMeasurerASA, IVMeasurerBase, IVMeasurerIVM10, IVMeasurerVirtual, IVMeasurerVirtualASA
from epcore.ivmeasurer.safe_opener import BadFirmwareVersion
from epcore.measurementmanager import MeasurementSystem
from epcore.product import EyePointProduct
from language import Language

logger = logging.getLogger("eplab")
_FILENAME_FOR_AUTO_SETTINGS = "eplab_settings_for_auto_save_and_read.ini"
EXCLUSIVE_COM_PORT = {
    "debian": "com:///dev/ttyACMx",
    "win32": "com:\\\\.\\COMx",
    "win64": "com:\\\\.\\COMx"}
COM_PATTERN = {
    "debian": re.compile(r"^com:///dev/ttyACM\d+$"),
    "win32": re.compile(r"^com:\\\\\.\\COM\d+$"),
    "win64": re.compile(r"^com:\\\\\.\\COM\d+$")}
IVM10_PATTERN = {
    "debian": re.compile(r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:///dev/ttyACM\d+|virtual)$"),
    "win32": re.compile(r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:\\\\\.\\COM\d+|virtual)$"),
    "win64": re.compile(r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:\\\\\.\\COM\d+|virtual)$")}
IVMASA_PATTERN = {
    "debian": re.compile(r"^(xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|virtual(asa)?)$"),
    "win32": re.compile(r"^(xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|virtual(asa)?)$"),
    "win64": re.compile(r"^(xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|virtual(asa)?)$")}


def _get_options_from_config(config: configparser.ConfigParser) -> Optional[Dict]:
    """
    Function returns options from config object with saved settings.
    :return: dictionary with probe signal frequency, internal resistance and
    max voltage.
    """

    frequency = config.get("frequency", None)
    resistance = config.get("sensitive", None)
    voltage = config.get("voltage", None)
    if None in (frequency, resistance, voltage):
        return None
    return {EyePointProduct.Parameter.frequency: frequency,
            EyePointProduct.Parameter.sensitive: resistance,
            EyePointProduct.Parameter.voltage: voltage}


def check_com_port(com_port: str) -> bool:
    """
    Function checks that given COM-port can be used for IV-measurer.
    :param com_port: COM-port to check.
    :return: True if COM-port can be used.
    """

    available_ports_in_required_format = [create_uri_name(port.device) for port in serial.tools.list_ports.comports()]
    if com_port not in available_ports_in_required_format:
        raise ValueError(f"COM-port {com_port} was not found in system")
    return True


def check_com_ports(com_ports: List[str]) -> Tuple[List[str], List[str]]:
    """
    Function checks that given COM-ports can be used for IV-measurer.
    :param com_ports: list of COM-ports.
    :return: list of good COM-ports that can be used for IV-measurers and
    list of bad COM-ports.
    """

    bad_com_ports = []
    good_com_ports = []
    for com_port in com_ports:
        if not check_port_name(com_port):
            bad_com_ports.append(com_port)
            good_com_ports.append(None)
        elif com_port is not None and COM_PATTERN[get_platform()].match(com_port) and com_port != "virtual":
            try:
                check_com_port(com_port)
                good_com_ports.append(com_port)
            except ValueError:
                bad_com_ports.append(com_port)
                good_com_ports.append(None)
        else:
            good_com_ports.append(com_port)
    while True:
        try:
            bad_com_ports.remove(EXCLUSIVE_COM_PORT[get_platform()])
            logger.info("Wildcard name com:\\\\.\\COMx passed that is not a real device. If you need to open a real "
                        "device, then instead of com:\\\\.\\COMx you need to enter the real port name")
        except ValueError:
            break
    return good_com_ports, bad_com_ports


def check_port_name(port: str) -> bool:
    """
    Function checks that port name is correct.
    :param port: port name.
    :return: True if port name is correct.
    """

    platform_name = get_platform()
    if port is None:
        return True
    if IVM10_PATTERN[platform_name].match(port) or IVMASA_PATTERN[platform_name].match(port):
        return True
    return False


def check_compatibility(product: EyePointProduct, board: Board) -> bool:
    """
    Function checks operating mode and loaded test plan for compatibility.
    :param product: product;
    :param board: board of loaded test plan.
    :return: True if operating mode and loaded test plan are compatible.
    """

    for element in board.elements:
        for pin in element.pins:
            for measurement in pin.measurements:
                measurement_settings = measurement.settings
                options = product.settings_to_options(measurement_settings)
                if len(options) < 3:
                    return False
    return True


def create_measurers(url_1: str, url_2: str) -> Tuple[Optional[List[IVMeasurerBase]], List[str]]:
    """
    Function creates measurers.
    :param url_1: port for first measurer;
    :param url_2: port for second measurer.
    :return: created measurers and list with bad ports.
    """

    bad_ports = []
    measurers = []
    measurers_args = url_1, url_2
    virtual_already_has_been = False
    for measurer_arg in measurers_args:
        measurer_type = ""
        try:
            if measurer_arg == "virtual":
                measurer_type = "IVMeasurerVirtual"
                measurer = IVMeasurerVirtual()
                if virtual_already_has_been:
                    measurer.nominal = 1000
                measurers.append(measurer)
                virtual_already_has_been = True
            elif measurer_arg == "virtualasa":
                measurer_type = "IVMeasurerVirtualASA"
                measurer = IVMeasurerVirtualASA(defer_open=True)
                measurers.append(measurer)
            elif measurer_arg is not None and ("com:" in measurer_arg or "xi-net:" in measurer_arg):
                measurer_type = "IVMeasurerIVM10"
                dir_name = os.path.dirname(os.path.abspath(__file__))
                config_file = os.path.join(dir_name, "cur.ini")
                measurer = IVMeasurerIVM10(measurer_arg, config=config_file, defer_open=True)
                measurers.append(measurer)
            elif measurer_arg is not None and "xmlrpc:" in measurer_arg:
                measurer_type = "IVMeasurerASA"
                measurer = IVMeasurerASA(measurer_arg, defer_open=True)
                measurers.append(measurer)
        except BadFirmwareVersion as exc:
            logger.error("%s firmware version %s is not compatible with this version of EPLab", exc.args[0],
                         exc.args[2])
            text = qApp.translate("t", "Версия прошивки {} {} несовместима с данной версией EPLab")
            show_exception(qApp.translate("t", "Ошибка"), text.format(exc.args[0], exc.args[2]), "")
        except Exception as exc:
            bad_ports.append(measurer_arg)
            logger.error("Error occurred while creating measurer of type '%s': %s", measurer_type, exc)
    if len(measurers) == 0:
        # Logically it will be correctly to abort here. But for better user
        # experience we will add single virtual IVM
        # measurers.append(IVMeasurerVirtual())
        return None, bad_ports
    elif len(measurers) == 2:
        # Reorder measurers according to their addresses in USB hubs tree
        measurers = sort_devices_by_usb_numbers(measurers)
    # Set pretty names for measurers
    measurers[0].name = "test"
    if len(measurers) == 2:
        measurers[1].name = "ref"
    return measurers, bad_ports


def create_measurement_system(measurer_url_1: str, measurer_url_2: str) -> Tuple[Optional[MeasurementSystem],
                                                                                 List[str]]:
    """
    Function creates measurement system.
    :param measurer_url_1: URL for first measurer;
    :param measurer_url_2: URL for second measurer.
    :return: measurement system and list with bad ports.
    """

    measurers, bad_ports = create_measurers(measurer_url_1, measurer_url_2)
    if measurers:
        return MeasurementSystem(measurers=measurers), bad_ports
    return None, bad_ports


def create_uri_name(com_port: str) -> str:
    """
    Function returns URI for port.
    :param com_port: COM-port.
    :return: URI.
    """

    os_name = get_platform()
    if "win" in os_name:
        return f"com:\\\\.\\{com_port}"
    if os_name == "debian":
        return f"com://{com_port}"
    raise RuntimeError("Unexpected OS")


def find_address_in_usb_hubs_tree(url: str) -> Optional[str]:
    """
    Function finds address of given URL in USB hubs tree.
    :param url: URL of device.
    :return: address of port in USB hubs tree or None if address was not found.
    """

    ports = list(serial.tools.list_ports.comports())
    port = get_port(url)
    if not port:
        return None
    for existing_port in ports:
        if port in existing_port.device:
            hub = re.findall(r"LOCATION=(?P<hub>.+)", existing_port.hwid)
            if not hub:
                return None
                # raise ValueError("No hub found in " + existing_port.hwid)
            return hub[0]
    return None


def get_dir_name() -> str:
    """
    Function returns path to directory with executable file or code files.
    :return: path to directory.
    """

    if getattr(sys, "frozen", False):
        path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        path = os.path.dirname(os.path.abspath(__file__))
    return path


def get_platform() -> Optional[str]:
    """
    Function returns name of OS.
    :return: name of OS.
    """

    os_kind = system().lower()
    if os_kind == "windows":
        if 8 * struct.calcsize("P") == 32:
            return "win32"
        return "win64"
    if os_kind == "linux":
        return "debian"
    raise RuntimeError("Unexpected OS")


def get_port(url) -> Optional[str]:
    """
    Functions returns port name from URL.
    :return: port.
    """

    port = ""
    if system() == "Linux":
        port = re.findall(r"^com:///dev/(?P<port>.+)$", url)
    elif system() == "Windows":
        port = re.findall(r"^com:\\\\.\\(?P<port>.+)$", url)
    if not port:
        return None
    return port[0]


def read_language_auto() -> Optional[Language]:
    """
    Function searches language that were specified for interface during previous work.
    :return: language for interface.
    """

    dir_name = get_dir_name()
    filename = os.path.join(dir_name, _FILENAME_FOR_AUTO_SETTINGS)
    if not os.path.exists(filename):
        return Language.EN
    config = configparser.ConfigParser()
    try:
        config.read(filename)
    except (configparser.ParsingError, configparser.DuplicateSectionError, configparser.DuplicateOptionError):
        return Language.EN
    language_name = config["DEFAULT"].get("language")
    language = Language.get_language_value(language_name)
    if language is None:
        return Language.EN
    return language


def read_json(path: Optional[str] = None) -> Optional[Dict]:
    """
    Function reads file with content in json format.
    :param path: path to file.
    :return: content in json format.
    """

    if not path:
        return None
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def read_settings_auto(product: EyePointProduct) -> Optional[MeasurementSettings]:
    """
    Function searches measurement settings that were specified for device
    during previous work.
    :param product:
    :return: previous settings for measurement system.
    """

    dir_name = get_dir_name()
    filename = os.path.join(dir_name, _FILENAME_FOR_AUTO_SETTINGS)
    if not os.path.exists(filename):
        return None
    config = configparser.ConfigParser()
    try:
        config.read(filename)
    except (configparser.ParsingError, configparser.DuplicateSectionError, configparser.DuplicateOptionError):
        return None
    options = _get_options_from_config(config["DEFAULT"])
    if options is None:
        return None
    settings = MeasurementSettings(0, 0, 0, 0)
    settings = product.options_to_settings(options, settings)
    if -1 in (settings.probe_signal_frequency, settings.sampling_rate, settings.max_voltage,
              settings.internal_resistance):
        return None
    return settings


def save_settings_auto(product: EyePointProduct, settings: MeasurementSettings, language: str):
    """
    Function saves current settings for device in file.
    :param product:
    :param settings: settings to be saved;
    :param language: language for interface.
    """

    options_config = {}
    if settings is not None:
        options = product.settings_to_options(settings)
        options_config = {"frequency": options[EyePointProduct.Parameter.frequency],
                          "sensitive": options[EyePointProduct.Parameter.sensitive],
                          "voltage": options[EyePointProduct.Parameter.voltage]}
    options_config["language"] = language
    config = configparser.ConfigParser()
    config["DEFAULT"] = options_config
    dir_name = get_dir_name()
    filename = os.path.join(dir_name, _FILENAME_FOR_AUTO_SETTINGS)
    with open(filename, "w") as configfile:
        config.write(configfile)


def show_exception(msg_title: str, msg_text: str, exc: str = ""):
    """
    Function shows message box with error.
    :param msg_title: title of message box;
    :param msg_text: message text;
    :param exc: text of exception.
    """

    max_message_length = 500
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(msg_title)
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "ico.png")
    msg.setWindowIcon(QIcon(icon_path))
    msg.setText(msg_text)
    if exc:
        msg.setInformativeText(str(exc)[-max_message_length:])
    msg.exec_()


def sort_devices_by_usb_numbers(measurers: Iterable, reverse: bool = False) -> List:
    """
    Function sorts devices by numbers in the USB hubs tree.
    :param measurers: list or tuple of sortable devices;
    :param reverse: if False devices will be sorted in ascending order.
    :return: sorted devices.
    """

    # Get addresses of devices in USB hubs tree
    addresses = []
    for measurer in measurers:
        address = find_address_in_usb_hubs_tree(measurer.url)
        if address is None:
            return measurers
        addresses.append((address, measurer))
    # Sort by addresses
    sorted_addresses = sorted(addresses, key=itemgetter(0), reverse=reverse)
    return [item[1] for item in sorted_addresses]
