"""
File with class for widget to show multiplexer pinout.
"""

import os
from typing import Dict, List, Optional
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget
from epcore.analogmultiplexer import ModuleTypes
from epcore.elements import MultiplexerOutput
from window import utils as ut
from window.common import DeviceErrorsHandler, WorkMode
from window.scaler import update_scale_of_class


class ChannelWidget(QWidget):
    """
    Class to show single channel of module.
    """

    COLOR_TURNED_OFF: str = "#9ADAEB"
    COLOR_TURNED_ON: str = "#F9E154"
    SIZE: int = 13
    turned_on: pyqtSignal = pyqtSignal(bool, int)

    def __init__(self, channel_number: int) -> None:
        """
        :param channel_number: channel number on module.
        """

        super().__init__()
        self._channel_number: int = channel_number
        self._init_ui()

    def _init_ui(self) -> None:
        self.button_turn_on_off: QPushButton = QPushButton(str(self._channel_number))
        self.button_turn_on_off.setCheckable(True)
        self.button_turn_on_off.setToolTip(qApp.translate("t", "Включить/выключить канал {}"
                                                          ).format(self._channel_number))
        self.button_turn_on_off.clicked.connect(self.send_to_turn_on_off)
        self.button_turn_on_off.setStyleSheet(
            f"QPushButton {{background-color: {ChannelWidget.COLOR_TURNED_OFF}; border: none; font: 10px; "
            f"font-weight: bold; spacing: 0px;}}"
            f"QPushButton:checked {{background-color: {ChannelWidget.COLOR_TURNED_ON}; border: none;}}")
        self.button_turn_on_off.setFixedSize(ChannelWidget.SIZE, ChannelWidget.SIZE)

        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self.button_turn_on_off, alignment=Qt.AlignHCenter)
        v_box_layout.setSpacing(0)
        v_box_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(v_box_layout)
        self.setToolTip(qApp.translate("t", "Канал {}").format(self._channel_number))

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


class ModuleWidget(QWidget):
    """
    Class to show single module of multiplexer.
    """

    COLOR_TURNED_OFF: str = "#186DB6"
    COLOR_TURNED_ON: str = "#D21404"
    MARGIN: int = 2
    MAX_CHANNEL_NUMBER: int = 64
    module_turned_off: pyqtSignal = pyqtSignal(MultiplexerOutput)
    module_turned_on: pyqtSignal = pyqtSignal(MultiplexerOutput)

    def __init__(self, module_type: ModuleTypes, module_number: int) -> None:
        """
        :param module_type: module type;
        :param module_number: module number.
        """

        super().__init__()
        self._channels: Dict[int, ChannelWidget] = {}
        self._module_number: int = module_number
        self._module_type: ModuleTypes = module_type
        self._turned_on_channel: int = None
        self._init_ui()

    def _change_module_color(self) -> None:
        """
        Method changes color of module.
        """

        color = ModuleWidget.COLOR_TURNED_ON if self._turned_on_channel else ModuleWidget.COLOR_TURNED_OFF
        self.frame_module.setStyleSheet(f"QWidget {{border: 2px solid {color}; border-radius: 3px;}}")

    def _create_pinout(self) -> QWidget:
        """
        Method creates widgets for channels in the module.
        :return: widget on which widgets for channels are located.
        """

        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(ModuleWidget.MARGIN, ModuleWidget.MARGIN, ModuleWidget.MARGIN,
                                       ModuleWidget.MARGIN)
        for index in range(ModuleWidget.MAX_CHANNEL_NUMBER):
            column = index // 2
            row = index % 2
            channel = ChannelWidget(index + 1)
            channel.turned_on.connect(self.turn_on_off_channel)
            self._channels[index + 1] = channel
            grid_layout.addWidget(channel, row, column)

        widget = QWidget()
        widget.setStyleSheet(f"QWidget {{border: 2px solid {ModuleWidget.COLOR_TURNED_OFF}; border-radius: 3px;}}")
        widget.setLayout(grid_layout)
        return widget

    def _init_ui(self) -> None:
        """
        Method initializes widgets on module widget.
        """

        self.frame_module: QWidget = self._create_pinout()
        label_module_number = QLabel(str(self._module_number))
        label_module_number.setStyleSheet("QLabel {border: none; font-size: 15px; font-weight: bold;}")
        label_module_number.setToolTip(qApp.translate("t", "Номер модуля"))

        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addWidget(label_module_number, alignment=Qt.AlignVCenter)
        h_layout.addWidget(self.frame_module)
        h_layout.addStretch(1)
        self.setLayout(h_layout)
        self.setToolTip(qApp.translate("t", "Модуль {}").format(self._module_number))

    def get_channels(self) -> List[MultiplexerOutput]:
        """
        Method returns channels for the module.
        :return: list with channels.
        """

        return [MultiplexerOutput(channel_number, self._module_number)
                for channel_number in sorted(self._channels.keys())]

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
            if self._turned_on_channel and self._turned_on_channel != channel_number:
                self._channels[self._turned_on_channel].turn_off()
            self._turned_on_channel = channel_number
            output = MultiplexerOutput(channel_number=channel_number, module_number=self._module_number)
            self.module_turned_on.emit(output)
        else:
            if self._turned_on_channel and self._turned_on_channel == channel_number:
                output = MultiplexerOutput(channel_number=channel_number, module_number=self._module_number)
                self.module_turned_off.emit(output)
                self._turned_on_channel = None
        self._change_module_color()

    def turn_off(self) -> None:
        """
        Method turns off channels of module.
        """

        if self._turned_on_channel:
            self._channels[self._turned_on_channel].turn_off()
            self._turned_on_channel = None
        self._change_module_color()


