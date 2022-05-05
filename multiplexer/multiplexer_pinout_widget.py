"""
File with class for widget to show multiplexer pinout.
"""

from typing import Dict, List
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt
from epcore.analogmultiplexer import AnalogMultiplexerBase, ModuleTypes
from epcore.elements import MultiplexerOutput


class ChannelWidget(qt.QWidget):
    """
    Class to show single channel of module.
    """

    COLOR_BORDER = "blue"
    COLOR_NORMAL = "white"
    COLOR_SELECTED = "green"
    COLOR_TURNED_ON = "red"
    SIZE = 5
    selected = pyqtSignal(bool, int)
    turned_on = pyqtSignal(bool, int)

    def __init__(self, channel_number: int, up: bool = True):
        """
        :param channel_number: channel number on module;
        :param up: if True then channel number should be displayed on top
        of widget.
        """

        super().__init__()
        self.check_box_select_channel: qt.QCheckBox = None
        self.label_channel_number: qt.QLabel = None
        self.radio_button_turn_on_off: qt.QRadioButton = None
        self._channel_number: int = channel_number
        self._selected: bool = False
        self._dont_send_signal: bool = False
        self._turned_on: bool = False
        self._init_ui(up)

    def _init_ui(self, up: bool):
        """
        Method initializes widgets on channel widget.
        :param up: if True then channel number should be displayed on top
        of widget.
        """

        self.label_channel_number = qt.QLabel(str(self._channel_number))
        self.label_channel_number.setStyleSheet("border: none;")
        self.radio_button_turn_on_off = qt.QRadioButton()
        tooltip = qApp.translate("t", "Включить/выключить канал {}")
        self.radio_button_turn_on_off.setToolTip(tooltip.format(self._channel_number))
        self.radio_button_turn_on_off.toggled.connect(self.send_to_turn_on_off)
        self.radio_button_turn_on_off.setStyleSheet(
            "QRadioButton {border: none;}"
            f"QRadioButton::indicator {{width: {self.SIZE}px; height: {self.SIZE}px; border: 1px solid "
            f"{self.COLOR_BORDER}; border-radius: {self.SIZE / 2}px;}}"
            f"QRadioButton::indicator:checked {{border: 1px solid {self.COLOR_TURNED_ON};"
            f" background-color: {self.COLOR_TURNED_ON}}}"
            f"QRadioButton::indicator:unchecked {{border: 1px solid {self.COLOR_BORDER};"
            f" background-color: {self.COLOR_NORMAL}}}")
        self.radio_button_turn_on_off.setFixedSize(self.SIZE + 2, self.SIZE + 2)
        self.check_box_select_channel = qt.QCheckBox()
        tooltip = qApp.translate("t", "Выбрать канал {}")
        self.check_box_select_channel.setToolTip(tooltip.format(self._channel_number))
        self.check_box_select_channel.stateChanged.connect(self.send_to_select_channel)
        self.check_box_select_channel.setStyleSheet(
            "QCheckBox {border: none; spacing: 0px;}"
            f"QCheckBox::indicator {{width: {self.SIZE}px; height: {self.SIZE}px; border: 1px solid "
            f"{self.COLOR_BORDER}}}"
            f"QCheckBox::indicator:checked {{border: 1px solid {self.COLOR_SELECTED};"
            f" background-color: {self.COLOR_SELECTED}}}"
            f"QCheckBox::indicator:unchecked {{border: 1px solid {self.COLOR_BORDER};"
            f" background-color: {self.COLOR_NORMAL}}}")
        self.check_box_select_channel.setFixedSize(self.SIZE + 2, self.SIZE + 2)
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.setSpacing(0)
        h_box_layout.addWidget(self.radio_button_turn_on_off)
        h_box_layout.addWidget(self.check_box_select_channel)
        v_box_layout = qt.QVBoxLayout()
        if up:
            v_box_layout.addWidget(self.label_channel_number, alignment=Qt.AlignHCenter)
            v_box_layout.addLayout(h_box_layout)
        else:
            v_box_layout.addLayout(h_box_layout)
            v_box_layout.addWidget(self.label_channel_number, alignment=Qt.AlignHCenter)
        v_box_layout.setSpacing(0)
        v_box_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(v_box_layout)
        tooltip = qApp.translate("t", "Канал {}")
        self.setToolTip(tooltip.format(self._channel_number))

    @pyqtSlot(int)
    def send_to_select_channel(self, state: int):
        """
        Slot sends signal that channel was selected.
        :param state: state.
        """

        self.selected.emit(state == Qt.Checked, self._channel_number)

    @pyqtSlot(bool)
    def send_to_turn_on_off(self, state: bool):
        """
        Slot sends signal that channel was turned on or turned off.
        :param state: if True then channel was turned on.
        """

        if self._dont_send_signal:
            self._dont_send_signal = False
            return
        self.turned_on.emit(state, self._channel_number)

    def turn_off(self):
        """
        Method turns off channel.
        """

        self._dont_send_signal = True
        self.radio_button_turn_on_off.setChecked(False)


