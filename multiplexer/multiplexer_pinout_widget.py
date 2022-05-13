"""
File with class for widget to show multiplexer pinout.
"""

from typing import Dict, List
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt, QTimer
from epcore.analogmultiplexer import ModuleTypes
from epcore.elements import MultiplexerOutput
from common import WorkMode


class ChannelWidget(qt.QWidget):
    """
    Class to show single channel of module.
    """

    COLOR_BORDER = "blue"
    COLOR_NORMAL = "white"
    COLOR_SELECTED = "green"
    COLOR_TURNED_ON = "red"
    SIZE = 5
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

    def is_selected(self) -> bool:
        """
        Method returns True if channel was selected.
        :return: True if channel was selected.
        """

        return self.check_box_select_channel.isChecked()

    def enable_select_widget(self, state):
        """
        Method enables or disables check box widget to select channel.
        :param state: if True then check box will be enabled.
        """

        self.check_box_select_channel.setEnabled(state)

    def select_channel(self, state):
        """
        Method selects or unselects channel.
        :param state: if True then channel should be selected.
        """

        self.check_box_select_channel.setChecked(state)

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

    def enable_select_channels(self, state: bool):
        """
        Method enables or disables widgets on channel widgets to select channel.
        :param state: if True then select widgets will be enabled.
        """

        for channel in self._channels.values():
            channel.enable_select_widget(state)

    def get_selected_channels(self) -> List[MultiplexerOutput]:
        """
        Method returns selected channels for given module.
        :return: list with selected channels.
        """

        selected_channels = []
        for channel_number in sorted(self._channels.keys()):
            channel = self._channels[channel_number]
            if channel.is_selected():
                selected_channels.append(MultiplexerOutput(channel_number=channel_number,
                                                           module_number=self._module_number))
        return selected_channels

    def select_all_channels(self, state: bool):
        """
        Method selects or unselects all channels of module.
        :param state: if True then all channels should be selected.
        """

        for channel in self._channels.values():
            channel.select_channel(state)

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

    channel_added = pyqtSignal(MultiplexerOutput)
    process_started = pyqtSignal(int)
    process_finished = pyqtSignal()

    def __init__(self, parent):
        """
        :param parent: parent main window.
        """

        super().__init__()
        self.check_box_select_all: qt.QCheckBox = None
        self.button_add_points_to_plan: qt.QPushButton = None
        self.button_start_or_stop_entire_plan_measurement: qt.QPushButton = None
        self.label_no_mux: qt.QLabel = None
        self.layout_for_modules: qt.QVBoxLayout = None
        self.scroll_area: qt.QScrollArea = None
        self._parent = parent
        self._modules: Dict[int, ModuleWidget] = {}
        self._selected_channels: List[MultiplexerOutput] = []
        self._timer: QTimer = QTimer()
        self._timer.setInterval(10)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.send_selected_channel)
        self._turned_on_output: MultiplexerOutput = None
        self._init_ui()

    def _create_empty_widget(self):
        """
        Method creates empty widget.
        """

        self.label_no_mux = qt.QLabel(qApp.translate("t", "Нет мультиплексора"))
        self.label_no_mux.setStyleSheet("font-weight: bold; font-size: 25px;")

    def _create_widgets_for_multiplexer(self) -> qt.QLayout:
        """
        Method creates widgets to work with multiplexer.
        """

        self.layout_for_modules = qt.QVBoxLayout()
        self.layout_for_modules.addStretch(1)

        self.scroll_area = qt.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        widget = qt.QWidget()
        widget.setLayout(self.layout_for_modules)
        self.scroll_area.setWidget(widget)
        self.check_box_select_all = qt.QCheckBox(qApp.translate("t", "Выбрать все"))
        self.check_box_select_all.stateChanged.connect(self.select_all_channels)
        self.check_box_select_all.setChecked(True)
        name_and_tooltip = qApp.translate("t", "Добавить точки в план тестирования")
        self.button_add_points_to_plan = qt.QPushButton(name_and_tooltip)
        self.button_add_points_to_plan.setToolTip(name_and_tooltip)
        self.button_add_points_to_plan.clicked.connect(self.collect_selected_channels)
        name_and_tooltip = qApp.translate("t", "Запустить измерение всего плана")
        self.button_start_or_stop_entire_plan_measurement = qt.QPushButton(name_and_tooltip)
        self.button_start_or_stop_entire_plan_measurement.setToolTip(name_and_tooltip)
        self.button_start_or_stop_entire_plan_measurement.setCheckable(True)
        self.button_start_or_stop_entire_plan_measurement.toggled.connect(self.start_or_stop_plan_measurement)

    def _enable_widgets(self, state: bool):
        """
        Method enables or disables widgets on multiplexer pinout widget.
        :param state: if True then widgets will be enabled.
        """

        widgets = (self.button_add_points_to_plan, self.button_start_or_stop_entire_plan_measurement,
                   self.check_box_select_all)
        for widget in widgets:
            widget.setEnabled(state)
        for module in self._modules.values():
            module.enable_select_channels(state)

    def _init_ui(self):
        """
        Method initializes widgets on main widget.
        """

        self._create_widgets_for_multiplexer()
        self._create_empty_widget()
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addWidget(self.check_box_select_all)
        h_box_layout.addStretch(1)
        h_box_layout.addWidget(self.button_add_points_to_plan)
        h_box_layout.addWidget(self.button_start_or_stop_entire_plan_measurement)
        layout = qt.QVBoxLayout()
        layout.addWidget(self.scroll_area)
        layout.addLayout(h_box_layout)
        layout.addWidget(self.label_no_mux, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

    def _remove_all_modules(self):
        """
        Method removes all modules from widget.
        """

        for module in self._modules.values():
            self.layout_for_modules.removeWidget(module)
            module.deleteLater()
        self._modules = {}

    def _set_visible(self):
        """
        Method sets widgets to visible state.
        """

        widgets = (self.button_add_points_to_plan, self.button_start_or_stop_entire_plan_measurement,
                   self.check_box_select_all, self.scroll_area)
        visible = bool(self._parent.measurement_plan and self._parent.measurement_plan.multiplexer)
        for widget in widgets:
            widget.setVisible(visible)
        self.label_no_mux.setVisible(not visible)

    def _update_modules(self):
        """
        Method updates modules for widget.
        """

        self._remove_all_modules()
        if not self._parent.measurement_plan.multiplexer:
            return
        chain = self._parent.measurement_plan.multiplexer.get_chain_info()
        module_index = 1
        for module_type in chain:
            module = ModuleWidget(module_type, module_index)
            module.module_turned_on.connect(self.turn_on_output)
            module.module_turned_off.connect(self.turn_off_output)
            self._modules[module_index] = module
            self.layout_for_modules.insertWidget(0, module)
            module_index += 1
        connected_output = self._parent.measurement_plan.multiplexer.get_connected_channel()
        if connected_output:
            self._modules[connected_output.module_number].set_connected_channel(connected_output.channel_number)
            self._turned_on_output = connected_output
        self._enable_widgets(len(chain) != 0)

    @pyqtSlot()
    def collect_selected_channels(self):
        """
        Slot collects selected multiplexer channels.
        """

        self._selected_channels = []
        for module_number in sorted(self._modules.keys()):
            module = self._modules[module_number]
            self._selected_channels.extend(module.get_selected_channels())
        if self._selected_channels:
            self.process_started.emit(len(self._selected_channels))
            self._timer.start()

    @pyqtSlot(int)
    def select_all_channels(self, state: int):
        """
        Slot selects or unselects all channels of modules.
        :param state: state of check box.
        """

        state = state == Qt.Checked
        for module in self._modules.values():
            module.select_all_channels(state)

    def send_selected_channel(self):
        """
        Method sends selected channel.
        """

        channel = self._selected_channels.pop(0)
        self.channel_added.emit(channel)
        if self._selected_channels:
            self._timer.start()
        else:
            self.process_finished.emit()

    def set_connected_channel(self, channel: MultiplexerOutput):
        """
        Method sets given channel of multiplexer as turned on.
        :param channel: connected channel.
        """

        if channel.module_number in self._modules:
            self._modules[channel.module_number].set_connected_channel(channel.channel_number)

    def set_work_mode(self, work_mode: WorkMode):
        """
        Method enables or disables widgets on multiplexer pinout widget according
        to given work mode.
        :param work_mode: work mode.
        """

        if work_mode != WorkMode.COMPARE and self._parent.measurement_plan and\
                self._parent.measurement_plan.multiplexer and\
                len(self._parent.measurement_plan.multiplexer.get_chain_info()):
            self._enable_widgets(True)
        else:
            self._enable_widgets(False)

    @pyqtSlot()
    def start_or_stop_plan_measurement(self):
        pass

    @pyqtSlot(MultiplexerOutput)
    def turn_on_output(self, output: MultiplexerOutput):
        """
        Slot turns on output of multiplexer.
        :param output: output to turn on.
        """

        self._parent.measurement_plan.multiplexer.connect_channel(output)
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
            self._parent.measurement_plan.multiplexer.disconnect_all_channels()
            self._turned_on_output = None

    def update_info(self):
        """
        Method updates information about multiplexer.
        """

        self._parent.measurement_plan.remove_all_callback_funcs_for_mux_output_change()
        self._parent.measurement_plan.add_callback_func_for_mux_output_change(self.set_connected_channel)
        self._turned_on_output = None
        self._update_modules()
        self._set_visible()
        self.select_all_channels(Qt.Checked)
