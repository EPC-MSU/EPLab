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
from platform import system
from typing import List, Optional, Tuple
import psutil
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import (QComboBox, QFormLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
                             QPushButton, QVBoxLayout)
import serial
import serial.tools.list_ports
from epcore.ivmeasurer.measurerasa import IVMeasurerASA, IVMeasurerVirtualASA
from epcore.ivmeasurer.measurerivm import IVMeasurerIVM10
from epcore.ivmeasurer.virtual import IVMeasurerVirtual
import safe_opener
import urpcbase as lib
from language import Language


IP_ASA_REG_EXP = r"^xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
if system().lower() == "windows":
    IP_IVM10_REG_EXP = r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:\\\\\.\\COM\d+)$"
else:
    IP_IVM10_REG_EXP = r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:///dev/ttyACM\d+)$"


class MeasurerType:
    """
    Class with types of measurers.
    """

    IVM10 = "IVM10"
    IVM10_VIRTUAL = "virtual"
    ASA = "ASA"
    ASA_VIRTUAL = "virtualasa"

    @classmethod
    def get_general_measurers_type(cls, measurers_types: List[str]) -> Optional[str]:
        """
        Method returns general type for measurers in list.
        :param measurers_types: types of measurers.
        :return: general type of measurers.
        """

        if cls.IVM10 in measurers_types or cls.IVM10_VIRTUAL in measurers_types:
            return cls.IVM10
        if cls.ASA in measurers_types or cls.ASA_VIRTUAL in measurers_types:
            return cls.ASA
        return None

    @classmethod
    def check_port_for_ivm10(cls, port: Optional[str]) -> bool:
        """
        Method checks if port can be of measurer of IVM10 type.
        :param port: port.
        :return: True if port can be of IVM10 measurer.
        """

        if system().lower() == "windows":
            pattern = re.compile(r"^com:\\\\\.\\COM\d+$")
        elif system().lower() == "linux":
            pattern = re.compile(r"^com:///dev/ttyACM\d+$")
        else:
            raise RuntimeError("Unexpected OS")
        if port is None or (not pattern.match(port) and port != "virtual"):
            return False
        return True


def _create_uri_name(port: str) -> str:
    """
    Function returns uri for port.
    :param port: port.
    :return: uri.
    """

    os_name = _get_platform()
    if "win" in os_name:
        return f"com:\\\\.\\{port}"
    if os_name == "debian":
        return f"com://{port}"
    raise RuntimeError("Unexpected OS")


def _filter_ports_by_vid_and_pid(ports: List, vid: str, pid: str) -> list:
    """
    Function returns list of ports with specified VID and PID from given list.
    :param ports: list of serial ports;
    :param vid: desired VID as a hex string (example: "1CBC");
    :param pid: desired PID as a hex string (example: "0007").
    :return: list of ports.
    """

    filtered_ports = []
    for port in ports:
        try:
            # Normal hwid string example:
            # USB VID:PID=1CBC:0007 SER=7 LOCATION=1-4.1.1:x.0
            vid_pid_info_block = port.hwid.split(" ")[1]
            vid_pid = vid_pid_info_block.split("=")[1]
            p_vid, p_pid = vid_pid.split(":")
            if p_vid == vid and p_pid == pid:
                filtered_ports.append(port)
        except Exception:
            # Some ports can have malformed information: simply ignore such devices
            continue
    return filtered_ports


def _get_active_serial_ports() -> List:
    """
    Function returns lists of serial port names.
    :return: list of the serial ports available on the system.
    """

    ports = serial.tools.list_ports.comports()
    valid_ports = []
    for port in sorted(ports):
        try:
            serial_port = serial.Serial(port.device)
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