class ModuleWidget(qt.QWidget):
    """
    Class to show single module of multiplexer.
    """

    COLOR_NORMAL = "blue"
    COLOR_SELECTED = "red"
    MAX_CHANNEL_NUMBER = 64
    module_turned_on = pyqtSignal(MultiplexerOutput)
    module_turned_off = pyqtSignal(MultiplexerOutput)

    def __init__(self, module_type: ModuleTypes, module_number: int):
        """
        :param module_type: module type;
        :param module_number: module number.
        """

        super().__init__()
        self.frame_module: qt.QFrame = None
        self._module_number: int = module_number
        self._module_type: ModuleTypes = module_type
        self._channels: Dict[int, ChannelWidget] = {}
        self._selected_channels: List[ChannelWidget] = []
        self._turned_on_channel: ChannelWidget = None
        self._init_ui()

    def _change_module_color(self):
        """
        Method changes color of module.
        """

        color = self.COLOR_SELECTED if self._turned_on_channel else self.COLOR_NORMAL
        self.frame_module.setStyleSheet(f"border: 2px solid {color};")

    def _create_pinout(self):
        """
        Method creates widgets for channels in module.
        """

        self.frame_module = qt.QWidget()
        self.frame_module.setStyleSheet(f"border: 2px solid {self.COLOR_NORMAL};")
        grid_layout = qt.QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        for index in range(self.MAX_CHANNEL_NUMBER):
            column = index // 2
            row = index % 2
            channel = ChannelWidget(index + 1, row == 0)
            channel.turned_on.connect(self.turn_on_off_channel)
            self._channels[index + 1] = channel
            grid_layout.addWidget(channel, row, column)
        self.frame_module.setLayout(grid_layout)

    def _init_ui(self):
        """
        Method initializes widgets on module widget.
        """

        self._create_pinout()
        label_module_number = qt.QLabel(str(self._module_number))
        label_module_number.setStyleSheet("border: none; font-weight: bold; font-size: large;")
        label_module_number.setToolTip(qApp.translate("t", "Номер модуля"))
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.setContentsMargins(0, 0, 0, 0)
        h_box_layout.addWidget(label_module_number, alignment=Qt.AlignVCenter)
        h_box_layout.addWidget(self.frame_module)
        h_box_layout.addStretch(1)
        self.setLayout(h_box_layout)
        tooltip = qApp.translate("t", "Модуль {} {}")
        self.setToolTip(tooltip.format(self._module_type, self._module_number))

    def set_connected_channel(self, channel_number: int):
        """
        Method sets given channel of module as turned on.
        :param channel_number: channel number.
        """

        self._channels[channel_number].radio_button_turn_on_off.setChecked(True)

    @pyqtSlot(bool, int)
    def turn_on_off_channel(self, state: bool, channel_number: int):
        """
        Slot turns on or turns off channel.
        :param state: if True then channel should be turned on;
        :param channel_number: channel number to be turned on or off.
        """

        if state:
            if self._turned_on_channel:
                self._turned_on_channel.turn_off()
            self._turned_on_channel = self._channels[channel_number]
            output = MultiplexerOutput(channel_number=channel_number, module_number=self._module_number)
            self.module_turned_on.emit(output)
        else:
            if self._turned_on_channel and self._turned_on_channel == self._channels[channel_number]:
                output = MultiplexerOutput(channel_number=channel_number, module_number=self._module_number)
                self.module_turned_off.emit(output)
                self._turned_on_channel = None
        self._change_module_color()

    def turn_off(self):
        """
        Method turns off channels of module.
        """

        if self._turned_on_channel:
            self._turned_on_channel.turn_off()
            self._turned_on_channel = None
        self._change_module_color()


