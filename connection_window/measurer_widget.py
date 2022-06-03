"""
File with classes to select measurers.
"""

import os
from functools import partial
from typing import Dict, List
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QIcon, QPixmap, QRegExpValidator
import connection_window.utils as ut


class MeasurerTypeWidget(qt.QWidget):
    """
    Class for widget to select measurer type.
    """

    IMAGE_HEIGHT: int = 100
    IMAGE_WIDTH: int = 100
    WIDGET_HEIGHT: int = 300
    WIDGET_WIDTH: int = 300
    measurer_type_changed: pyqtSignal = pyqtSignal(ut.MeasurerType, bool)

    def __init__(self, initial_product_name: ut.ProductNames = None):
        """
        :param initial_product_name: initial product name.
        """

        super().__init__()
        self.radio_buttons_products: Dict[ut.ProductNames, qt.QRadioButton] = None
        if initial_product_name is None:
            initial_product_name = ut.ProductNames.EYEPOINT_A2
        self._initial_product_name: ut.ProductNames = initial_product_name
        self._init_ui()

    def _init_ui(self):
        """
        Method initializes widgets on main widget.
        """

        widget = qt.QWidget()
        scroll_area = qt.QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        layout = qt.QVBoxLayout()
        layout.addWidget(scroll_area)
        grid_layout = qt.QGridLayout()
        widget.setLayout(grid_layout)
        self.radio_buttons_products = {}
        for row, product_name in enumerate(ut.ProductNames.get_product_names_for_platform()):
            radio_button = qt.QRadioButton(product_name.value, self)
            radio_button.setToolTip(product_name.value)
            measurer_type = ut.ProductNames.get_measurer_type_by_product_name(product_name)
            radio_button.toggled.connect(partial(self.select_measurer_type, measurer_type))
            product_image = QPixmap(os.path.join(ut.DIR_MEDIA, f"{product_name.value}.png"))
            label = qt.QLabel("")
            label.setPixmap(product_image.scaled(self.IMAGE_WIDTH, self.IMAGE_HEIGHT, Qt.KeepAspectRatio))
            label.setToolTip(product_name.value)
            grid_layout.addWidget(label, row, 0)
            grid_layout.addWidget(radio_button, row, 1)
            self.radio_buttons_products[product_name] = radio_button
        self.radio_buttons_products[self._initial_product_name].setChecked(True)
        self.setToolTip(qApp.translate("t", "Тип измерителя"))
        self.setFixedSize(self.WIDGET_WIDTH, self.WIDGET_HEIGHT)
        self.setLayout(layout)

    def get_product_name(self) -> ut.ProductNames:
        """
        Method returns checked product name.
        :return: product name.
        """

        for product_name, radio_button in self.radio_buttons_products.items():
            if radio_button.isChecked():
                return product_name

    @pyqtSlot(ut.MeasurerType, bool)
    def select_measurer_type(self, measurer_type: ut.MeasurerType, radio_button_status: bool):
        """
        Slot handles signal that new measurer type was selected.
        :param measurer_type: selected measurer type;
        :param radio_button_status: if True then radio button was checked.
        """

        if not radio_button_status:
            return
        show_two_channels = self.get_product_name() not in ut.ProductNames.get_single_channel_products()
        self.measurer_type_changed.emit(measurer_type, show_two_channels)

    def send_initial_values(self):
        """
        Method emits signal.
        """

        measurer_type = ut.ProductNames.get_measurer_type_by_product_name(self._initial_product_name)
        self.select_measurer_type(measurer_type, True)


