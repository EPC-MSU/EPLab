"""
File with useful functions.
"""

import json
import logging
import os
import re
import sys
from operator import itemgetter
from platform import system
from typing import Any, Callable, Dict, List, Optional, Tuple
import serial.tools.list_ports
from PyQt5.QtCore import QCoreApplication as qApp, QDir, QStandardPaths, Qt
from PyQt5.QtGui import QFontDatabase, QIcon
from PyQt5.QtWidgets import QCheckBox, QHBoxLayout, QLayout, QMessageBox
from epcore.elements import MeasurementSettings
from epcore.ivmeasurer import IVMeasurerBase


logger = logging.getLogger("eplab")
DIR_MEDIA: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")


def calculate_scales(settings: MeasurementSettings) -> Tuple[float, float]:
    """
    :param settings: measurement settings.
    :return: scale along horizontal and vertical axes.
    """

    scale_coefficient = 1.2
    x_scale = scale_coefficient * settings.max_voltage
    y_scale = 1000 * x_scale / settings.internal_resistance
    return x_scale, y_scale


def clear_layout(layout: QLayout) -> None:
    """
    :param layout: layout from which to completely remove all widgets.
    """

    for i_item in range(layout.count()):
        item = layout.itemAt(i_item)
        widget = item.widget()
        layout.removeWidget(widget)
        widget.deleteLater()


def convert_to_multiple_units(value: float) -> Tuple[float, str]:
    """
    :param value: the value to be converted to multiples of units.
    :return: converted number and unit prefix.
    """

    sign = 1 if value >= 0 else -1
    value = abs(value)
    if value >= 10 ** 18:
        value = round(value / 10 ** 18, 2)
        unit = qApp.translate("t", "Э")
    elif value >= 10 ** 15:
        value = round(value / 10 ** 15, 2)
        unit = qApp.translate("t", "П")
    elif value >= 10 ** 12:
        value = round(value / 10 ** 12, 2)
        unit = qApp.translate("t", "Т")
    elif value >= 10 ** 9:
        value = round(value / 10 ** 9, 2)
        unit = qApp.translate("t", "Г")
    elif value >= 10 ** 6:
        value = round(value / 10 ** 6, 2)
        unit = qApp.translate("t", "М")
    elif value >= 10 ** 3:
        value = round(value / 10 ** 3, 2)
        unit = qApp.translate("t", "к")
    elif value >= 1:
        value = round(value, 2)
        unit = ""
    elif value >= 1e-3:
        value = round(10 ** 3 * value, 2)
        unit = qApp.translate("t", "м")
    elif value >= 1e-6:
        value = round(10 ** 6 * value, 2)
        unit = qApp.translate("t", "мк")
    elif value >= 1e-9:
        value = round(10 ** 9 * value, 2)
        unit = qApp.translate("t", "н")
    elif value >= 1e-12:
        value = round(10 ** 12 * value, 2)
        unit = qApp.translate("t", "п")
    elif value >= 1e-15:
        value = round(10 ** 15 * value, 2)
        unit = qApp.translate("t", "ф")
    else:
        value = round(10 ** 18 * value, 2)
        unit = qApp.translate("t", "а")
    return sign * value, unit


def create_message_box(header: str, message: str, additional_info: str = None, detailed_info: str = None,
                       icon: QMessageBox.Icon = QMessageBox.Warning, no_button: bool = False,
                       cancel_button: bool = False, yes_button: bool = False) -> QMessageBox:
    """
    Function creates message box.
    :param header: header;
    :param message: message;
    :param additional_info: additional information for the message;
    :param detailed_info: text to be displayed in the details area;
    :param icon: message box icon;
    :param no_button: if True, then No button will be shown;
    :param cancel_button: if True, then Cancel button will be shown;
    :param yes_button: if True, then Yes button will be shown.
    :return: message box.
    """

    message_box = QMessageBox()
    message_box.setWindowTitle(header)
    message_box.setWindowIcon(QIcon(os.path.join(DIR_MEDIA, "icon.png")))
    message_box.setIcon(icon)
    message_box.setTextFormat(Qt.RichText)
    message_box.setTextInteractionFlags(Qt.TextBrowserInteraction)
    message_box.setText(message)
    if additional_info:
        message_box.setInformativeText(additional_info)
    if detailed_info:
        message_box.setDetailedText(detailed_info)
    if yes_button:
        message_box.addButton(qApp.translate("t", "Да"), QMessageBox.AcceptRole)
    else:
        message_box.addButton("OK", QMessageBox.AcceptRole)
    if no_button:
        message_box.addButton(qApp.translate("t", "Нет"), QMessageBox.NoRole)
    if cancel_button:
        message_box.addButton(qApp.translate("t", "Отмена"), QMessageBox.RejectRole)
    return message_box


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


def get_device_port(devices: List[Any], index: int) -> Optional[str]:
    """
    :param devices: list of devices from one of which to get a port;
    :param index: index of the device whose port to get.
    :return: desired device port.
    """

    return devices[index]._url if len(devices) > index else None


def get_dir_name() -> str:
    """
    :return: path to directory with executable file or code files.
    """

    if getattr(sys, "frozen", False):
        path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return path


def get_port(url: str) -> Optional[str]:
    """
    :param url: URL.
    :return: port name from URL.
    """

    port = ""
    if system() == "Linux":
        port = re.findall(r"^com:///dev/(?P<port>.+)$", url)
    elif system() == "Windows":
        port = re.findall(r"^com:\\\\.\\(?P<port>.+)$", url)

    if not port:
        return None

    return port[0]


