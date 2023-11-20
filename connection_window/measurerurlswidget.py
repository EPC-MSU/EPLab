"""
File with classes to select measurers.
"""

import ipaddress
import os
from typing import List
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp
from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtWidgets import QComboBox, QGridLayout, QLabel, QMessageBox, QPushButton, QWidget
import connection_window.utils as ut
from connection_window.productname import MeasurerType
from utils import DIR_MEDIA, show_message


class MeasurerURLsWidget(QWidget):
    """
    Class for widget to select URLs for measurers.
    """

    BUTTON_HELP_WIDTH: int = 20
    BUTTON_UPDATE_WIDTH: int = 25
    COMBO_BOX_MIN_WIDTH: int = 160
    IP_ASA_REG_EXP = r"^(xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|virtual)$"
    PLACEHOLDER_ASA = "xmlrpc://x.x.x.x"
    if ut.get_platform() == "debian":
        IP_IVM10_REG_EXP = r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:///dev/ttyACM\d+|virtual)$"
        PLACEHOLDER_IVM = "com:///dev/ttyACMx {} xi-net://x.x.x.x/x"
    else:
        IP_IVM10_REG_EXP = r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:\\\\\.\\COM\d+|virtual)$"
        PLACEHOLDER_IVM = "com:\\\\.\\COMx {} xi-net://x.x.x.x/x"

    def __init__(self, initial_ports: List[str]) -> None:
        """
        :param initial_ports: initial ports of measurers.
        """

        super().__init__()
        self.button_update: QPushButton = None
        self.buttons_show_help: List[QPushButton] = []
        self.combo_boxes_measurers: List[QComboBox] = []
        self.labels_measurers: List[QLabel] = []
        self._initial_ports: List[str] = initial_ports
        self._measurer_type: MeasurerType = None
        self._show_two_channels: bool = None
        self._init_ui()

    def _get_ports_for_ivm10(self, ports: List[str], port_1: str = None, port_2: str = None) -> List[List[str]]:
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
            ports_list = [port] if port is not None and ut.IVM10_PATTERN[ut.get_platform()].match(port) else []
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
                if port not in spec_ports and port is not None and ut.IVM10_PATTERN[ut.get_platform()].match(port) and\
                        port not in ports_for_first_and_second[index]:
                    ports_for_first_and_second[index].append(port)
            ports_for_first_and_second[index] = sorted(ports_for_first_and_second[index])
        return ports_for_first_and_second

    def _init_asa(self, url: str = None) -> None:
        """
        Method initializes available ports for first measurer of type ASA.
        :param url: selected address for first measurer.
        """

        ip_addresses = [ipaddress.ip_address(ip_address) for ip_address in ut.reveal_asa()]
        ip_addresses.sort()
        urls_for_first = [f"xmlrpc://{host}" for host in ip_addresses]
        urls_for_first.append("virtual")
        self.combo_boxes_measurers[0].clear()
        self.combo_boxes_measurers[0].addItems(urls_for_first)
        if url in urls_for_first:
            self.combo_boxes_measurers[0].setCurrentText(url)
        else:
            self.combo_boxes_measurers[0].setCurrentText("virtual")

    def _init_ivm10(self, port_1: str = None, port_2: str = None) -> None:
        """
        Method initializes available ports for first and second measurers of type IVM10.
        :param port_1: selected port for first measurer;
        :param port_2: selected port for second measurer.
        """

        ports = [port_1, port_2] if self._show_two_channels else [port_1, None]
        for index, port in enumerate(ports):
            if port is None or not ut.IVM10_PATTERN[ut.get_platform()].match(port):
                ports[index] = None
        available_ports = ut.find_urpc_ports("ivm")
        ports_for_first_and_second = self._get_ports_for_ivm10(available_ports, *ports)
        for index, combo_box in enumerate(self.combo_boxes_measurers):
            combo_box.clear()
            combo_box.addItems(ports_for_first_and_second[index])
            if ports[index] in ports_for_first_and_second[index]:
                combo_box.setCurrentText(ports[index])
            else:
                combo_box.setCurrentText("virtual")
        if port_1 is None and port_2 is None:
            self._set_real_ivm10_ports()

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget.
        """

        grid_layout = QGridLayout()
        for index in range(1, 3):
            label_text = qApp.translate("connection_window", "Канал #{}")
            label = QLabel(label_text.format(index))
            grid_layout.addWidget(label, index - 1, 0)
            self.labels_measurers.append(label)
            combo_box = QComboBox()
            combo_box.setMinimumWidth(MeasurerURLsWidget.COMBO_BOX_MIN_WIDTH)
            combo_box.setEditable(True)
            combo_box.setToolTip(label_text.format(index))
            combo_box.textActivated.connect(self.change_ports)
            grid_layout.addWidget(combo_box, index - 1, 1)
            self.combo_boxes_measurers.append(combo_box)
            if index == 1:
                self.button_update = QPushButton()
                self.button_update.setFixedWidth(MeasurerURLsWidget.BUTTON_UPDATE_WIDTH)
                self.button_update.setIcon(QIcon(os.path.join(DIR_MEDIA, "update.png")))
                self.button_update.setToolTip(qApp.translate("connection_window", "Обновить"))
                self.button_update.clicked.connect(self.update_ports)
                grid_layout.addWidget(self.button_update, index - 1, 2)
            button = QPushButton()
            button.setIcon(QIcon(os.path.join(DIR_MEDIA, "info.png")))
            button.setToolTip(qApp.translate("connection_window", "Помощь"))
            button.setFixedWidth(MeasurerURLsWidget.BUTTON_HELP_WIDTH)
            button.clicked.connect(self.show_help)
            grid_layout.addWidget(button, index - 1, 3)
            self.buttons_show_help.append(button)
        self.setLayout(grid_layout)

    def _set_real_ivm10_ports(self) -> None:
        """
        Method sets real IVM10 device to current ports.
        """

        ports = ["virtual", "virtual"]
        initial_current_ports = [combo_box.currentText() for combo_box in self.combo_boxes_measurers]
        for combo_box_index, combo_box in enumerate(self.combo_boxes_measurers):
            if not self._show_two_channels and combo_box_index == 1:
                continue
            current_port = combo_box.currentText()
            if current_port == "virtual":
                for index in range(combo_box.count()):
                    if combo_box.itemText(index) != "virtual" and combo_box.itemText(index) not in ports:
                        ports[combo_box_index] = combo_box.itemText(index)
                        break
                else:
                    ports[combo_box_index] = "virtual"
            else:
                ports[combo_box_index] = current_port
        if initial_current_ports != ports:
            self._init_ivm10(*ports)

    @pyqtSlot()
    def change_ports(self) -> None:
        """
        Slot handles signal that port for measurer was changed.
        """

        ports = [combo_box.currentText() for combo_box in self.combo_boxes_measurers if combo_box.isVisible()]
        if self._measurer_type == MeasurerType.IVM10:
            self._init_ivm10(*ports)
        else:
            self._init_asa(ports[0])

    def get_selected_ports(self) -> List[str]:
        """
        Method returns selected ports for measurers.
        :return: list with selected ports.
        """

        ports = []
        for combo_box in self.combo_boxes_measurers:
            if not combo_box.isVisible() or not combo_box.lineEdit().hasAcceptableInput():
                continue
            ports.append(combo_box.currentText())
        return ports

    @pyqtSlot(MeasurerType, bool)
    def set_measurer_type(self, measurer_type: MeasurerType, show_two_channels: bool) -> None:
        """
        Slot sets new measurer type.
        :param measurer_type: new measurer type;
        :param show_two_channels: True if two channels (ports for measurers) should be shown.
        """

        self._show_two_channels = show_two_channels
        self._measurer_type = measurer_type
        if measurer_type == MeasurerType.IVM10:
            placeholder_text = MeasurerURLsWidget.PLACEHOLDER_IVM.format(qApp.translate("t", "или"))
            validator = QRegExpValidator(QRegExp(MeasurerURLsWidget.IP_IVM10_REG_EXP), self)
            self._init_ivm10(*self._initial_ports)
        else:
            placeholder_text = MeasurerURLsWidget.PLACEHOLDER_ASA
            validator = QRegExpValidator(QRegExp(MeasurerURLsWidget.IP_ASA_REG_EXP), self)
            self._init_asa(self._initial_ports[0])
        for combo_box in self.combo_boxes_measurers:
            combo_box.setValidator(validator)
            combo_box.lineEdit().setPlaceholderText(placeholder_text)
        self.buttons_show_help[1].setVisible(show_two_channels)
        self.combo_boxes_measurers[1].setVisible(show_two_channels)
        self.labels_measurers[1].setVisible(show_two_channels)

    @pyqtSlot()
    def show_help(self) -> None:
        """
        Slot shows help information how to enter COM-port or server address.
        """

        if self._measurer_type == MeasurerType.IVM10:
            if "win" in ut.get_platform():
                info = qApp.translate("connection_window", "Введите значение последовательного порта в формате "
                                                           "com:\\\\.\\COMx или адрес XiNet сервера в формате "
                                                           "xi-net://x.x.x.x/x.")
            else:
                info = qApp.translate("connection_window", "Введите значение последовательного порта в формате "
                                                           "com:///dev/ttyACMx или адрес XiNet сервера в формате "
                                                           "xi-net://x.x.x.x/x.")
        else:
            info = qApp.translate("connection_window", "Введите адрес сервера H10 в формате xmlrpc://x.x.x.x.")
        show_message(qApp.translate("connection_window", "Помощь"), info, icon=QMessageBox.Information)

    def validate(self) -> bool:
        """
        Method checks that there are correct values for ports.
        :return: True if values for ports are correct.
        """

        for combo_box in self.combo_boxes_measurers:
            if combo_box.isVisible() and not combo_box.lineEdit().hasAcceptableInput():
                return False
        return True

    @pyqtSlot()
    def update_ports(self) -> None:
        """
        Slot updates ports for measurers.
        """

        if self._measurer_type == MeasurerType.IVM10:
            self._init_ivm10(*self._initial_ports)
        else:
            self._init_asa()
