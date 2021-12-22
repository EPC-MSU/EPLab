"""
File with class for dialog window to select devices for connection.
"""

import configparser
import logging
import os
import re
import select
import socket
import struct
from datetime import datetime, timedelta
from enum import Enum
from functools import partial
from platform import system
from typing import List, Optional, Tuple
import psutil
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QPixmap, QRegExpValidator
import serial
import serial.tools.list_ports
import serial.tools.list_ports_common
from epcore.ivmeasurer.measurerasa import IVMeasurerASA, IVMeasurerVirtualASA
from epcore.ivmeasurer.measurerivm import IVMeasurerIVM10
from epcore.ivmeasurer.virtual import IVMeasurerVirtual
import safe_opener
import urpcbase as lib

logger = logging.getLogger("eplab")
IP_ASA_REG_EXP = r"^xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
if system().lower() == "windows":
    IP_IVM10_REG_EXP = r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:\\\\\.\\COM\d+)$"
else:
    IP_IVM10_REG_EXP = r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:///dev/ttyACM\d+)$"


class ProductNames(Enum):
    """
    Class with names of available products for application.
    """

    EYEPOINT_A2 = "EyePoint a2"
    EYEPOINT_H10 = "EyePoint H10"
    EYEPOINT_S2 = "EyePoint S2"
    EYEPOINT_U21 = "EyePoint u21"
    EYEPOINT_U22 = "EyePoint u22"

    @classmethod
    def get_default_product_name_for_measurers(cls, measurers: List) -> Optional["ProductNames"]:
        """
        Method returns default name of product for given measurers.
        :param measurers: measurers.
        :return: name of product.
        """

        product_name = None
        for measurer in measurers:
            if isinstance(measurer, (IVMeasurerASA, IVMeasurerVirtualASA)) and product_name in (None, cls.EYEPOINT_H10):
                product_name = cls.EYEPOINT_H10
            elif (isinstance(measurer, (IVMeasurerIVM10, IVMeasurerVirtual)) and
                  product_name in (None, cls.EYEPOINT_A2)):
                product_name = cls.EYEPOINT_A2
            else:
                raise ValueError("")
        return product_name

    @classmethod
    def get_measurer_type_by_product_name(cls, product_name: "ProductNames") -> Optional["MeasurerType"]:
        """
        Method returns type of measurer by name of product.
        :param product_name: name of product.
        :return: type of measurer.
        """

        if product_name == cls.EYEPOINT_H10:
            return MeasurerType.ASA
        if product_name in (cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_U22, cls.EYEPOINT_S2):
            return MeasurerType.IVM10
        return None

    @classmethod
    def get_product_names_for_platform(cls) -> list:
        """
        Method returns names of products for platform of system.
        :return: names of products.
        """

        products = [cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_U22, cls.EYEPOINT_S2]
        if _get_platform() != "win64":
            products.append(cls.EYEPOINT_H10)
        return products


class MeasurerType(Enum):
    """
    Class with types of measurers.
    """

    ASA = "ASA"
    ASA_VIRTUAL = "virtualasa"
    IVM10 = "IVM10"
    IVM10_VIRTUAL = "virtual"

    @classmethod
    def check_port_for_ivm10(cls, port: Optional[str]) -> bool:
        """
        Method checks if port can be of measurer of IVM10 type.
        :param port: port.
        :return: True if port can be of IVM10 measurer.
        """

        platform_name = _get_platform()
        if "win" in platform_name:
            pattern = re.compile(r"^com:\\\\\.\\COM\d+$")
        elif platform_name == "debian":
            pattern = re.compile(r"^com:///dev/ttyACM\d+$")
        else:
            raise RuntimeError("Unexpected OS")
        if port is None or (not pattern.match(port) and port != "virtual"):
            return False
        return True


def _create_uri_name(com_port: str) -> str:
    """
    Function returns uri for port.
    :param com_port: COM-port.
    :return: uri.
    """

    os_name = _get_platform()
    if "win" in os_name:
        return f"com:\\\\.\\{com_port}"
    if os_name == "debian":
        return f"com://{com_port}"
    raise RuntimeError("Unexpected OS")


