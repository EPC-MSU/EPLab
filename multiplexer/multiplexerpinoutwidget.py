"""
File with class for widget to show multiplexer pinout.
"""

import logging
from typing import Dict, List, Optional
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget
from epcore.analogmultiplexer import ModuleTypes
from epcore.elements import MultiplexerOutput


logger = logging.getLogger("eplab")


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
        self.button_turn_on_off.setToolTip(qApp.translate("mux", "Включить/выключить канал {}"
                                                          ).format(self._channel_number))
        self.button_turn_on_off.clicked.connect(self.send_to_turn_on_off)
        self.button_turn_on_off.setStyleSheet(
            f"QPushButton {{background-color: {self.COLOR_TURNED_OFF}; border: none; font: 10px; "
            f"font-weight: bold; spacing: 0px;}}"
            f"QPushButton:checked {{background-color: {self.COLOR_TURNED_ON}; border: none;}}")
        self.button_turn_on_off.setFixedSize(self.SIZE, self.SIZE)

        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self.button_turn_on_off, alignment=Qt.AlignmentFlag.AlignHCenter)
        v_box_layout.setSpacing(0)
        v_box_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(v_box_layout)
        self.setToolTip(qApp.translate("mux", "Канал {}").format(self._channel_number))

    @pyqtSlot(bool)
    def send_to_turn_on_off(self, state: bool) -> None:
        """
        Slot sends signal that channel was turned on or turned off.
        :param state: if True then channel was turned on.
        """

        self.turned_on.emit(state, self._channel_number)


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
        self._channels: Dict[int, ChannelWidget] = dict()
        self._module_number: int = module_number
        self._module_type: ModuleTypes = module_type
        self._turned_on_channel: Optional[int] = None
        self._init_ui()

    def _change_module_color(self) -> None:
        """
        Method changes color of module.
        """

        color = self.COLOR_TURNED_ON if self._turned_on_channel else self.COLOR_TURNED_OFF
        self.frame_module.setStyleSheet(f"QWidget {{border: 2px solid {color}; border-radius: 3px;}}")

    def _create_pinout(self) -> QWidget:
        """
        Method creates widgets for channels in the module.
        :return: widget on which widgets for channels are located.
        """

        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)
        for index in range(self.MAX_CHANNEL_NUMBER):
            column = index // 2
            row = index % 2
            channel = ChannelWidget(index + 1)
            channel.turned_on.connect(self.turn_on_off_channel)
            self._channels[index + 1] = channel
            grid_layout.addWidget(channel, row, column)

        widget = QWidget()
        widget.setStyleSheet(f"QWidget {{border: 2px solid {self.COLOR_TURNED_OFF}; border-radius: 3px;}}")
        widget.setLayout(grid_layout)
        return widget

    def _init_ui(self) -> None:
        """
        Method initializes widgets on module widget.
        """

        self.frame_module: QWidget = self._create_pinout()
        label_module_number = QLabel(str(self._module_number))
        label_module_number.setStyleSheet("QLabel {border: none; font-size: 15px; font-weight: bold;}")
        label_module_number.setToolTip(qApp.translate("mux", "Номер модуля"))

        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addWidget(label_module_number, alignment=Qt.AlignmentFlag.AlignVCenter)
        h_layout.addWidget(self.frame_module)
        h_layout.addStretch(1)
        self.setLayout(h_layout)
        self.setToolTip(qApp.translate("mux", "Модуль {}").format(self._module_number))

    def show_channel_as_connected(self, channel_number: int) -> None:
        """
        Method shows given channel of module as turned on.
        :param channel_number: channel number.
        """

        self._channels[channel_number].button_turn_on_off.setChecked(True)
        if self._turned_on_channel and self._turned_on_channel != channel_number:
            self._channels[self._turned_on_channel].button_turn_on_off.setChecked(False)
        self._turned_on_channel = channel_number
        self._change_module_color()

    @pyqtSlot(bool, int)
    def turn_on_off_channel(self, state: bool, channel_number: int) -> None:
        """
        Slot turns on or turns off channel.
        :param state: if True then channel should be turned on;
        :param channel_number: channel number to be turned on or off.
        """

        if state:
            if self._turned_on_channel and self._turned_on_channel != channel_number:
                self._channels[self._turned_on_channel].button_turn_on_off.setChecked(False)
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
            self._channels[self._turned_on_channel].button_turn_on_off.setChecked(False)
            self._turned_on_channel = None
        self._change_module_color()


