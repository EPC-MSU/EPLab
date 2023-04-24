"""
File with useful functions.
"""

import configparser
import json
import logging
import os
import re
import sys
from operator import itemgetter
from platform import system
from typing import Dict, Iterable, List, Optional, Tuple
import serial.tools.list_ports
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QCheckBox, QMessageBox
from epcore.analogmultiplexer import AnalogMultiplexer, AnalogMultiplexerBase, AnalogMultiplexerVirtual
from epcore.elements import Board, MeasurementSettings
from epcore.ivmeasurer import IVMeasurerASA, IVMeasurerBase, IVMeasurerIVM10, IVMeasurerVirtual, IVMeasurerVirtualASA
from epcore.ivmeasurer.safe_opener import BadFirmwareVersion
from epcore.measurementmanager import MeasurementSystem
from epcore.product import EyePointProduct
from eplab.language import Language


_FILENAME_FOR_AUTO_SETTINGS = "eplab_settings_for_auto_save_and_read.ini"
DIR_MEDIA: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")


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

    measurers_args = url_1, url_2
    measurers, bad_ports, bad_ports_by_firmware, bad_firmware_text_error = initialize_measurers(measurers_args)
    if bad_ports_by_firmware and request_opening_by_force(bad_firmware_text_error):
        new_meaurers, new_bad_ports, _, _ = initialize_measurers(bad_ports_by_firmware, True)
        measurers.extend(new_meaurers)
        bad_ports.extend(new_bad_ports)
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


def create_measurement_system(measurer_url_1: str, measurer_url_2: str, mux_url: Optional[str] = None
                              ) -> Tuple[Optional[MeasurementSystem], List[str]]:
    """
    Function creates measurement system.
    :param measurer_url_1: URL for first measurer;
    :param measurer_url_2: URL for second measurer;
    :param mux_url: URL for multiplexer.
    :return: measurement system and list with bad ports.
    """

    measurers, bad_ports = create_measurers(measurer_url_1, measurer_url_2)
    if measurers:
        multiplexer, mux_bad_ports = create_multiplexer(mux_url)
        bad_ports.extend(mux_bad_ports)
        if multiplexer:
            return MeasurementSystem(measurers=measurers, multiplexers=[multiplexer]), bad_ports
        return MeasurementSystem(measurers=measurers), bad_ports
    return None, bad_ports


def create_message_box(msg_title: str, msg_text: str, exc: str = "") -> QMessageBox:
    """
    Function creates message box.
    :param msg_title: title of message box;
    :param msg_text: message text;
    :param exc: text of exception.
    :return: message box.
    """

    max_message_length = 500
    message_box = QMessageBox()
    message_box.setIcon(QMessageBox.Warning)
    message_box.setWindowTitle(msg_title)
    message_box.setWindowIcon(QIcon(os.path.join(DIR_MEDIA, "ico.png")))
    message_box.setText(msg_text)
    if exc:
        message_box.setInformativeText(str(exc)[-max_message_length:])
    return message_box


def create_multiplexer(mux_url: Optional[str] = None) -> Tuple[Optional[AnalogMultiplexerBase], List[str]]:
    """
    Function creates multiplexer.
    :param mux_url: URL for multiplexer.
    :return: created multiplexer and list with bad ports.
    """

    try:
        if mux_url == "virtual":
            return AnalogMultiplexerVirtual(mux_url, defer_open=True), []
        elif mux_url is not None and "com:" in mux_url:
            mux = AnalogMultiplexer(mux_url)
            mux.close_device()
            return mux, []
    except Exception:
        return None, [mux_url]
    return None, []


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
        path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return path


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


def initialize_measurers(measurer_ports: Iterable[str], force_open: bool = False
                         ) -> Tuple[List[IVMeasurerBase], List[str], List[str], str]:
    """
    Function initializes measurers.
    :param measurer_ports: ports of measurers.
    :param force_open: if True then port should be opened by force.
    :return: created measurers, bad ports of measurers, ports of measurers with
    incompatible firmwares and text of errors.
    """

    bad_ports = []
    bad_ports_by_firmware = []
    bad_firmware_text_error = ""
    measurers = []
    virtual_already_has_been = False
    for measurer_arg in measurer_ports:
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
                dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                config_file = os.path.join(dir_name, "cur.ini")
                measurer = IVMeasurerIVM10(measurer_arg, config=config_file, defer_open=True, force_open=force_open)
                measurers.append(measurer)
            elif measurer_arg is not None and "xmlrpc:" in measurer_arg:
                measurer_type = "IVMeasurerASA"
                measurer = IVMeasurerASA(measurer_arg, defer_open=True)
                measurers.append(measurer)
        except BadFirmwareVersion as exc:
            logging.error("%s firmware version %s is not compatible with this version of EPLab", exc.args[0],
                          exc.args[2])
            bad_ports_by_firmware.append(measurer_arg)
            text = qApp.translate("t", "{}: версия прошивки {} {} несовместима с данной версией EPLab.")
            if bad_firmware_text_error:
                bad_firmware_text_error += "\n"
            bad_firmware_text_error += text.format(measurer_arg, exc.args[0], exc.args[2])
        except Exception as exc:
            bad_ports.append(measurer_arg)
            logging.error("Error occurred while creating measurer of type '%s': %s", measurer_type, exc)
    return measurers, bad_ports, bad_ports_by_firmware, bad_firmware_text_error


def read_language_auto() -> Optional[Language]:
    """
    Function searches language that were specified for interface during previous work.
    :return: language for interface.
    """

    filename = os.path.join(get_dir_name(), _FILENAME_FOR_AUTO_SETTINGS)
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

    filename = os.path.join(get_dir_name(), _FILENAME_FOR_AUTO_SETTINGS)
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


def request_opening_by_force(text: str) -> bool:
    """
    Function reports that the user has selected measurers with firmware incompatible with program.
    Function also asks if measurers need to be opened by force.
    :param text: error text.
    :return: True if measurers need to be opened by force.
    """

    message_box = create_message_box(qApp.translate("t", "Ошибка"), text)
    check_box_force_open = QCheckBox(qApp.translate("t", "Все равно открыть"))
    message_box.layout().addWidget(check_box_force_open)
    message_box.exec_()
    return check_box_force_open.checkState() == Qt.Checked


def save_settings_auto(product: EyePointProduct, settings: MeasurementSettings, language: str) -> None:
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
    filename = os.path.join(get_dir_name(), _FILENAME_FOR_AUTO_SETTINGS)
    with open(filename, "w") as configfile:
        config.write(configfile)


def set_logger() -> None:
    logging.basicConfig(format="[%(asctime)s %(module)s.%(funcName)s %(levelname)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)


def show_exception(msg_title: str, msg_text: str, exc: str = "") -> None:
    """
    Function shows message box with error.
    :param msg_title: title of message box;
    :param msg_text: message text;
    :param exc: text of exception.
    """

    message_box = create_message_box(msg_title, msg_text, exc)
    message_box.exec_()


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
