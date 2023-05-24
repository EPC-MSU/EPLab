"""
File with class for widget to show multiplexer pinout.
"""

import os
from typing import Dict, List, Optional
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt, QTimer
from PyQt5.QtGui import QIcon
from epcore.analogmultiplexer import ModuleTypes
from epcore.elements import MultiplexerOutput
from common import DeviceErrorsHandler, WorkMode


DIR_MEDIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")


class ChannelWidget(qt.QWidget):
    """
    Class to show single channel of module.
    """

    COLOR_TURNED_OFF: str = "#9ADAEB"
    COLOR_TURNED_ON: str = "#F9E154"
    SIZE: int = 13
    selected: pyqtSignal = pyqtSignal(bool)
    turned_on: pyqtSignal = pyqtSignal(bool, int)

    def __init__(self, channel_number: int, up: bool = True) -> None:
        """
        :param channel_number: channel number on module;
        :param up: if True then channel number should be displayed on top of widget.
        """

        super().__init__()
        self.button_turn_on_off: qt.QPushButton = None
        self.check_box_select_channel: qt.QCheckBox = None
        self._channel_number: int = channel_number
        self._init_ui(up)

    def _init_ui(self, up: bool) -> None:
        """
        Method initializes widgets on channel widget.
        :param up: if True then channel number should be displayed on top of widget.
        """

        self.button_turn_on_off = qt.QPushButton(str(self._channel_number))
        self.button_turn_on_off.setCheckable(True)
        tooltip = qApp.translate("t", "Включить/выключить канал {}")
        self.button_turn_on_off.setToolTip(tooltip.format(self._channel_number))
        self.button_turn_on_off.clicked.connect(self.send_to_turn_on_off)
        self.button_turn_on_off.setStyleSheet(
            f"QPushButton {{background-color: {self.COLOR_TURNED_OFF}; border: none; font: 10px; font-weight: bold;"
            f" spacing: 0px;}}"
            f"QPushButton:checked {{background-color: {self.COLOR_TURNED_ON}; border: none;}}")
        self.button_turn_on_off.setFixedSize(self.SIZE, self.SIZE)
        self.check_box_select_channel = qt.QCheckBox()
        tooltip = qApp.translate("t", "Выбрать канал {}")
        self.check_box_select_channel.setToolTip(tooltip.format(self._channel_number))
        self.check_box_select_channel.stateChanged.connect(self.send_to_select)
        self.check_box_select_channel.setStyleSheet("QCheckBox {border: none; spacing: 0px;}")
        self.check_box_select_channel.setFixedSize(self.SIZE, self.SIZE)
        v_box_layout = qt.QVBoxLayout()
        if up:
            v_box_layout.addWidget(self.button_turn_on_off, alignment=Qt.AlignHCenter)
            v_box_layout.addWidget(self.check_box_select_channel, alignment=Qt.AlignHCenter)
        else:
            v_box_layout.addWidget(self.check_box_select_channel, alignment=Qt.AlignHCenter)
            v_box_layout.addWidget(self.button_turn_on_off, alignment=Qt.AlignHCenter)
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

    def enable_select_widget(self, state) -> None:
        """
        Method enables or disables check box widget to select channel.
        :param state: if True then check box will be enabled.
        """

        self.check_box_select_channel.setEnabled(state)

    def select_channel(self, state: bool) -> None:
        """
        Method selects or unselects channel.
        :param state: if True then channel should be selected.
        """

        self.check_box_select_channel.setChecked(state)

    @pyqtSlot(int)
    def send_to_select(self, state: int) -> None:
        """
        Slot sends signal that channel was selected or unselected.
        :param state: state of check box widget.
        """

        self.selected.emit(state == Qt.Checked)

    @pyqtSlot(bool)
    def send_to_turn_on_off(self, state: bool) -> None:
        """
        Slot sends signal that channel was turned on or turned off.
        :param state: if True then channel was turned on.
        """

        self.turned_on.emit(state, self._channel_number)

    def turn_off(self) -> None:
        """
        Method turns off channel.
        """

        self.button_turn_on_off.setChecked(False)


