"""
File with classes to select measurers.
"""

import os
from typing import Callable, List, Optional, Tuple
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QEvent, QObject, Qt
from PyQt5.QtGui import QFocusEvent, QIcon
from PyQt5.QtWidgets import QComboBox, QGridLayout, QLabel, QMessageBox, QPushButton, QWidget
import connection_window.utils as ut
from connection_window.productname import MeasurerType
from connection_window.urichecker import URIChecker
from window.utils import DIR_MEDIA, show_message


class MeasurerURIsWidget(QWidget):
    """
    Class for widget to select URLs for measurers.
    """

    BUTTON_HELP_WIDTH: int = 20
    BUTTON_UPDATE_WIDTH: int = 25
    COMBO_BOX_MIN_WIDTH: int = 160
    PLACEHOLDER_ASA: str = "xmlrpc://x.x.x.x"
    PLACEHOLDER_IVM: str = "com:///dev/ttyx" if ut.get_platform() == "debian" else "com:\\\\.\\COMx"

    def __init__(self, initial_uris: List[str]) -> None:
        """
        :param initial_uris: initial URIs of measurers.
        """

        super().__init__()
        self._check_uri: Callable[[str], bool] = None
        self._initial_uris: List[str] = initial_uris
        self._measurer_type: MeasurerType = None
        self._show_two_channels: bool = None
        self._uri_checker: URIChecker = URIChecker()
        self._init_ui()

    def _check_uri_correctness(self) -> bool:
        """
        Method checks that there are correct values for URIs.
        :return: True if values for URIs are correct.
        """

        for combo_box in self.combo_boxes_measurers:
            if combo_box.isVisible() and not self._uri_checker.check_uri_for_correctness(combo_box):
                return False
        return True

    def _get_ports_for_ivm10(self, ports: List[str], port_1: str = None, port_2: str = None) -> List[List[str]]:
        """
        :param ports: all available ports;
        :param port_1: selected port for first measurer;
        :param port_2: selected port for second measurer.
        :return: lists of available ports for first and second measurers.
        """

        selected_ports = [port_1, port_2]
        for port_index, port in enumerate(selected_ports):
            i = get_string_index_in_list(port, ports)
            if i is not None:
                selected_ports[port_index] = ports[i]

        ports_for_first_and_second = []
        for port in selected_ports:
            ports_list = [port] if port is not None and URIChecker.check_ivm10(port) else []
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
            for port in self._initial_uris:
                if port is not None and URIChecker.check_ivm10(port) and not check_string_in_list(port, spec_ports) and\
                        not check_string_in_list(port, ports_for_first_and_second[index]):
                    ports_for_first_and_second[index].append(port)
            ports_for_first_and_second[index] = sorted(ports_for_first_and_second[index])

        return ports_for_first_and_second

    def _get_selected_uris(self) -> Tuple[List[str], List[str]]:
        """
        :return: a list of entered URIs for measurers and a list of different URIs.
        """

        uris = []
        for combo_box in self.combo_boxes_measurers:
            if not combo_box.isVisible() or not self._uri_checker.check_uri_for_correctness(combo_box):
                continue
            uris.append(combo_box.currentText())
        return uris, ut.get_different_uris(uris)

    def _init_asa(self, uri: str = None) -> None:
        """
        Method initializes available URIs for first measurer of type ASA.
        :param uri: selected address for first measurer.
        """

        ip_addresses = ut.reveal_asa()
        ip_addresses.sort()
        uris_for_first = [f"xmlrpc://{host}" for host in ip_addresses]
        uris_for_first.append("virtual")
        self.combo_boxes_measurers[0].clear()
        self.combo_boxes_measurers[0].addItems(uris_for_first)
        if uri in uris_for_first:
            self.combo_boxes_measurers[0].setCurrentText(uri)
        else:
            self.combo_boxes_measurers[0].setCurrentText("virtual")

        self._uri_checker.color_widgets(*self.combo_boxes_measurers)

    def _init_ivm10(self, port_1: str = None, port_2: str = None) -> None:
        """
        Method initializes available ports for first and second measurers of type IVM10.
        :param port_1: selected port for first measurer;
        :param port_2: selected port for second measurer.
        """

        ports = [port_1, port_2] if self._show_two_channels else [port_1, None]
        for index, port in enumerate(ports):
            if port is None or not URIChecker.check_ivm10(port):
                ports[index] = None

        available_ports = ut.find_urpc_ports("ivm")
        ports_for_first_and_second = self._get_ports_for_ivm10(available_ports, *ports)
        for index, combo_box in enumerate(self.combo_boxes_measurers):
            combo_box.clear()
            combo_box.addItems(ports_for_first_and_second[index])
            if not set_current_item(combo_box, ports[index]):
                combo_box.setCurrentText("virtual")
        if port_1 is None and port_2 is None:
            self._set_real_ivm10_ports()

        self._uri_checker.color_widgets(*self.combo_boxes_measurers)

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget.
        """

        self.setFocusPolicy(Qt.ClickFocus)
        grid_layout = QGridLayout()
        self.buttons_show_help: List[QPushButton] = []
        self.combo_boxes_measurers: List[QComboBox] = []
        self.labels_measurers: List[QLabel] = []
        for index in range(2):
            label = QLabel(qApp.translate("connection_window", "Канал #{}").format(index + 1))
            grid_layout.addWidget(label, index, 0)
            self.labels_measurers.append(label)

            combo_box = QComboBox()
            combo_box.setMinimumWidth(MeasurerURIsWidget.COMBO_BOX_MIN_WIDTH)
            combo_box.setEditable(True)
            combo_box.textActivated.connect(self.change_uris)
            combo_box.installEventFilter(self)
            grid_layout.addWidget(combo_box, index, 1)
            self.combo_boxes_measurers.append(combo_box)

            button = QPushButton()
            button.setIcon(QIcon(os.path.join(DIR_MEDIA, "info.png")))
            button.setToolTip(qApp.translate("connection_window", "Помощь"))
            button.setFixedWidth(MeasurerURIsWidget.BUTTON_HELP_WIDTH)
            button.clicked.connect(self.show_help)
            grid_layout.addWidget(button, index, 3)
            self.buttons_show_help.append(button)

        self.button_update: QPushButton = QPushButton()
        self.button_update.setFixedWidth(MeasurerURIsWidget.BUTTON_UPDATE_WIDTH)
        self.button_update.setIcon(QIcon(os.path.join(DIR_MEDIA, "update.png")))
        self.button_update.setToolTip(qApp.translate("connection_window", "Обновить"))
        self.button_update.clicked.connect(self.update_uris)
        grid_layout.addWidget(self.button_update, 0, 2)
        self.setLayout(grid_layout)

    def _set_real_ivm10_ports(self) -> None:
        """
        Method sets real IVM10 measurer ports as to current ports.
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
    def change_uris(self) -> None:
        """
        Slot handles signal that URI for measurer was changed.
        """

        uris = [combo_box.currentText() for combo_box in self.combo_boxes_measurers if combo_box.isVisible()]
        if self._measurer_type == MeasurerType.IVM10:
            self._init_ivm10(*uris)
        else:
            self._init_asa(uris[0])

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        :param obj: the object with which the event occurred;
        :param event: event.
        :return: to filter the event out, i.e. stop it being handled further, return True, otherwise return False.
        """

        if isinstance(event, QFocusEvent):
            for combo_box in self.combo_boxes_measurers:
                if obj == combo_box:
                    self._uri_checker.color_widget(obj, QFocusEvent(event))
        return False

    def get_selected_uris(self) -> List[str]:
        """
        Method returns selected URIs for measurers.
        :return: list with selected URIs.
        """

        uris = self._get_selected_uris()[1]
        while len(uris) < 2:
            uris.append(None)

        for index, uri in enumerate(uris):
            if uri and uri.lower() == "virtual" and self._measurer_type == MeasurerType.ASA:
                uris[index] = "virtualasa"
        return uris

    @pyqtSlot(MeasurerType, bool)
    def set_measurer_type(self, measurer_type: MeasurerType, show_two_channels: bool) -> None:
        """
        Slot sets new measurer type.
        :param measurer_type: new measurer type;
        :param show_two_channels: True if two channels (ports for measurers) should be shown.
        """

        self._show_two_channels = show_two_channels
        self._measurer_type = measurer_type
        self._uri_checker.set_measurer_type(measurer_type)
        if measurer_type == MeasurerType.IVM10:
            placeholder_text = MeasurerURIsWidget.PLACEHOLDER_IVM
            self._init_ivm10(*self._initial_uris)
        else:
            placeholder_text = MeasurerURIsWidget.PLACEHOLDER_ASA
            self._init_asa(self._initial_uris[0])
        for combo_box in self.combo_boxes_measurers:
            combo_box.lineEdit().setPlaceholderText(placeholder_text)

        self.buttons_show_help[1].setVisible(show_two_channels)
        self.combo_boxes_measurers[1].setVisible(show_two_channels)
        self.labels_measurers[1].setVisible(show_two_channels)

    @pyqtSlot()
    def show_help(self) -> None:
        """
        Slot shows help information how to enter URI.
        """

        if self._measurer_type == MeasurerType.IVM10:
            port_format = "com:///dev/ttyx" if ut.get_platform() == "debian" else "com:\\\\.\\COMx"
            info = qApp.translate("connection_window", "Введите значение последовательного порта в формате {}."
                                  ).format(port_format)
        else:
            info = qApp.translate("connection_window", "Введите адрес сервера H10 в формате xmlrpc://x.x.x.x.")
        show_message(qApp.translate("connection_window", "Помощь"), info, icon=QMessageBox.Information)

    def validate(self) -> bool:
        """
        Method checks that there are correct values for URIs.
        :return: True if values for URIs are correct.
        """

        if not self._check_uri_correctness():
            self.show_help()
            return False

        uris, different_uris = self._get_selected_uris()
        if len(uris) != len(different_uris):
            show_message(qApp.translate("t", "Ошибка"), qApp.translate("connection_window", "Введите разные порты."))
            return False

        return True

    @pyqtSlot()
    def update_uris(self) -> None:
        """
        Slot updates URIs for measurers.
        """

        if self._measurer_type == MeasurerType.IVM10:
            self._init_ivm10(*self._initial_uris)
        else:
            self._init_asa()


def check_string_in_list(string: Optional[str], list_of_strings: List[Optional[str]]) -> bool:
    """
    :param string: string;
    :param list_of_strings: list with strings.
    :return: True if the string is in the list, False otherwise. It is taken into account that in Windows strings
    do not differ in case, but in Linux they do.
    """

    return get_string_index_in_list(string, list_of_strings) is not None


def get_string_index_in_list(string: Optional[str], list_of_strings: List[Optional[str]]) -> Optional[int]:
    """
    :param string: string;
    :param list_of_strings: list with strings.
    :return: index of the element that matches the given string in the list.
    """

    def get_string_to_compare(str_: str) -> str:
        return str_ if str_ is None or ut.get_platform() == "debian" else str_.lower()

    str_cmp = get_string_to_compare(string)
    for i, str_from_list in enumerate(list_of_strings):
        str_from_list_cmp = get_string_to_compare(str_from_list)
        if str_from_list_cmp == str_cmp:
            return i
    return None


def set_current_item(widget: QComboBox, text: Optional[str]) -> bool:
    """
    :param widget: combo box widget;
    :param text: text to set as current in the widget.
    :return: True if the given text is set as current.
    """

    if text is None:
        return False

    for i in range(widget.count()):
        item_text = widget.itemText(i)
        if check_string_in_list(text, [item_text]):
            widget.setCurrentIndex(i)
            return True

    return False
