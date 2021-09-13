import configparser
import json
import os
import re
from operator import itemgetter
from platform import system
from typing import Dict, Iterable, List, Optional, Union
import serial.tools.list_ports
from epcore.elements import MeasurementSettings
from epcore.ivmeasurer import (IVMeasurerASA, IVMeasurerIVM10, IVMeasurerVirtual,
                               IVMeasurerVirtualASA)
from epcore.measurementmanager import MeasurementSystem
from epcore.product import EPLab

_FILENAME_FOR_AUTO_SETTINGS = "eplab_settings_for_auto_save_and_read.ini"


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


def _get_options_from_config(config: configparser.ConfigParser) -> Union[Dict, None]:
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
    return {EPLab.Parameter.frequency: frequency,
            EPLab.Parameter.sensitive: resistance,
            EPLab.Parameter.voltage: voltage}


def read_settings_auto(product: EPLab) -> Union[MeasurementSettings, None]:
    """
    Function searches for the settings that were specified for the device
    during previous work.
    :param product:
    :return: previous settings.
    """

    dir_name = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(dir_name, _FILENAME_FOR_AUTO_SETTINGS)
    if not os.path.exists(filename):
        return None
    config = configparser.ConfigParser()
    try:
        config.read(filename)
    except (configparser.ParsingError, configparser.DuplicateSectionError,
            configparser.DuplicateOptionError):
        return None
    options = _get_options_from_config(config["DEFAULT"])
    if options is None:
        return None
    settings = MeasurementSettings(0, 0, 0, 0)
    settings = product.options_to_settings(options, settings)
    if 0 in (settings.probe_signal_frequency, settings.sampling_rate,
             settings.max_voltage, settings.internal_resistance):
        return None
    return settings


def save_settings_auto(product: EPLab, settings: MeasurementSettings):
    """
    Function saves current settings for device in file.
    :param product:
    :param settings: settings to be saved.
    """

    options = product.settings_to_options(settings)
    options = {
        "frequency": options[EPLab.Parameter.frequency],
        "sensitive": options[EPLab.Parameter.sensitive],
        "voltage": options[EPLab.Parameter.voltage]
    }
    config = configparser.ConfigParser()
    config["DEFAULT"] = options
    dir_name = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(dir_name, _FILENAME_FOR_AUTO_SETTINGS)
    with open(filename, "w") as configfile:
        config.write(configfile)


def create_measurers(port_1: str, port_2: str) -> MeasurementSystem:
    """
    Function creates measurers and measurement system.
    :param port_1: port for first measurer;
    :param port_2: port for second measurer.
    :return: measurement system.
    """

    measurers = []
    measurers_args = port_1, port_2
    virtual_already_has_been = False
    for measurer_arg in measurers_args:
        try:
            if measurer_arg == "virtual":
                measurer = IVMeasurerVirtual()
                if virtual_already_has_been:
                    measurer.nominal = 1000
                measurers.append(measurer)
                virtual_already_has_been = True
            elif measurer_arg == "virtualasa":
                measurer = IVMeasurerVirtualASA(defer_open=True)
                measurers.append(measurer)
            elif measurer_arg is not None and "com:" in measurer_arg:
                measurer = IVMeasurerIVM10(measurer_arg, config=os.path.abspath("cur.ini"),
                                           defer_open=True)
                measurers.append(measurer)
            elif measurer_arg is not None and "xmlrpc:" in measurer_arg:
                measurer = IVMeasurerASA(measurer_arg, defer_open=True)
                measurers.append(measurer)
        except Exception:
            pass
    if len(measurers) == 0:
        # Logically it will be correctly to abort here.
        # But for better user experience we will add single virtual IVM.
        ivm_1 = IVMeasurerVirtual()
        measurers.append(ivm_1)
    elif len(measurers) == 2:
        # Reorder measurers according to their addresses in USB hubs tree
        measurers = sort_devices_by_usb_numbers(measurers)
    # Set pretty names for measurers
    measurers[0].name = "test"
    if len(measurers) == 2:
        measurers[1].name = "ref"
    return MeasurementSystem(measurers)