class ModuleWidget(qt.QWidget):
    """
    Class to show single module of multiplexer.
    """

    COLOR_TURNED_OFF: str = "#186DB6"
    COLOR_TURNED_ON: str = "#D21404"
    MAX_CHANNEL_NUMBER: int = 64
    all_channels_selected: pyqtSignal = pyqtSignal(bool)
    module_turned_off: pyqtSignal = pyqtSignal(MultiplexerOutput)
    module_turned_on: pyqtSignal = pyqtSignal(MultiplexerOutput)

    def __init__(self, module_type: ModuleTypes, module_number: int) -> None:
        """
        :param module_type: module type;
        :param module_number: module number.
        """

        super().__init__()
        self.action_select_all_channels: qt.QAction = None
        self.frame_module: qt.QWidget = None
        self._channels: Dict[int, ChannelWidget] = {}
        self._module_number: int = module_number
        self._module_type: ModuleTypes = module_type
        self._turned_on_channel: ChannelWidget = None
        self._init_ui()

    def _change_module_color(self) -> None:
        """
        Method changes color of module.
        """

        color = self.COLOR_TURNED_ON if self._turned_on_channel else self.COLOR_TURNED_OFF
        self.frame_module.setStyleSheet(f"QWidget {{border: 2px solid {color}; border-radius: 3px;}}")

    def _create_context_menu(self) -> None:
        """
        Method creates context menu for module.
        """

        self.action_select_all_channels = qt.QAction(QIcon(os.path.join(DIR_MEDIA, "select.png")),
                                                     qApp.translate("t", "Выбрать все каналы"))
        self.action_select_all_channels.setCheckable(True)
        self.action_select_all_channels.triggered.connect(self.select_all_channels)
        self.addAction(self.action_select_all_channels)
        self.setContextMenuPolicy(Qt.ActionsContextMenu)

    def _create_pinout(self) -> None:
        """
        Method creates widgets for channels in module.
        """

        self.frame_module = qt.QWidget()
        self.frame_module.setStyleSheet(f"QWidget {{border: 2px solid {self.COLOR_TURNED_OFF}; border-radius: 3px;}}")
        grid_layout = qt.QGridLayout()
        grid_layout.setContentsMargins(2, 2, 2, 2)
        for index in range(self.MAX_CHANNEL_NUMBER):
            column = index // 2
            row = index % 2
            channel = ChannelWidget(index + 1, row == 0)
            channel.selected.connect(self.send_that_all_channels_selected)
            channel.turned_on.connect(self.turn_on_off_channel)
            self._channels[index + 1] = channel
            grid_layout.addWidget(channel, row, column)
        self.frame_module.setLayout(grid_layout)

    def _init_ui(self) -> None:
        """
        Method initializes widgets on module widget.
        """

        self._create_context_menu()
        self._create_pinout()
        label_module_number = qt.QLabel(str(self._module_number))
        label_module_number.setStyleSheet("QLabel {border: none; font-size: 15px; font-weight: bold;}")
        label_module_number.setToolTip(qApp.translate("t", "Номер модуля"))
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.setContentsMargins(0, 0, 0, 0)
        h_box_layout.addWidget(label_module_number, alignment=Qt.AlignVCenter)
        h_box_layout.addWidget(self.frame_module)
        h_box_layout.addStretch(1)
        self.setLayout(h_box_layout)
        tooltip = qApp.translate("t", "Модуль {}")
        self.setToolTip(tooltip.format(self._module_number))

    def check_selected_channels(self) -> bool:
        """
        Method checks if all channels of module are selected.
        :return: True if all channels are selected.
        """

        all_channels_selected = True
        for channel in self._channels.values():
            if not channel.is_selected():
                all_channels_selected = False
                break
        return all_channels_selected

    def enable_select_channels(self, state: bool) -> None:
        """
        Method enables or disables widgets on channel widgets to select channel.
        :param state: if True then select widgets will be enabled.
        """

        self.action_select_all_channels.setEnabled(state)
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

    def select_all_channels(self, state: bool) -> None:
        """
        Method selects or unselects all channels of module.
        :param state: if True then all channels should be selected.
        """

        for channel in self._channels.values():
            channel.select_channel(state)

    @pyqtSlot(bool)
    def send_that_all_channels_selected(self, state: bool) -> None:
        """
        Slot checks if all channels of module are selected and sends appropriate signal.
        :param state: new state of one of module's channel.
        """

        all_channels_selected = False if not state else self.check_selected_channels()
        self.action_select_all_channels.setChecked(all_channels_selected)
        self.all_channels_selected.emit(all_channels_selected)

    def set_connected_channel(self, channel_number: int) -> None:
        """
        Method sets given channel of module as turned on.
        :param channel_number: channel number.
        """

        self._channels[channel_number].button_turn_on_off.setChecked(True)
        self.turn_on_off_channel(True, channel_number)

    @pyqtSlot(bool, int)
    def turn_on_off_channel(self, state: bool, channel_number: int) -> None:
        """
        Slot turns on or turns off channel.
        :param state: if True then channel should be turned on;
        :param channel_number: channel number to be turned on or off.
        """

        if state:
            if self._turned_on_channel and self._turned_on_channel != self._channels[channel_number]:
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

    def turn_off(self) -> None:
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

    MIN_WIDTH: int = 500
    SCROLL_AREA_MIN_HEIGHT: int = 100
    TIMEOUT: int = 10
    adding_channels_finished: pyqtSignal = pyqtSignal()
    adding_channels_started: pyqtSignal = pyqtSignal(int)
    channel_added: pyqtSignal = pyqtSignal(MultiplexerOutput)

    def __init__(self, parent, device_errors_handler: Optional[DeviceErrorsHandler] = None) -> None:
        """
        :param parent: parent main window;
        :param device_errors_handler: device errors handler.
        """

        super().__init__()
        self.check_box_select_all: qt.QCheckBox = None
        self.button_add_points_to_plan: qt.QPushButton = None
        self.button_start_or_stop_entire_plan_measurement: qt.QPushButton = None
        self.label_no_mux: qt.QLabel = None
        self.layout_for_modules: qt.QVBoxLayout = None
        self.scroll_area: qt.QScrollArea = None
        self._device_errors_handler: DeviceErrorsHandler = device_errors_handler if device_errors_handler else\
            parent.device_errors_handler
        self._modules: Dict[int, ModuleWidget] = {}
        self._parent = parent
        self._selected_channels: List[MultiplexerOutput] = []
        self._timer: QTimer = QTimer()
        self._timer.setInterval(self.TIMEOUT)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.send_selected_channel)
        self._turned_on_output: MultiplexerOutput = None
        self._init_ui()

    def _create_empty_widget(self) -> None:
        """
        Method creates empty widget.
        """

        self.label_no_mux = qt.QLabel(qApp.translate("t", "Нет мультиплексора"))
        self.label_no_mux.setStyleSheet("QLabel {font-weight: bold; font-size: 25px;}")

    def _create_widgets_for_multiplexer(self) -> None:
        """
        Method creates widgets to work with multiplexer.
        """

        self.layout_for_modules = qt.QVBoxLayout()
        self.layout_for_modules.addStretch(1)
        self.scroll_area = qt.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(self.SCROLL_AREA_MIN_HEIGHT)
        widget = qt.QWidget()
        widget.setLayout(self.layout_for_modules)
        self.scroll_area.setWidget(widget)
        self.check_box_select_all = qt.QCheckBox(qApp.translate("t", "Выбрать все каналы"))
        self.check_box_select_all.clicked.connect(self.select_all_channels)
        self.check_box_select_all.setChecked(True)
        name_and_tooltip = qApp.translate("t", "Добавить выбранные каналы в план")
        self.button_add_points_to_plan = qt.QPushButton(name_and_tooltip)
        self.button_add_points_to_plan.setToolTip(name_and_tooltip)
        self.button_add_points_to_plan.setIcon(QIcon(os.path.join(DIR_MEDIA, "add_channels.png")))
        self.button_add_points_to_plan.clicked.connect(self.collect_selected_channels)
        name_and_tooltip = qApp.translate("t", "Запустить измерение всего плана")
        self.button_start_or_stop_entire_plan_measurement = qt.QPushButton(name_and_tooltip)
        self.button_start_or_stop_entire_plan_measurement.setIcon(QIcon(os.path.join(DIR_MEDIA, "start_auto_test.png")))
        self.button_start_or_stop_entire_plan_measurement.setToolTip(name_and_tooltip)
        self.button_start_or_stop_entire_plan_measurement.setCheckable(True)

    def _enable_widgets(self, state: bool) -> None:
        """
        Method enables or disables some widgets on multiplexer pinout widget.
        :param state: if True then widgets will be enabled.
        """

        widgets = (self.button_add_points_to_plan, self.button_start_or_stop_entire_plan_measurement,
                   self.check_box_select_all)
        for widget in widgets:
            widget.setEnabled(state)
        for module in self._modules.values():
            module.enable_select_channels(state)

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget.
        """

        self._create_widgets_for_multiplexer()
        self._create_empty_widget()
        self.setMinimumWidth(self.MIN_WIDTH)
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addWidget(self.check_box_select_all)
        h_box_layout.addStretch(1)
        v_box_layout = qt.QVBoxLayout()
        v_box_layout.addWidget(self.button_add_points_to_plan)
        v_box_layout.addWidget(self.button_start_or_stop_entire_plan_measurement)
        h_box_layout.addLayout(v_box_layout)
        layout = qt.QVBoxLayout()
        layout.addWidget(self.scroll_area)
        layout.addLayout(h_box_layout)
        layout.addWidget(self.label_no_mux, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

    def _remove_all_modules(self) -> None:
        """
        Method removes all modules from widget.
        """

        for module in self._modules.values():
            self.layout_for_modules.removeWidget(module)
            module.deleteLater()
        self._modules = {}

    def _update_modules(self) -> None:
        """
        Method updates modules for widget.
        """

        self._remove_all_modules()
        if not self._parent.measurement_plan.multiplexer:
            return
        with self._device_errors_handler:
            chain = self._parent.measurement_plan.multiplexer.get_chain_info()
            module_index = 1
            for module_type in chain:
                module = ModuleWidget(module_type, module_index)
                module.all_channels_selected.connect(self.check_selected_channels)
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

    @pyqtSlot(bool)
    def check_selected_channels(self, state: bool) -> None:
        """
        Slot checks if all channels of multiplexer are selected.
        :param state: new state of one of multiplexer's module.
        """

        all_channels_selected = False
        if state:
            all_channels_selected = True
            for module in self._modules.values():
                if not module.check_selected_channels():
                    all_channels_selected = False
                    break
        self.check_box_select_all.setChecked(all_channels_selected)

    @pyqtSlot()
    def collect_selected_channels(self) -> None:
        """
        Slot collects selected multiplexer channels.
        """

        self._selected_channels = []
        for module_number in sorted(self._modules.keys()):
            module = self._modules[module_number]
            self._selected_channels.extend(module.get_selected_channels())
        if self._selected_channels:
            self.adding_channels_started.emit(len(self._selected_channels))
            self._timer.start()

    def enable_widgets(self, state: bool) -> None:
        """
        Method enables or disables all widgets on multiplexer pinout widget.
        :param state: if True then widgets will be enabled.
        """

        self._enable_widgets(state)
        for module in self._modules.values():
            module.setEnabled(state)

    @pyqtSlot(bool)
    def select_all_channels(self, state: bool) -> None:
        """
        Slot selects or unselects all channels of modules.
        :param state: state of check box.
        """

        for module in self._modules.values():
            module.select_all_channels(state)

    def send_selected_channel(self) -> None:
        """
        Method sends selected channel.
        """

        channel = self._selected_channels.pop(0)
        self.channel_added.emit(channel)
        if self._selected_channels:
            self._timer.start()
        else:
            self.adding_channels_finished.emit()

    def set_connected_channel(self, channel: MultiplexerOutput) -> None:
        """
        Method sets given channel of multiplexer as turned on.
        :param channel: connected channel.
        """

        if channel.module_number in self._modules:
            self._modules[channel.module_number].set_connected_channel(channel.channel_number)

    def set_visible(self, status: Optional[bool] = None) -> None:
        """
        Method sets widgets to visible state.
        :param status: if True then widgets to work with multiplexer will be shown.
        """

        widgets = (self.button_add_points_to_plan, self.button_start_or_stop_entire_plan_measurement,
                   self.check_box_select_all, self.scroll_area)
        if status is None:
            visible = bool(self._parent.measurement_plan and self._parent.measurement_plan.multiplexer)
        else:
            visible = status
        for widget in widgets:
            widget.setVisible(visible)
        self.label_no_mux.setVisible(not visible)

    def set_work_mode(self, work_mode: WorkMode) -> None:
        """
        Method enables or disables widgets on multiplexer pinout widget according to given work mode.
        :param work_mode: work mode.
        """

        with self._device_errors_handler:
            if work_mode != WorkMode.COMPARE and self._parent.measurement_plan and\
                    self._parent.measurement_plan.multiplexer and\
                    len(self._parent.measurement_plan.multiplexer.get_chain_info()):
                self._enable_widgets(True)
            else:
                self._enable_widgets(False)

    def stop_sending_channels(self) -> None:
        """
        Method stops sending selected channels.
        """

        if self._timer.isActive():
            self._timer.stop()

    @pyqtSlot(MultiplexerOutput)
    def turn_off_output(self, output: MultiplexerOutput) -> None:
        """
        Slot turns off output of multiplexer.
        :param output: output to turn off.
        """

        with self._device_errors_handler:
            if self._turned_on_output == output:
                self._parent.measurement_plan.multiplexer.disconnect_all_channels()
                self._turned_on_output = None

    @pyqtSlot(MultiplexerOutput)
    def turn_on_output(self, output: MultiplexerOutput) -> None:
        """
        Slot turns on output of multiplexer.
        :param output: output to turn on.
        """

        try:
            self._parent.measurement_plan.multiplexer.connect_channel(output)
        except Exception:
            self._device_errors_handler.all_ok = False
            return
        if self._turned_on_output and output.module_number != self._turned_on_output.module_number:
            self._modules[self._turned_on_output.module_number].turn_off()
        self._turned_on_output = output

    def update_info(self) -> None:
        """
        Method updates information about multiplexer.
        """

        self._parent.measurement_plan.remove_all_callback_funcs_for_mux_output_change()
        self._parent.measurement_plan.add_callback_func_for_mux_output_change(self.set_connected_channel)
        self._turned_on_output = None
        self._update_modules()
        self.set_visible()
        self.select_all_channels(True)
