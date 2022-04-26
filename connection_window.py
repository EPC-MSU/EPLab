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
from typing import Dict, List, Optional, Tuple
import psutil
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QIcon, QPixmap, QRegExpValidator
import serial
import serial.tools.list_ports
import serial.tools.list_ports_common
from epcore.analogmultiplexer import AnalogMultiplexer
from epcore.ivmeasurer import IVMeasurerASA, IVMeasurerIVM10, IVMeasurerVirtual, IVMeasurerVirtualASA
import safe_opener
import urpcbase as lib

logger = logging.getLogger("eplab")
IP_ASA_REG_EXP = r"^(xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|virtual)$"
PLACEHOLDER_ASA = "xmlrpc://x.x.x.x"
if system().lower() == "windows":
    IP_IVM10_REG_EXP = r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:\\\\\.\\COM\d+|virtual)$"
    PLACEHOLDER_IVM = "com:\\\\.\\COMx {} xi-net://x.x.x.x/x"
else:
    IP_IVM10_REG_EXP = r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:///dev/ttyACM\d+|virtual)$"
    PLACEHOLDER_IVM = "com:///dev/ttyACMx {} xi-net://x.x.x.x/x"


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
                raise ValueError("Unknown default name of product")
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
    def get_product_names_for_platform(cls) -> List["ProductNames"]:
        """
        Method returns names of products for platform of system.
        :return: names of products.
        """

        products = [cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_U22, cls.EYEPOINT_S2]
        if _get_platform() != "win64":
            products.append(cls.EYEPOINT_H10)
        return products

    @classmethod
    def get_single_channel_products(cls) -> Tuple:
        """
        Method returns names of products with single channel (measurer).
        :return: names of products.
        """

        return cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_H10


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
            # Normal hwid string example: USB VID:PID=1CBC:0007 SER=7 LOCATION=1-4.1.1:x.0
            vid_pid_info_block = com_port.hwid.split(" ")[1]
            vid_pid = vid_pid_info_block.split("=")[1]
            p_vid, p_pid = vid_pid.split(":")
            if p_vid == vid and p_pid == pid:
                filtered_ports.append(com_port)
        except Exception as exc:
            # Some ports can have malformed information: simply ignore such devices
            logger.warning("Error occurred while filtering COM-port '%s' by VID and PID: %s", com_port, exc)
    return filtered_ports


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
    raise RuntimeError("Unexpected OS")


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
    serial_ports = serial.tools.list_ports.comports()
    serial_ports = _filter_ports_by_vid_and_pid(serial_ports, vid, pid)
    ximc_ports = []
    for com_port in serial_ports:
        device_name = _create_uri_name(com_port.device)
        device = lib.UrpcbaseDeviceHandle(device_name.encode(), True)
        try:
            safe_opener.open_device_safely(device, config_file)
            ximc_ports.append(device_name)
        except RuntimeError as exc:
            logger.error("'%s' is not XIMC controller: %s", device_name, exc)
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
    return ip_addresses


class ComboBoxForDevices(qt.QComboBox):
    """
    Class for combo box to show list of COM-ports or URLs.
    """

    MIN_WIDTH = 100

    def __init__(self):
        super().__init__()
        self.setEditable(True)
        self.setMinimumWidth(self.MIN_WIDTH)

    """
    def showPopup(self):
        self.clear()
        ports = sorted(comport.device for comport in serial.tools.list_ports.comports())
        ports.append("virtual")
        self.addItems(ports)
        super().showPopup()
    """


