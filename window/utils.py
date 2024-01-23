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
from typing import Any, Dict, List, Optional, Tuple
import serial.tools.list_ports
from PyQt5.QtCore import QCoreApplication as qApp, QDir, QStandardPaths, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QLayout, QMessageBox
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


def get_user_documents_path() -> str:
    """
    :return: path to the standard user folder in which documents are stored.
    """

    for path in QStandardPaths.standardLocations(QStandardPaths.DocumentsLocation):
        return path
    return QDir.homePath()


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


def show_message(header: str, message: str, additional_info: str = None, icon: QMessageBox.Icon = QMessageBox.Warning,
                 no_button: bool = False, cancel_button: bool = False, yes_button: bool = False) -> int:
    """
    Function shows message box.
    :param header: header;
    :param message: message;
    :param additional_info: additional information for the message;
    :param icon: message box icon;
    :param no_button: if True, then No button will be shown;
    :param cancel_button: if True, then Cancel button will be shown;
    :param yes_button: if True, then Yes button will be shown.
    :return: code of the button that the user clicked in the message box.
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
    if yes_button:
        message_box.addButton(qApp.translate("t", "Да"), QMessageBox.AcceptRole)
    else:
        message_box.addButton("OK", QMessageBox.AcceptRole)
    if no_button:
        message_box.addButton(qApp.translate("t", "Нет"), QMessageBox.NoRole)
    if cancel_button:
        message_box.addButton(qApp.translate("t", "Отмена"), QMessageBox.RejectRole)
    return message_box.exec()


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