def _filter_ports_by_vid_and_pid(com_ports: List[serial.tools.list_ports_common.ListPortInfo], vid: str, pid: str
                                 ) -> List[serial.tools.list_ports_common.ListPortInfo]:
    """
    Function returns list of COM-ports with specified VID and PID from given list.
    :param com_ports: list of serial ports;
    :param vid: desired VID as a hex string (example: "1CBC");
    :param pid: desired PID as a hex string (example: "0007").
    :return: list of ports.
    """

    filtered_ports = []
    for com_port in com_ports:
        try:
            # Normal hwid string example:
            # USB VID:PID=1CBC:0007 SER=7 LOCATION=1-4.1.1:x.0
            vid_pid_info_block = com_port.hwid.split(" ")[1]
            vid_pid = vid_pid_info_block.split("=")[1]
            p_vid, p_pid = vid_pid.split(":")
            if p_vid == vid and p_pid == pid:
                filtered_ports.append(com_port)
        except Exception:
            # Some ports can have malformed information: simply ignore such devices
            continue
    return filtered_ports


def _get_active_serial_ports() -> List[serial.tools.list_ports_common.ListPortInfo]:
    """
    Function returns lists of serial port names.
    :return: list of the serial ports available on the system.
    """

    com_ports = serial.tools.list_ports.comports()
    valid_ports = []
    for port in sorted(com_ports):
        try:
            serial_port = serial.Serial(port.device, timeout=0)
            serial_port.close()
            valid_ports.append(port)
        except (OSError, serial.SerialException):
            pass
    return valid_ports


def _get_platform() -> Optional[str]:
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
    raise RuntimeError("unexpected OS")


def find_urpc_ports(device_type: str) -> List[str]:
    """
    Function returns available COM-ports to connect.
    :param device_type: type of device that is connected to port.
    :return: list of available COM-ports.
    """

    os_name = _get_platform()
    dir_name = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(dir_name, "resources", os_name, f"{device_type}_config.ini")
    config = configparser.ConfigParser()
    try:
        config.read(config_file)
    except Exception as exc:
        logger.error("Cannot open '%s': %s", config_file, exc)
        raise
    try:
        vid = config["Global"]["vid"]
        pid = config["Global"]["pid"]
    except Exception as exc:
        logger.error("Cannot read 'VID' and 'PID' fields from '%s': %s", config_file, exc)
        raise
    serial_ports = _get_active_serial_ports()
    serial_ports = _filter_ports_by_vid_and_pid(serial_ports, vid, pid)
    ximc_ports = []
    for com_port in serial_ports:
        device_name = _create_uri_name(com_port.device)
        device = lib.UrpcbaseDeviceHandle(device_name.encode(), True)
        try:
            safe_opener.open_device_safely(device, config_file, lib._logging_callback)
            ximc_ports.append(device_name)
        except RuntimeError as exc:
            logger.error("%s is not XIMC controller: %s", device_name, exc)
    return ximc_ports


def reveal_asa(timeout: float = None) -> List[str]:
    """
    Function detects ASA in the local network.
    :param timeout: max waiting time for responses from ASA.
    :return: list of IP addresses.
    """

    waiting_time = 0.1
    if timeout is None:
        timeout = waiting_time
    timeout = timedelta(seconds=timeout)
    ifaces = psutil.net_if_addrs()
    ip_addresses = []
    for iface_name, iface in ifaces.items():
        iface_name = iface_name.encode(errors="replace").decode(errors="replace")
        for address in iface:
            if address.family != socket.AF_INET:
                continue
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.bind((address.address, 0))
                    sock.sendto(("DISCOVER_CUBIELORD_REQUEST " + str(sock.getsockname()[1])).encode(),
                                ("255.255.255.255", 8008))
                    sock.setblocking(0)
                    time_end = datetime.utcnow() + timeout
                    while True:
                        time_now = datetime.utcnow()
                        time_left = (time_end - time_now).total_seconds()
                        if time_left < 0:
                            break
                        ready = select.select([sock], [], [], time_left)
                        if ready[0]:
                            data, addr = sock.recvfrom(4096)
                            if data.startswith("DISCOVER_CUBIELORD_RESPONSE ".encode()):
                                ip_addresses.append(str(addr[0]))
            except Exception as exc:
                logger.error("Failed to bind to interface %s and address %s: %s", iface_name, address.address, exc)
    print(ip_addresses)
    return ip_addresses