class MultiplexerPinoutWidget(qt.QWidget):
    """
    Class to show multiplexer pinout.
    """

    def __init__(self, parent):
        """
        :param parent: parent main window.
        """

        super().__init__()
        self.check_box_select_all: qt.QCheckBox = None
        self.button_add_points_to_plan: qt.QPushButton = None
        self.button_start_or_stop_entire_plan_measurement: qt.QPushButton = None
        self._parent = parent
        self._modules: Dict[int, ModuleWidget] = {}
        self._multiplexer: AnalogMultiplexerBase = self._parent.measurement_plan.multiplexer
        self._turned_on_output: MultiplexerOutput = None
        self._init_ui()

    def _create_empty_widget(self):
        """
        Method creates empty widget.
        """

        label = qt.QLabel(qApp.translate("t", "Нет мультиплексора"))
        label.setStyleSheet("font-weight: bold; font-size: x-large;")
        layout = qt.QVBoxLayout()
        layout.addWidget(label, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

    def _init_ui(self):
        """
        Method initializes widgets on main widget.
        """

        if self._multiplexer:
            v_box_layout = qt.QVBoxLayout()
            chain = self._multiplexer.get_chain_info()
            chain.reverse()
            module_index = len(chain)
            for module_type in chain:
                module = ModuleWidget(module_type, module_index)
                module.module_turned_on.connect(self.turn_on_output)
                module.module_turned_off.connect(self.turn_off_output)
                self._modules[module_index] = module
                v_box_layout.addWidget(module)
                module_index -= 1
            connected_output = self._multiplexer.get_connected_channel()
            if connected_output:
                self._modules[connected_output.module_number].set_connected_channel(connected_output.channel_number)
                self._turned_on_output = connected_output
            scroll_area = qt.QScrollArea()
            scroll_area.setWidgetResizable(True)
            widget = qt.QWidget()
            widget.setLayout(v_box_layout)
            scroll_area.setWidget(widget)
            self.check_box_select_all = qt.QCheckBox(qApp.translate("t", "Выбрать все"))
            self.check_box_select_all.setChecked(True)
            name_and_tooltip = qApp.translate("t", "Добавить точки в план тестирования")
            self.button_add_points_to_plan = qt.QPushButton(name_and_tooltip)
            self.button_add_points_to_plan.setToolTip(name_and_tooltip)
            self.button_add_points_to_plan.clicked.connect(self.add_points_to_plan)
            name_and_tooltip = qApp.translate("t", "Запустить измерение всего плана")
            self.button_start_or_stop_entire_plan_measurement = qt.QPushButton(name_and_tooltip)
            self.button_start_or_stop_entire_plan_measurement.setToolTip(name_and_tooltip)
            self.button_start_or_stop_entire_plan_measurement.setCheckable(True)
            self.button_start_or_stop_entire_plan_measurement.toggled.connect(self.start_or_stop_plan_measurement)
            h_box_layout = qt.QHBoxLayout()
            h_box_layout.addWidget(self.check_box_select_all)
            h_box_layout.addStretch(1)
            h_box_layout.addWidget(self.button_add_points_to_plan)
            h_box_layout.addWidget(self.button_start_or_stop_entire_plan_measurement)
            layout = qt.QVBoxLayout()
            layout.addWidget(scroll_area)
            layout.addLayout(h_box_layout)
            layout.addStretch(1)
            self.setLayout(layout)
        else:
            self._create_empty_widget()

    @pyqtSlot()
    def add_points_to_plan(self):
        """
        Slot adds selected multiplexer channels to measurement plan.
        """

        pass

    @pyqtSlot()
    def start_or_stop_plan_measurement(self):
        pass

    @pyqtSlot(MultiplexerOutput)
    def turn_on_output(self, output: MultiplexerOutput):
        """
        Slot turns on output of multiplexer.
        :param output: output to turn on.
        """

        self._multiplexer.connect_channel(output)
        if self._turned_on_output and output.module_number != self._turned_on_output.module_number:
            self._modules[self._turned_on_output.module_number].turn_off()
        self._turned_on_output = output

    @pyqtSlot(MultiplexerOutput)
    def turn_off_output(self, output: MultiplexerOutput):
        """
        Slot turns off output of multiplexer.
        :param output: output to turn off.
        """

        if self._turned_on_output == output:
            self._multiplexer.disconnect_all_channels()
            self._turned_on_output = None