def find_urpc_ports(dev_type: str) -> list:
    """
    Function returns available COM-ports for connect.
    :param dev_type: type of device that is connected to port.
    :return: list of ports.
    """

    config = configparser.ConfigParser()
    os_name = _get_platform()
    dir_name = os.path.dirname(os.path.abspath(__file__))
    config_name = "{}/{}_config.ini".format(os_name, dev_type)
    config_file = os.path.join(dir_name, "resources", config_name)
    try:
        config.read(config_file)
    except Exception:
        logging.error("Cannot open %s", config_file)
        raise
    try:
        vid = config["Global"]["vid"]
        pid = config["Global"]["pid"]
    except Exception:
        logging.error("Cannot read 'VID' and 'PID' fields from %s", config_file)
        raise
    serial_ports = _get_active_serial_ports()
    serial_ports = _filter_ports_by_vid_and_pid(serial_ports, vid, pid)
    ximc_ports = []
    for port in serial_ports:
        device_name = _create_uri_name(port.device)
        device = lib.UrpcbaseDeviceHandle(device_name.encode(), True)
        try:
            safe_opener.open_device_safely(device, config_file, lib._logging_callback)
            ximc_ports.append(device_name)
        except RuntimeError:
            logging.error("%s is not XIMC controller", device_name)
    return ximc_ports


def reveal_asa(timeout: float = None) -> List[str]:
    """
    Function detects ASA in the network.
    :param timeout: max waiting time for responses from ASA.
    :return: list of IP addresses.
    """

    waiting_time = 1.0
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
                    sock.sendto(
                        ("DISCOVER_CUBIELORD_REQUEST " + str(sock.getsockname()[1])).encode(),
                        ("255.255.255.255", 8008))
                    sock.setblocking(0)
                    t_end = datetime.utcnow() + timeout
                    while True:
                        t_now = datetime.utcnow()
                        d_t = (t_end - t_now).total_seconds()
                        if d_t < 0:
                            break
                        ready = select.select([sock], [], [], d_t)
                        if ready[0]:
                            data, addr = sock.recvfrom(4096)
                            if data.startswith("DISCOVER_CUBIELORD_RESPONSE ".encode()):
                                ip_address = str(addr[0])
                                ip_addresses.append(ip_address)
            except Exception:
                print(f"Failed to bind to interface {iface_name}, address {address.address}")
    return ip_addresses