class ConnectionWindow(qt.QDialog):
    """
    Class for dialog window to select devices for connection.
    """

    def __init__(self, parent=None, initial_product_name: Optional[ProductNames] = None):
        """
        :param parent: parent window;
        :param initial_product_name: name of product with which application was working.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.parent = parent
        self._urls: list = None
        self._your_variant: str = qApp.translate("t", "Свой вариант")
        if initial_product_name is None:
            initial_product_name = ProductNames.EYEPOINT_A2
        self._initial_product_name: ProductNames = initial_product_name
        self._initial_ports, self._initial_type = self._get_current_measurers_ports()
        if self._initial_type is None:
            self._initial_type = MeasurerType.IVM10
        self._init_ui()

    def _check_ip_address(self, ip_address: str) -> bool:
        """
        Method checks if given IP address is correct.
        :return: True if IP address is correct.
        """

        checked_product_name, _ = self._get_checked_product_name()
        if checked_product_name == ProductNames.EYEPOINT_H10:
            reg_exp = IP_ASA_REG_EXP
        else:
            reg_exp = IP_IVM10_REG_EXP
        if re.match(reg_exp, ip_address):
            return True
        return False

    def _create_widgets(self):
        """
        Method creates widgets in dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "Настройка подключения"))
        layout = qt.QVBoxLayout()
        group_box = qt.QGroupBox(qApp.translate("t", "Тип ВАХометра"))
        group_box.setFixedSize(300, 300)
        group_box.setLayout(layout)
        widget = qt.QWidget()
        scroll_area = qt.QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        layout.addWidget(scroll_area)
        grid_layout = qt.QGridLayout()
        widget.setLayout(grid_layout)
        dir_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
        products = ProductNames.get_product_names_for_platform()
        self.radio_buttons_products = {}
        for row, product_name in enumerate(products):
            radio_button = qt.QRadioButton(product_name.value, self)
            measurer_type = ProductNames.get_measurer_type_by_product_name(product_name)
            radio_button.toggled.connect(partial(self.init_available_ports, measurer_type))
            product_image = QPixmap(os.path.join(dir_name, f"{product_name.value}.png"))
            label = qt.QLabel("")
            label.setPixmap(product_image.scaled(100, 100, Qt.KeepAspectRatio))
            grid_layout.addWidget(label, row, 0)
            grid_layout.addWidget(radio_button, row, 1)
            self.radio_buttons_products[product_name] = radio_button
        form_layout = qt.QFormLayout()
        self.combo_box_measurer_1 = qt.QComboBox()
        form_layout.addRow(qt.QLabel(qApp.translate("t", "ВАХометр #1")), self.combo_box_measurer_1)
        self.line_edit_measurer_1 = qt.QLineEdit()
        form_layout.addRow(qt.QLabel(""), self.line_edit_measurer_1)
        self.combo_box_measurer_2 = qt.QComboBox()
        form_layout.addRow(qt.QLabel(qApp.translate("t", "ВАХометр #2")), self.combo_box_measurer_2)
        self.line_edit_measurer_2 = qt.QLineEdit()
        form_layout.addRow(qt.QLabel(""), self.line_edit_measurer_2)
        self.button_connect = qt.QPushButton(qApp.translate("t", "Подключить"))
        self.button_disconnect = qt.QPushButton(qApp.translate("t", "Отключить"))
        self.button_cancel = qt.QPushButton(qApp.translate("t", "Отмена"))
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addWidget(self.button_connect)
        h_box_layout.addWidget(self.button_disconnect)
        h_box_layout.addWidget(self.button_cancel)
        v_box_layout = qt.QVBoxLayout(self)
        v_box_layout.addWidget(group_box)
        v_box_layout.addLayout(form_layout)
        v_box_layout.addLayout(h_box_layout)
        v_box_layout.setSizeConstraint(qt.QLayout.SetFixedSize)
        self.setLayout(v_box_layout)

    def _get_checked_product_name(self) -> Tuple[ProductNames, qt.QRadioButton]:
        """
        Method returns checked product name and its radio button.
        :return: product name and its radio button.
        """

        for product_name, radio_button in self.radio_buttons_products.items():
            if radio_button.isChecked():
                return product_name, radio_button

    def _get_current_measurers_ports(self) -> Tuple[List[str], MeasurerType]:
        """
        Method returns ports of measurers connected to app and general type of this measurers.
        :return: ports of measurers and general type.
        """

        ports = [None, None]
        general_type = None
        for i_measurer, measurer in enumerate(self.parent.get_measurers()):
            if (isinstance(measurer, (IVMeasurerASA, IVMeasurerVirtualASA)) and
                    (general_type in (None, MeasurerType.ASA))):
                general_type = MeasurerType.ASA
            elif (isinstance(measurer, (IVMeasurerIVM10, IVMeasurerVirtual)) and
                  (general_type in (None, MeasurerType.IVM10))):
                general_type = MeasurerType.IVM10
            else:
                raise ValueError("Measurers are of incompatible types")
            if measurer.url:
                ports[i_measurer] = measurer.url
            elif isinstance(measurer, IVMeasurerVirtualASA):
                ports[i_measurer] = MeasurerType.ASA_VIRTUAL.value
            elif isinstance(measurer, IVMeasurerVirtual):
                ports[i_measurer] = MeasurerType.IVM10_VIRTUAL.value
        return ports, general_type

    @staticmethod
    def _get_different_xi_net_ports(ports: List[str]) -> List[str]:
        """
        Method returns only different xi-net ports in the list of ports.
        :param ports: initial list of ports.
        :return: ports.
        """

        xi_net_ports = True
        for port in ports:
            if not re.match(IP_IVM10_REG_EXP, port):
                xi_net_ports = False
        if xi_net_ports:
            return list(set(ports))
        return ports

    def _get_ports_for_ivm10(self, ports: List, port_1: str = None, port_2: str = None) -> List[List[str]]:
        """
        Method returns lists of available ports for first and second measurers.
        :param ports: all available ports;
        :param port_1: selected port for first measurer;
        :param port_2: selected port for second measurer.
        :return: lists of available ports for first and second measurers.
        """

        selected_ports = port_1, port_2
        ports_for_first_and_second = []
        for port in selected_ports:
            ports_list = [port] if MeasurerType.check_port_for_ivm10(port) else []
            ports_for_first_and_second.append(ports_list)
            if len(ports) > 0:
                if port in ports and port != MeasurerType.IVM10_VIRTUAL.value:
                    ports.remove(port)
        for index in range(2):
            ports_for_first_and_second[index] = [*ports_for_first_and_second[index], *ports]
            if MeasurerType.IVM10_VIRTUAL.value not in ports_for_first_and_second[index]:
                ports_for_first_and_second[index].append(MeasurerType.IVM10_VIRTUAL.value)
            if selected_ports[index] not in (MeasurerType.IVM10_VIRTUAL.value, "None", self._your_variant):
                try:
                    ports_for_first_and_second[index - 1].remove(selected_ports[index])
                except ValueError:
                    pass
            spec_ports = [*selected_ports, None, MeasurerType.IVM10_VIRTUAL.value]
            for port in self._initial_ports:
                if port not in spec_ports and MeasurerType.check_port_for_ivm10(port):
                    ports_for_first_and_second[index].append(port)
            ports_for_first_and_second[index] = sorted(ports_for_first_and_second[index])
            ports_for_first_and_second[index].append("None")
            ports_for_first_and_second[index].append(self._your_variant)
        return ports_for_first_and_second

    def _init_asa(self, url_1: str = None, url_2: str = None):
        """
        Method initializes available ports for first and second measurers of type ASA.
        :param url_1: selected address for first measurer;
        :param url_2: selected address for second measurer.
        """

        urls_for_first = [f"xmlrpc://{host}" for host in reveal_asa()]
        urls_for_first.append(self._your_variant)
        urls_for_second = "virtualasa", "None"
        urls_for_first_and_second = urls_for_first, urls_for_second
        urls = url_1, url_2
        for index, combo_box in enumerate(self.combo_boxes):
            combo_box.clear()
            combo_box.addItems(urls_for_first_and_second[index])
            current_url = "None" if urls[index] is None else urls[index]
            if current_url in urls_for_first_and_second[index]:
                combo_box.setCurrentText(current_url)
            self.line_edits[index].setText("xmlrpc://")
            self.line_edits[index].setVisible(current_url == self._your_variant)

    def _init_ivm10(self, port_1: str = None, port_2: str = None):
        """
        Method initializes available ports for first and second measurers of type IVM10.
        :param port_1: selected port for first measurer;
        :param port_2: selected port for second measurer.
        """

        ports = [port_1, port_2]
        for index, port in enumerate(ports):
            if port != self._your_variant and not MeasurerType.check_port_for_ivm10(port):
                ports[index] = "None"
        available_ports = find_urpc_ports("ivm")
        ports_for_first_and_second = self._get_ports_for_ivm10(available_ports, *ports)
        for index, combo_box in enumerate(self.combo_boxes):
            combo_box.clear()
            combo_box.addItems(ports_for_first_and_second[index])
            if ports[index] in ports_for_first_and_second[index]:
                combo_box.setCurrentText(ports[index])
            self.line_edits[index].setText("")
            self.line_edits[index].setVisible(ports[index] == self._your_variant)

    def _init_ui(self):
        """
        Method initializes widgets in dialog window.
        """

        self._create_widgets()
        self.combo_boxes = self.combo_box_measurer_1, self.combo_box_measurer_2
        self.line_edits = self.line_edit_measurer_1, self.line_edit_measurer_2
        self.radio_buttons_products[self._initial_product_name].setChecked(True)
        for combo_box in self.combo_boxes:
            combo_box.textActivated.connect(self.change_port)
        for line_edit in self.line_edits:
            line_edit.setVisible(False)
        self.init_available_ports(self._initial_type)
        self.button_connect.clicked.connect(self.connect)
        self.button_disconnect.clicked.connect(self.disconnect)
        self.button_cancel.clicked.connect(self.close)
        self.adjustSize()

    @pyqtSlot()
    def change_port(self):
        """
        Slot handles signal that port for measurer was changed.
        """

        ports = [combo_box.currentText() for combo_box in self.combo_boxes]
        product_name, radio_button = self._get_checked_product_name()
        if ProductNames.get_measurer_type_by_product_name(product_name) == MeasurerType.IVM10:
            self._init_ivm10(*ports)
        else:
            self._init_asa(*ports)

    @pyqtSlot()
    def connect(self):
        """
        Slot connects new measurers.
        """

        ports = []
        for index, combo_box in enumerate(self.combo_boxes):
            port = combo_box.currentText()
            if port == self._your_variant:
                port = self.line_edits[index].text()
                if not self._check_ip_address(port):
                    return
            ports.append(port)
        ports = self._get_different_xi_net_ports(ports)
        if len(set(ports)) == 1 and "None" in ports:
            self.disconnect()
            return
        selected_product_name, _ = self._get_checked_product_name()
        self.parent.connect_devices(*ports, selected_product_name)
        self.close()

    @pyqtSlot()
    def disconnect(self):
        """
        Slot disconnects all measurers.
        """

        self.parent.disconnect_devices()
        self.close()

    @pyqtSlot(str)
    def init_available_ports(self, measurer_type: str):
        """
        Slot initializes available ports for first and second measurers.
        :param measurer_type: type of measurers.
        """

        for line_edit in self.line_edits:
            line_edit.setVisible(False)
        if measurer_type == MeasurerType.IVM10:
            validator = QRegExpValidator(QRegExp(IP_IVM10_REG_EXP), self)
            self._init_ivm10(*self._initial_ports)
        elif measurer_type == MeasurerType.ASA:
            validator = QRegExpValidator(QRegExp(IP_ASA_REG_EXP), self)
            self._init_asa(*self._initial_ports)
        for line_edit in self.line_edits:
            line_edit.setValidator(validator)