@update_scale_of_class
class MultiplexerPinoutWidget(QWidget):
    """
    Class to show multiplexer pinout.
    """

    MIN_WIDTH: int = 500
    SCROLL_AREA_MIN_HEIGHT: int = 100
    TIMEOUT: int = 10
    adding_channels_finished: pyqtSignal = pyqtSignal()
    adding_channels_started: pyqtSignal = pyqtSignal(int)
    channel_added: pyqtSignal = pyqtSignal(MultiplexerOutput)

    def __init__(self, main_window, device_errors_handler: Optional[DeviceErrorsHandler] = None) -> None:
        """
        :param main_window: main window of application;
        :param device_errors_handler: device errors handler.
        """

        super().__init__()
        self._device_errors_handler: DeviceErrorsHandler = device_errors_handler if device_errors_handler else \
            main_window.device_errors_handler
        self._modules: Dict[int, ModuleWidget] = {}
        self._parent = main_window
        self._selected_channels: List[MultiplexerOutput] = []
        self._turned_on_output: MultiplexerOutput = None
        self._init_ui()

    @staticmethod
    def _create_empty_widget() -> QLabel:
        """
        :return: empty widget.
        """

        label = QLabel(qApp.translate("t", "Нет мультиплексора"))
        label.setStyleSheet("QLabel {font-weight: bold; font-size: 25px;}")
        return label

    def _create_widgets_for_multiplexer(self) -> None:
        """
        Method creates widgets to work with multiplexer.
        """

        self.layout_for_modules: QVBoxLayout = QVBoxLayout()
        self.layout_for_modules.addStretch(1)
        self.scroll_area: QScrollArea = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(MultiplexerPinoutWidget.SCROLL_AREA_MIN_HEIGHT)
        widget = QWidget()
        widget.setLayout(self.layout_for_modules)
        self.scroll_area.setWidget(widget)
        self.button_start_or_stop_entire_plan_measurement: QPushButton = QPushButton(
            qApp.translate("t", "Запустить измерение всех точек"))
        self.button_start_or_stop_entire_plan_measurement.setIcon(QIcon(os.path.join(ut.DIR_MEDIA,
                                                                                     "start_auto_test.png")))
        self.button_start_or_stop_entire_plan_measurement.setCheckable(True)

    def _enable_widgets(self, state: bool) -> None:
        """
        Method enables or disables some widgets on multiplexer pinout widget.
        :param state: if True then widgets will be enabled.
        """

        for widget in (self.button_start_or_stop_entire_plan_measurement,):
            widget.setEnabled(state)

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget.
        """

        self._create_widgets_for_multiplexer()
        self.label_no_mux: QLabel = self._create_empty_widget()
        self.setMinimumWidth(MultiplexerPinoutWidget.MIN_WIDTH)

        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self.button_start_or_stop_entire_plan_measurement)
        h_box_layout = QHBoxLayout()
        h_box_layout.addStretch(1)
        h_box_layout.addLayout(v_box_layout)

        layout = QVBoxLayout()
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
            for module_index, module_type in enumerate(chain, start=1):
                module = ModuleWidget(module_type, module_index)
                module.module_turned_on.connect(self.turn_on_output)
                module.module_turned_off.connect(self.turn_off_output)
                self._modules[module_index] = module
                self.layout_for_modules.insertWidget(0, module)

            connected_output = self._parent.measurement_plan.multiplexer.get_connected_channel()
            if connected_output:
                self._modules[connected_output.module_number].set_connected_channel(connected_output.channel_number)
                self._turned_on_output = connected_output
            self._enable_widgets(len(chain) != 0)

    def enable_widgets(self, state: bool) -> None:
        """
        Method enables or disables all widgets on multiplexer pinout widget.
        :param state: if True then widgets will be enabled.
        """

        self._enable_widgets(state)
        for module in self._modules.values():
            module.setEnabled(state)

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

        visible = bool(self._parent.measurement_plan and self._parent.measurement_plan.multiplexer) if status is None \
            else status
        for widget in (self.button_start_or_stop_entire_plan_measurement, self.scroll_area):
            widget.setVisible(visible)
        self.label_no_mux.setVisible(not visible)

    def set_work_mode(self, work_mode: WorkMode) -> None:
        """
        Method enables or disables widgets on multiplexer pinout widget according to given work mode.
        :param work_mode: work mode.
        """

        with self._device_errors_handler:
            if work_mode != WorkMode.COMPARE and self._parent.measurement_plan and \
                    self._parent.measurement_plan.multiplexer and \
                    len(self._parent.measurement_plan.multiplexer.get_chain_info()):
                self._enable_widgets(True)
            else:
                self._enable_widgets(False)

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