class MuxWidget(qt.QGroupBox):
    """
    Class for widget to show list of COM-ports for multiplexer.
    """

    BUTTON_SHOW_HELP_WIDTH: int = 20
    COMBO_BOX_MIN_WIDTH: int = 200
    IMAGE_SIZE: int = 200

    def __init__(self):
        super().__init__()
        self.combo_box_com_ports: qt.QComboBox = None
        self._dir_name: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
        self._init_ui()

    def _init_combo_box(self) -> qt.QComboBox:
        """
        Method initializes combo box widget for COM-ports.
        :return: combo box widget created for multiplexer.
        """

        combo_box = qt.QComboBox()
        combo_box.setEditable(True)
        combo_box.setMinimumWidth(self.COMBO_BOX_MIN_WIDTH)
        if _get_platform() == "linux":
            reg_exp = r"^(com:///dev/ttyACM\d+|virtual)$"
            placeholder = "com:///dev/ttyACMx"
        else:
            reg_exp = r"^(com:\\\\\.\\COM\d+|virtual)$"
            placeholder = "com:\\\\.\\COMx"
        combo_box.lineEdit().setValidator(QRegExpValidator(QRegExp(reg_exp)))
        combo_box.lineEdit().setPlaceholderText(placeholder)
        combo_box.setToolTip(placeholder)
        return combo_box

    def _init_ui(self):
        """
        Method initializes widgets on main widget for multiplexer.
        """

        self.setTitle(qApp.translate("t", "Мультиплексор"))
        mux_image = QPixmap(os.path.join(self._dir_name, "mux.png"))
        label = qt.QLabel("")
        label.setPixmap(mux_image.scaled(self.IMAGE_SIZE, self.IMAGE_SIZE, Qt.KeepAspectRatio))
        label.setToolTip(qApp.translate("t", "Мультиплексор"))
        self.combo_box_com_ports = self._init_combo_box()
        self.update_com_ports()
        button_show_help = qt.QPushButton()
        button_show_help.setIcon(QIcon(os.path.join(self._dir_name, "info.png")))
        button_show_help.setToolTip(qApp.translate("t", "Помощь"))
        button_show_help.setFixedWidth(self.BUTTON_SHOW_HELP_WIDTH)
        button_show_help.clicked.connect(self.show_help)
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addWidget(self.combo_box_com_ports)
        h_box_layout.addWidget(button_show_help)
        v_box_layout = qt.QVBoxLayout()
        v_box_layout.addWidget(label)
        v_box_layout.addLayout(h_box_layout)
        v_box_layout.addStretch(1)
        self.setLayout(v_box_layout)

    @staticmethod
    def _find_multiplexer_com_port(ports: List[str]) -> Optional[str]:
        """
        Method looks for COM-port of multiplexer.
        :param ports: available COM-ports.
        :return: COM-port of multiplexer.
        """

        for port in ports:
            try:
                if port == "virtual":
                    return port
                multiplexer = AnalogMultiplexer(port, True)
                multiplexer.open_device()
                multiplexer.get_identity_information()
                multiplexer.close_device()
                return port
            except Exception:
                continue
        return None

    @pyqtSlot()
    def show_help(self):
        """
        Slot shows help information how to enter COM-port.
        """

        msg_box = qt.QMessageBox()
        msg_box.setIcon(qt.QMessageBox.Information)
        msg_box.setWindowTitle(qApp.translate("t", "Помощь"))
        msg_box.setWindowIcon(QIcon(os.path.join(self._dir_name, "ico.png")))
        if "win" in _get_platform():
            info = qApp.translate("t", "Введите значение последовательного порта в формате com:\\\\.\\COMx.")
        else:
            info = qApp.translate("t", "Введите значение последовательного порта в формате com:///dev/ttyACMx.")
        msg_box.setText(info)
        msg_box.exec_()

    @pyqtSlot()
    def update_com_ports(self):
        """
        Method updates list of COM-ports.
        """

        self.combo_box_com_ports.clear()
        ports = sorted(_create_uri_name(comport.device) for comport in serial.tools.list_ports.comports())
        ports.append("virtual")
        multiplexer_port = self._find_multiplexer_com_port(ports)
        self.combo_box_com_ports.addItems(ports)
        self.combo_box_com_ports.setCurrentText(multiplexer_port)


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
        if initial_product_name is None:
            initial_product_name = ProductNames.EYEPOINT_A2
        self._initial_product_name: ProductNames = initial_product_name
        self._initial_ports: List[str] = None
        self._initial_type: MeasurerType = None
        self._initial_ports, self._initial_type = self._get_current_measurers_ports()
        if self._initial_type is None:
            self._initial_type = MeasurerType.IVM10
        self._init_ui()

    def _create_widget_with_measurer_types(self) -> qt.QWidget:
        """
        Method creates widget to select measurer type.
        :return: widget to select measurer type.
        """

        layout = qt.QVBoxLayout()
        widget_measurer_type = qt.QWidget()
        widget_measurer_type.setToolTip(qApp.translate("t", "Тип измерителя"))
        widget_measurer_type.setFixedSize(300, 300)
        widget_measurer_type.setLayout(layout)
        widget = qt.QWidget()
        scroll_area = qt.QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        layout.addWidget(scroll_area)
        grid_layout = qt.QGridLayout()
        widget.setLayout(grid_layout)
        dir_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
        self.radio_buttons_products: Dict[ProductNames, qt.QRadioButton] = {}
        for row, product_name in enumerate(ProductNames.get_product_names_for_platform()):
            radio_button = qt.QRadioButton(product_name.value, self)
            radio_button.setToolTip(product_name.value)
            measurer_type = ProductNames.get_measurer_type_by_product_name(product_name)
            radio_button.toggled.connect(partial(self.init_available_ports, measurer_type))
            product_image = QPixmap(os.path.join(dir_name, f"{product_name.value}.png"))
            label = qt.QLabel("")
            label.setPixmap(product_image.scaled(100, 100, Qt.KeepAspectRatio))
            label.setToolTip(product_name.value)
            grid_layout.addWidget(label, row, 0)
            grid_layout.addWidget(radio_button, row, 1)
            self.radio_buttons_products[product_name] = radio_button
        return widget_measurer_type

    def _create_widgets(self):
        """
        Method creates widgets in dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "Настройка подключения"))
        self.setToolTip(qApp.translate("t", "Настройка подключения"))
        v_box_layout = qt.QVBoxLayout()
        group_box_measurers = qt.QGroupBox(qApp.translate("t", "Измерители"))
        group_box_measurers.setLayout(v_box_layout)
        v_box_layout.addWidget(self._create_widget_with_measurer_types())
        v_box_layout.addLayout(self._create_widgets_for_measurer_ports())
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addWidget(group_box_measurers)
        self.widget_mux: MuxWidget = MuxWidget()
        h_box_layout.addWidget(self.widget_mux)
        self.button_connect: qt.QPushButton = qt.QPushButton(qApp.translate("t", "Подключить"))
        self.button_connect.setToolTip(qApp.translate("t", "Подключить"))
        self.button_connect.setDefault(True)
        self.button_disconnect: qt.QPushButton = qt.QPushButton(qApp.translate("t", "Отключить"))
        self.button_disconnect.setToolTip(qApp.translate("t", "Отключить"))
        self.button_cancel: qt.QPushButton = qt.QPushButton(qApp.translate("t", "Отмена"))
        self.button_cancel.setToolTip(qApp.translate("t", "Отмена"))
        layout = qt.QHBoxLayout()
        layout.addWidget(self.button_connect)
        layout.addWidget(self.button_disconnect)
        layout.addWidget(self.button_cancel)
        v_box_layout = qt.QVBoxLayout(self)
        v_box_layout.addLayout(h_box_layout)
        v_box_layout.addLayout(layout)
        v_box_layout.setSizeConstraint(qt.QLayout.SetFixedSize)
        self.setLayout(v_box_layout)

    def _create_widgets_for_measurer_ports(self) -> qt.QLayout:
        """
        Method creates widgets to select measurer ports.
        :return: layout with created widgets.
        """

        dir_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
        self.combo_box_measurer_1: ComboBoxForDevices = ComboBoxForDevices()
        self.combo_box_measurer_1.setToolTip(qApp.translate("t", "Канал #1"))
        self.label_measurer_1: qt.QLabel = qt.QLabel(qApp.translate("t", "Канал #1"))
        self.button_show_info_1 = qt.QPushButton()
        self.button_show_info_1.setIcon(QIcon(os.path.join(dir_name, "info.png")))
        self.button_show_info_1.setToolTip(qApp.translate("t", "Помощь"))
        self.button_show_info_1.setFixedWidth(20)
        self.button_show_info_1.clicked.connect(lambda: self.show_help_info(True))
        layout = qt.QHBoxLayout()
        layout.addWidget(self.combo_box_measurer_1)
        layout.addWidget(self.button_show_info_1)
        form_layout = qt.QFormLayout()
        form_layout.addRow(self.label_measurer_1, layout)
        self.combo_box_measurer_2: ComboBoxForDevices = ComboBoxForDevices()
        self.combo_box_measurer_2.setToolTip(qApp.translate("t", "Канал #2"))
        self.label_measurer_2: qt.QLabel = qt.QLabel(qApp.translate("t", "Канал #2"))
        self.button_show_info_2 = qt.QPushButton()
        self.button_show_info_2.setIcon(QIcon(os.path.join(dir_name, "info.png")))
        self.button_show_info_2.setToolTip(qApp.translate("t", "Помощь"))
        self.button_show_info_2.setFixedWidth(20)
        self.button_show_info_2.clicked.connect(lambda: self.show_help_info(True))
        layout = qt.QHBoxLayout()
        layout.addWidget(self.combo_box_measurer_2)
        layout.addWidget(self.button_show_info_2)
        form_layout.addRow(self.label_measurer_2, layout)
        return form_layout

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
    def _get_different_ports(ports: List[str]) -> List[str]:
        """
        Method returns only different real ports in list of ports.
        :param ports: initial list of ports.
        :return: ports.
        """

        different_ports = []
        for port in ports:
            if port == "virtual" or port not in different_ports:
                different_ports.append(port)
        return different_ports

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
            if selected_ports[index] != MeasurerType.IVM10_VIRTUAL.value:
                try:
                    ports_for_first_and_second[index - 1].remove(selected_ports[index])
                except ValueError:
                    pass
            spec_ports = [*selected_ports, None, MeasurerType.IVM10_VIRTUAL.value]
            for port in self._initial_ports:
                if port not in spec_ports and MeasurerType.check_port_for_ivm10(port):
                    ports_for_first_and_second[index].append(port)
            ports_for_first_and_second[index] = sorted(ports_for_first_and_second[index])
        return ports_for_first_and_second

    def _init_asa(self, url_1: str = None):
        """
        Method initializes available ports for first measurer of type ASA.
        :param url_1: selected address for first measurer.
        """

        urls_for_first = [f"xmlrpc://{host}" for host in reveal_asa()]
        urls_for_first.append("virtual")
        self.combo_box_measurer_1.clear()
        self.combo_box_measurer_1.addItems(urls_for_first)
        if url_1 in urls_for_first:
            self.combo_box_measurer_1.setCurrentText(url_1)
        else:
            self.combo_box_measurer_1.setCurrentText("virtual")

    def _init_ivm10(self, port_1: str = None, port_2: str = None):
        """
        Method initializes available ports for first and second measurers of type IVM10.
        :param port_1: selected port for first measurer;
        :param port_2: selected port for second measurer.
        """

        product_name, _ = self._get_checked_product_name()
        show_two_channels = product_name not in ProductNames.get_single_channel_products()
        if show_two_channels:
            ports = [port_1, port_2]
        else:
            ports = [port_1, None]
        for index, port in enumerate(ports):
            if not MeasurerType.check_port_for_ivm10(port):
                ports[index] = None
        available_ports = find_urpc_ports("ivm")
        ports_for_first_and_second = self._get_ports_for_ivm10(available_ports, *ports)
        for index, combo_box in enumerate(self.combo_boxes):
            combo_box.clear()
            combo_box.addItems(ports_for_first_and_second[index])
            if ports[index] in ports_for_first_and_second[index]:
                combo_box.setCurrentText(ports[index])
            else:
                combo_box.setCurrentText("virtual")

    def _init_ui(self):
        """
        Method initializes widgets in dialog window.
        """

        self._create_widgets()
        self.combo_boxes = self.combo_box_measurer_1, self.combo_box_measurer_2
        self.radio_buttons_products[self._initial_product_name].setChecked(True)
        for combo_box in self.combo_boxes:
            combo_box.textActivated.connect(self.change_port)
        self.init_available_ports(self._initial_type, True)
        self.button_connect.clicked.connect(self.connect)
        self.button_disconnect.clicked.connect(self.disconnect)
        self.button_cancel.clicked.connect(self.close)
        self.adjustSize()

    def _show_or_hide_second_measurer(self, status: bool = True):
        """
        Method shows or hides combo box for second measurer.
        :param status: if True then combo box will be shown.
        """

        self.button_show_info_2.setVisible(status)
        self.combo_box_measurer_2.setVisible(status)
        self.label_measurer_2.setVisible(status)

    @pyqtSlot()
    def change_port(self):
        """
        Slot handles signal that port for measurer was changed.
        """

        ports = [combo_box.currentText() for combo_box in self.combo_boxes if combo_box.isVisible()]
        product_name, radio_button = self._get_checked_product_name()
        if ProductNames.get_measurer_type_by_product_name(product_name) == MeasurerType.IVM10:
            self._init_ivm10(*ports)
        else:
            self._init_asa(ports[0])

    @pyqtSlot()
    def connect(self):
        """
        Slot connects new measurers.
        """

        ports = []
        for index, combo_box in enumerate(self.combo_boxes):
            if not combo_box.isVisible():
                continue
            elif not combo_box.lineEdit().hasAcceptableInput():
                return
            ports.append(combo_box.currentText())
        ports = self._get_different_ports(ports)
        while len(ports) < 2:
            ports.append("")
        selected_product_name, _ = self._get_checked_product_name()
        for index, port in enumerate(ports):
            if (port == "virtual" and
                    ProductNames.get_measurer_type_by_product_name(selected_product_name) == MeasurerType.ASA):
                ports[index] = "virtualasa"
        self.parent.connect_devices(*ports, selected_product_name)
        self.close()

    @pyqtSlot()
    def disconnect(self):
        """
        Slot disconnects all measurers.
        """

        self.parent.disconnect_devices()
        self.close()

    @pyqtSlot(str, bool)
    def init_available_ports(self, measurer_type: MeasurerType, status: bool):
        """
        Slot initializes available ports for first and second measurers.
        :param measurer_type: type of measurers;
        :param status: if True then ports should be initialized for given type
        of measurers.
        """

        if not status:
            return
        show_two_channels = self._get_checked_product_name()[0] not in ProductNames.get_single_channel_products()
        self._show_or_hide_second_measurer(show_two_channels)
        if measurer_type == MeasurerType.IVM10:
            placeholder_text = PLACEHOLDER_IVM.format(qApp.translate("t", "или"))
            validator = QRegExpValidator(QRegExp(IP_IVM10_REG_EXP), self)
            self._init_ivm10(*self._initial_ports)
        elif measurer_type == MeasurerType.ASA:
            placeholder_text = PLACEHOLDER_ASA
            validator = QRegExpValidator(QRegExp(IP_ASA_REG_EXP), self)
            self._init_asa(self._initial_ports[0])
        else:
            placeholder_text = ""
            validator = QRegExpValidator(QRegExp(r""), self)
        for combo_box in self.combo_boxes:
            combo_box.setValidator(validator)
            combo_box.lineEdit().setPlaceholderText(placeholder_text)

    @pyqtSlot(bool)
    def show_help_info(self, info_for_measurer: bool):
        """
        Slot shows help information how to enter user's COM-port or server address.
        :param info_for_measurer: if True then help information for measurer
        will be shown. Otherwise for multiplexer.
        """

        msg = qt.QMessageBox()
        msg.setIcon(qt.QMessageBox.Information)
        msg.setWindowTitle(qApp.translate("t", "Помощь"))
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "ico.png")
        msg.setWindowIcon(QIcon(icon_path))
        if not info_for_measurer:
            if "win" in _get_platform():
                info = qApp.translate("t", "Введите значение последовательного порта в формате com:\\\\.\\COMx.")
            else:
                info = qApp.translate("t", "Введите значение последовательного порта в формате com:///dev/ttyACMx.")
            msg.setText(info)
            msg.exec_()
            return
        product_name, _ = self._get_checked_product_name()
        measurer_type = ProductNames.get_measurer_type_by_product_name(product_name)
        if measurer_type == MeasurerType.IVM10 and "win" in _get_platform():
            info = qApp.translate("t", "Введите значение последовательного порта в формате com:\\\\.\\COMx или "
                                       "адрес XiNet сервера в формате xi-net://x.x.x.x/x.")
        elif measurer_type == MeasurerType.IVM10 and _get_platform() == "debian":
            info = qApp.translate("t", "Введите значение последовательного порта в формате com:///dev/ttyACMx или "
                                       "адрес XiNet сервера в формате xi-net://x.x.x.x/x.")
        elif measurer_type == MeasurerType.ASA:
            info = qApp.translate("t", "Введите адрес сервера H10 в формате xmlrpc://x.x.x.x.")
        else:
            info = None
        if info:
            msg.setText(info)
            msg.exec_()