class MultiplexerPinoutWidget(QWidget):
    """
    Class to show multiplexer pinout.
    """

    MIN_WIDTH: int = 500
    SCROLL_AREA_MIN_HEIGHT: int = 100
    mux_output_turned_on: pyqtSignal = pyqtSignal(MultiplexerOutput)
    mux_outputs_turned_off: pyqtSignal = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._modules: Dict[int, ModuleWidget] = dict()
        self._turned_on_output: Optional[MultiplexerOutput] = None
        self._init_ui()

    @staticmethod
    def _create_empty_widget() -> QLabel:
        """
        :return: empty widget.
        """

        label = QLabel(qApp.translate("mux", "Нет мультиплексора"))
        label.setStyleSheet("QLabel {font-weight: bold; font-size: 25px;}")
        return label

    def _create_widgets_for_multiplexer(self) -> QScrollArea:
        """
        Method creates widgets to work with multiplexer.
        :return: scroll area.
        """

        self.layout_for_modules: QVBoxLayout = QVBoxLayout()
        self.layout_for_modules.addStretch(1)
        scroll_area: QScrollArea = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(self.SCROLL_AREA_MIN_HEIGHT)
        widget = QWidget()
        widget.setLayout(self.layout_for_modules)
        scroll_area.setWidget(widget)
        return scroll_area

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget.
        """

        self.scroll_area: QScrollArea = self._create_widgets_for_multiplexer()
        self.label_no_mux: QLabel = self._create_empty_widget()
        self.setMinimumWidth(self.MIN_WIDTH)

        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.label_no_mux, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

    def _remove_all_modules(self) -> None:
        """
        Method removes all modules from widget.
        """

        for module in self._modules.values():
            self.layout_for_modules.removeWidget(module)
            module.deleteLater()
        self._modules = dict()

    def _set_visible(self, visible: bool) -> None:
        """
        :param visible: if True, then the multiplexer widgets should be made visible.
        """

        self.scroll_area.setVisible(visible)
        self.label_no_mux.setVisible(not visible)

    def _update_modules(self, chain: List[ModuleTypes], output: Optional[MultiplexerOutput]) -> None:
        """
        Method updates modules for widget.
        :param chain: list with types of multiplexer modules in chain;
        :param output: connected output.
        """

        self._remove_all_modules()
        if not chain:
            return

        for module_index, module_type in enumerate(chain, start=1):
            module = ModuleWidget(module_type, module_index)
            module.module_turned_on.connect(self.turn_on_output)
            module.module_turned_off.connect(self.turn_off_output)
            self._modules[module_index] = module
            self.layout_for_modules.insertWidget(0, module)

        if output:
            self._modules[output.module_number].show_channel_as_connected(output.channel_number)
            self._turned_on_output = output

    def show_connected_output(self, output: MultiplexerOutput) -> None:
        """
        :param output: output to turn on.
        """

        if self._turned_on_output and output.module_number != self._turned_on_output.module_number:
            self._modules[self._turned_on_output.module_number].turn_off()
        self._turned_on_output = output
        self._modules[self._turned_on_output.module_number].show_channel_as_connected(output.channel_number)

    @pyqtSlot(MultiplexerOutput)
    def turn_off_output(self, output: MultiplexerOutput) -> None:
        """
        Slot turns off output of multiplexer.
        :param output: output to turn off.
        """

        if self._turned_on_output == output:
            self.mux_outputs_turned_off.emit()
            self._turned_on_output = None

    @pyqtSlot(MultiplexerOutput)
    def turn_on_output(self, output: MultiplexerOutput) -> None:
        """
        Slot turns on output of multiplexer.
        :param output: output to turn on.
        """

        self.show_connected_output(output)
        self.mux_output_turned_on.emit(output)

    def update_info(self, connected: bool, chain: List[ModuleTypes], output: Optional[MultiplexerOutput]) -> None:
        """
        Method updates information about multiplexer.
        :param connected: if True, then the multiplexer is connected;
        :param chain: list with types of multiplexer modules in chain;
        :param output: connected output.
        """

        self._turned_on_output = None
        self._update_modules(chain, output)
        self._set_visible(connected)