class ConnectionWindow(qt.QDialog):
    """
    Class for dialog window to select devices for connection.
    """

    def __init__(self, parent=None):
        """
        :param parent: parent window.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.parent = parent
        self.lang = qApp.instance().property("language")
        self._your_variant = "Свой вариант" if self.lang is Language.RU else "Your variant"
        self._urls = None
        self._initial_ports, self._initial_type = self._get_current_measurers_ports()
        self._init_ui()

    def _check_ip_address(self, ip_address: str) -> bool:
        """
        Method checks if given IP address is correct.
        :return: True if IP address is correct.
        """

        if self.combo_box_measurer_type.currentText() == "ASA":
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
        form_layout = QFormLayout()
        label_measurer_type = QLabel(qApp.translate("t", "Тип ВАХометра"))
        self.combo_box_measurer_type = QComboBox()
        self.combo_box_measurer_type.addItems(["IVM10", "ASA"])
        form_layout.addRow(label_measurer_type, self.combo_box_measurer_type)
        label_measurer_1 = QLabel(qApp.translate("t", "ВАХометр #1"))
        self.combo_box_measurer_1 = QComboBox()
        form_layout.addRow(label_measurer_1, self.combo_box_measurer_1)
        self.line_edit_measurer_1 = QLineEdit()
        form_layout.addRow(QLabel(""), self.line_edit_measurer_1)
        label_measurer_2 = QLabel(qApp.translate("t", "ВАХометр #2"))
        self.combo_box_measurer_2 = QComboBox()
        form_layout.addRow(label_measurer_2, self.combo_box_measurer_2)
        self.line_edit_measurer_2 = QLineEdit()
        form_layout.addRow(QLabel(""), self.line_edit_measurer_2)
        self.button_connect = QPushButton(qApp.translate("t", "Подключить"))
        self.button_disconnect = QPushButton(qApp.translate("t", "Отключить"))
        self.button_cancel = QPushButton(qApp.translate("t", "Отмена"))
        h_box_layout = QHBoxLayout()
        h_box_layout.addWidget(self.button_connect)
        h_box_layout.addWidget(self.button_disconnect)
        h_box_layout.addWidget(self.button_cancel)
        v_box_layout = QVBoxLayout(self)
        v_box_layout.addLayout(form_layout)
        v_box_layout.addLayout(h_box_layout)
        v_box_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(v_box_layout)

    def _get_current_measurers_ports(self) -> Tuple[List[str], str]:
        """
        Method returns ports of measurers connected to app and general type
        of this measurers.
        :return: ports of measurers and general type.
        """

        types = [None, None]
        ports = [None, None]
        for i_measurer, measurer in enumerate(self.parent.get_measurers()):
            if isinstance(measurer, IVMeasurerASA):
                types[i_measurer] = MeasurerType.ASA
            elif isinstance(measurer, IVMeasurerVirtualASA):
                types[i_measurer] = MeasurerType.ASA_VIRTUAL
            elif isinstance(measurer, IVMeasurerIVM10):
                types[i_measurer] = MeasurerType.IVM10
            elif isinstance(measurer, IVMeasurerVirtual):
                types[i_measurer] = MeasurerType.IVM10_VIRTUAL
            if measurer.url:
                ports[i_measurer] = measurer.url
            else:
                ports[i_measurer] = types[i_measurer]
        general_type = MeasurerType.get_general_measurers_type(types)
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

    def _get_ports_for_ivm10(self, ports: List, port_1: str = None, port_2: str = None) ->\
            List[List[str]]:
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
                if port in ports and port != MeasurerType.IVM10_VIRTUAL:
                    ports.remove(port)
        for index in range(2):
            ports_for_first_and_second[index] = [*ports_for_first_and_second[index], *ports]
            if MeasurerType.IVM10_VIRTUAL not in ports_for_first_and_second[index]:
                ports_for_first_and_second[index].append(MeasurerType.IVM10_VIRTUAL)
            if selected_ports[index] not in (MeasurerType.IVM10_VIRTUAL, "None",
                                             self._your_variant):
                try:
                    ports_for_first_and_second[index - 1].remove(selected_ports[index])
                except ValueError:
                    pass
            spec_ports = [*selected_ports, None, MeasurerType.IVM10_VIRTUAL]
            for port in self._initial_ports:
                if port not in spec_ports and MeasurerType.check_port_for_ivm10(port):
                    ports_for_first_and_second[index].append(port)
            ports_for_first_and_second[index] = sorted(ports_for_first_and_second[index])
            ports_for_first_and_second[index].append("None")
            ports_for_first_and_second[index].append(self._your_variant)
        return ports_for_first_and_second

    def _init_asa(self, url_1: str = None, url_2: str = None):
        """
        Method initializes available ports for first and second measurers of
        type ASA.
        :param url_1: selected address for first measurer;
        :param url_2: selected address for second measurer.
        """

        if self._urls is None:
            self._urls = [f"xmlrpc://{host}" for host in reveal_asa(0.05)]
            self._urls.append(self._your_variant)
        urls_for_first = self._urls
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
        Method initializes available ports for first and second measurers of
        type IVM10.
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
        if _get_platform() == "win64":
            self.combo_box_measurer_type.clear()
            self.combo_box_measurer_type.addItem("IVM10")
        self.combo_box_measurer_type.currentTextChanged.connect(self.init_available_ports)
        if self._initial_type is None:
            self._initial_type = MeasurerType.IVM10
        self.combo_box_measurer_type.setCurrentText(self._initial_type)
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
        if self.combo_box_measurer_type.currentText() == MeasurerType.IVM10:
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
        self.parent.connect_devices(*ports)
        self.close()

    @pyqtSlot()
    def disconnect(self):
        """
        Slot disconnects all measurers.
        """

        self.parent.disconnect_devices()
        self.close()

    @pyqtSlot(str)
    def init_available_ports(self, general_measurers_type: str):
        """
        Slot initializes available ports for first and second measurers.
        :param general_measurers_type: general type for measurers.
        """

        for line_edit in self.line_edits:
            line_edit.setVisible(False)
        if general_measurers_type == MeasurerType.IVM10:
            validator = QRegExpValidator(QRegExp(IP_IVM10_REG_EXP), self)
            self._init_ivm10(*self._initial_ports)
        elif general_measurers_type == MeasurerType.ASA:
            validator = QRegExpValidator(QRegExp(IP_ASA_REG_EXP), self)
            self._init_asa(*self._initial_ports)
        for line_edit in self.line_edits:
            line_edit.setValidator(validator)