class MeasurerURLsWidget(qt.QWidget):
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

    def __init__(self, initial_ports: List[str]):
        """
        :param initial_ports: initial ports of measurers.
        """

        super().__init__()
        self.button_update: qt.QPushButton = None
        self.buttons_show_help: List[qt.QPushButton] = []
        self.combo_boxes_measurers: List[qt.QComboBox] = []
        self.labels_measurers: List[qt.QLabel] = []
        self._initial_ports: List[str] = initial_ports
        self._measurer_type: ut.MeasurerType = None
        self._show_two_channels: bool = None
        self._init_ui()

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
            ports_list = [port] if port is not None and ut.IVM10_PATTERN[ut.get_platform()].match(port) else []
            ports_for_first_and_second.append(ports_list)
            if len(ports) > 0:
                if port in ports and port != ut.MeasurerType.IVM10_VIRTUAL.value:
                    ports.remove(port)
        for index in range(2):
            ports_for_first_and_second[index] = [*ports_for_first_and_second[index], *ports]
            if ut.MeasurerType.IVM10_VIRTUAL.value not in ports_for_first_and_second[index]:
                ports_for_first_and_second[index].append(ut.MeasurerType.IVM10_VIRTUAL.value)
            if selected_ports[index] != ut.MeasurerType.IVM10_VIRTUAL.value:
                try:
                    ports_for_first_and_second[index - 1].remove(selected_ports[index])
                except ValueError:
                    pass
            spec_ports = [*selected_ports, None, ut.MeasurerType.IVM10_VIRTUAL.value]
            for port in self._initial_ports:
                if port not in spec_ports and port is not None and ut.IVM10_PATTERN[ut.get_platform()].match(port) and\
                        port not in ports_for_first_and_second[index]:
                    ports_for_first_and_second[index].append(port)
            ports_for_first_and_second[index] = sorted(ports_for_first_and_second[index])
        return ports_for_first_and_second

    def _init_asa(self, url: str = None):
        """
        Method initializes available ports for first measurer of type ASA.
        :param url: selected address for first measurer.
        """

        urls_for_first = [f"xmlrpc://{host}" for host in ut.reveal_asa()]
        urls_for_first.append("virtual")
        self.combo_boxes_measurers[0].clear()
        self.combo_boxes_measurers[0].addItems(urls_for_first)
        if url in urls_for_first:
            self.combo_boxes_measurers[0].setCurrentText(url)
        else:
            self.combo_boxes_measurers[0].setCurrentText("virtual")

    def _init_ivm10(self, port_1: str = None, port_2: str = None):
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

    def _init_ui(self):
        """
        Method initializes widgets on main widget.
        """

        grid_layout = qt.QGridLayout()
        for index in range(1, 3):
            label_text = qApp.translate("t", "Канал #{}")
            label = qt.QLabel(label_text.format(index))
            grid_layout.addWidget(label, index - 1, 0)
            self.labels_measurers.append(label)
            combo_box = qt.QComboBox()
            combo_box.setMinimumWidth(self.COMBO_BOX_MIN_WIDTH)
            combo_box.setEditable(True)
            combo_box.setToolTip(label_text.format(index))
            combo_box.textActivated.connect(self.change_ports)
            grid_layout.addWidget(combo_box, index - 1, 1)
            self.combo_boxes_measurers.append(combo_box)
            if index == 1:
                self.button_update = qt.QPushButton()
                self.button_update.setFixedWidth(self.BUTTON_UPDATE_WIDTH)
                self.button_update.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "update.png")))
                self.button_update.setToolTip(qApp.translate("t", "Обновить"))
                self.button_update.clicked.connect(self.update_ports)
                grid_layout.addWidget(self.button_update, index - 1, 2)
            button = qt.QPushButton()
            button.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "info.png")))
            button.setToolTip(qApp.translate("t", "Помощь"))
            button.setFixedWidth(self.BUTTON_HELP_WIDTH)
            button.clicked.connect(self.show_help)
            grid_layout.addWidget(button, index - 1, 3)
            self.buttons_show_help.append(button)
        self.setLayout(grid_layout)

    def _set_real_ivm10_ports(self):
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
    def change_ports(self):
        """
        Slot handles signal that port for measurer was changed.
        """

        ports = [combo_box.currentText() for combo_box in self.combo_boxes_measurers if combo_box.isVisible()]
        if self._measurer_type == ut.MeasurerType.IVM10:
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

    @pyqtSlot(ut.MeasurerType, bool)
    def set_measurer_type(self, measurer_type: ut.MeasurerType, show_two_channels: bool):
        """
        Slot sets new measurer type.
        :param measurer_type: new measurer type;
        :param show_two_channels: True if two channels (ports for measurers) should be shown.
        """

        self._show_two_channels = show_two_channels
        self._measurer_type = measurer_type
        if measurer_type == ut.MeasurerType.IVM10:
            placeholder_text = self.PLACEHOLDER_IVM.format(qApp.translate("t", "или"))
            validator = QRegExpValidator(QRegExp(self.IP_IVM10_REG_EXP), self)
            self._init_ivm10(*self._initial_ports)
        else:
            placeholder_text = self.PLACEHOLDER_ASA
            validator = QRegExpValidator(QRegExp(self.IP_ASA_REG_EXP), self)
            self._init_asa(self._initial_ports[0])
        for combo_box in self.combo_boxes_measurers:
            combo_box.setValidator(validator)
            combo_box.lineEdit().setPlaceholderText(placeholder_text)
        self.buttons_show_help[1].setVisible(show_two_channels)
        self.combo_boxes_measurers[1].setVisible(show_two_channels)
        self.labels_measurers[1].setVisible(show_two_channels)

    @pyqtSlot()
    def show_help(self):
        """
        Slot shows help information how to enter COM-port or server address.
        """

        msg_box = qt.QMessageBox()
        msg_box.setIcon(qt.QMessageBox.Information)
        msg_box.setWindowTitle(qApp.translate("t", "Помощь"))
        msg_box.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "ico.png")))
        if self._measurer_type == ut.MeasurerType.IVM10:
            if "win" in ut.get_platform():
                info = qApp.translate("t", "Введите значение последовательного порта в формате com:\\\\.\\COMx или "
                                           "адрес XiNet сервера в формате xi-net://x.x.x.x/x.")
            else:
                info = qApp.translate("t", "Введите значение последовательного порта в формате com:///dev/ttyACMx или "
                                           "адрес XiNet сервера в формате xi-net://x.x.x.x/x.")
        else:
            info = qApp.translate("t", "Введите адрес сервера H10 в формате xmlrpc://x.x.x.x.")
        msg_box.setText(info)
        msg_box.exec_()

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
    def update_ports(self):
        """
        Slot updates ports for measurers.
        """

        if self._measurer_type == ut.MeasurerType.IVM10:
            self._init_ivm10(*self._initial_ports)
        else:
            self._init_asa()