def get_str_representation_of_physical_quantity(name: str, value: float, units_of_measurement) -> str:
    """
    :param name: designation/name of a physical quantity;
    :param value: physical quantity value;
    :param units_of_measurement: units of measurement.
    :return: textual representation of a physical quantity.
    """

    value, prefix = convert_to_multiple_units(value)
    return f"{name}: {value} {prefix}{units_of_measurement}"


def get_units_of_measurement_for_physical_quantity(name: str) -> str:
    """
    :param name: designation/name of a physical quantity.
    :return: units of measurement.
    """

    units = {"C": qApp.translate("t", "Ф"),
             "R": qApp.translate("t", "Ом"),
             "Df": qApp.translate("t", "В"),
             "Dr": qApp.translate("t", "В")}
    return units.get(name, "")


def get_user_documents_path() -> str:
    """
    :return: path to the standard user folder in which documents are stored.
    """

    for path in QStandardPaths.standardLocations(QStandardPaths.StandardLocation.DocumentsLocation):
        return path

    return QDir.homePath()


def load_monospace_font() -> str:
    """
    :return: font family name.
    """

    font_path = os.path.join(DIR_MEDIA, "consolas.ttf")
    font_id = QFontDatabase.addApplicationFont(font_path)
    if font_id == -1:
        logger.error("Error loading font from file '%s'", font_path)
        return "monospace"

    font_families = QFontDatabase.applicationFontFamilies(font_id)
    if font_families:
        font_family_name = font_families[0]
        logger.info("Font '%s' loaded successfully", font_family_name)
        return font_family_name

    return "monospace"


def read_json(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Function reads file with content in json format.
    :param path: path to file.
    :return: content in json format.
    """

    if not path:
        return None

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def restore_ld_library_path(func: Callable[..., Any]):
    """
    To run an external application (such as Firefox) from a frozen application, you need to restore LD_LIBRARY_PATH.
    :param func: a decorated function in which an external application can be called.
    """

    def wrapper(*args, **kwargs) -> Any:
        backup_ld_library_path = os.environ.get("LD_LIBRARY_PATH", None)
        logger.info("LD_LIBRARY_PATH before restoration: %s", os.environ.get("LD_LIBRARY_PATH", None))

        if os.environ.get("LD_LIBRARY_PATH_ORIG", None) is not None:
            os.environ["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH_ORIG"]
            logger.info("LD_LIBRARY_PATH is set to a value before the application is launched: %s",
                        os.environ["LD_LIBRARY_PATH"])
        else:
            os.environ.pop("LD_LIBRARY_PATH", None)
            logger.info("LD_LIBRARY_PATH removed")

        result = func(*args, **kwargs)

        if backup_ld_library_path is not None:
            os.environ["LD_LIBRARY_PATH"] = backup_ld_library_path
        else:
            os.environ.pop("LD_LIBRARY_PATH", None)
        logger.info("LD_LIBRARY_PATH restored: %s", os.environ.get("LD_LIBRARY_PATH", None))

        return result

    return wrapper


@restore_ld_library_path
def show_message(header: str, message: str, additional_info: str = None, detailed_text: str = None,
                 icon: QMessageBox.Icon = QMessageBox.Warning, no_button: bool = False, cancel_button: bool = False,
                 yes_button: bool = False) -> int:
    """
    Function shows message box.
    :param header: header;
    :param message: message;
    :param additional_info: additional information for the message;
    :param detailed_text: text to be displayed in the details area;
    :param icon: message box icon;
    :param no_button: if True, then No button will be shown;
    :param cancel_button: if True, then Cancel button will be shown;
    :param yes_button: if True, then Yes button will be shown.
    :return: code of the button that the user clicked in the message box.
    """

    message_box = create_message_box(header, message, additional_info, detailed_text, icon, no_button, cancel_button,
                                     yes_button)
    return message_box.exec()


def show_message_with_option(header: str, message: str, option_text: str, additional_info: str = None,
                             icon: QMessageBox.Icon = QMessageBox.Warning, no_button: bool = False,
                             cancel_button: bool = False, yes_button: bool = False) -> Tuple[int, bool]:
    """
    Function shows message box with an additional option.
    :param header: header;
    :param message: message;
    :param option_text: option text;
    :param additional_info: additional information for the message;
    :param icon: message box icon;
    :param no_button: if True, then No button will be shown;
    :param cancel_button: if True, then Cancel button will be shown;
    :param yes_button: if True, then Yes button will be shown.
    :return: code of the button that the user clicked in the message box and True if the additional option has been
    selected.
    """

    message_box = create_message_box(header, message, additional_info, icon=icon, no_button=no_button,
                                     cancel_button=cancel_button, yes_button=yes_button)
    layout = message_box.layout()
    item_with_ok_button = layout.itemAtPosition(2, 2)
    layout.removeItem(item_with_ok_button)

    check_box_force_open = QCheckBox(option_text)
    h_layout = QHBoxLayout()
    h_layout.addWidget(check_box_force_open)
    h_layout.addStretch(1)
    h_layout.addItem(item_with_ok_button)

    layout.addLayout(h_layout, 2, 0, 1, 3, Qt.AlignLeft)
    return message_box.exec_(), check_box_force_open.checkState() == Qt.Checked


def sort_devices_by_usb_numbers(measurers: List[IVMeasurerBase], reverse: bool = False) -> List[IVMeasurerBase]:
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
