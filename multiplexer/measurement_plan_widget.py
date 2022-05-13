"""
File with class for widget to show short information from measurement plan.
"""

from enum import auto, Enum
from functools import partial
from typing import List, Tuple
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp
from PyQt5.QtGui import QCloseEvent, QRegExpValidator
from epcore.analogmultiplexer.base import MAX_CHANNEL_NUMBER, MIN_CHANNEL_NUMBER
from epcore.elements import MultiplexerOutput, Pin
from common import WorkMode


class ChannelAndModuleErrors(Enum):
    """
    Class to denote possible erroneous multiplexer outputs.
    """

    INVALID_CHANNEL = auto()
    INVALID_MODULE = auto()
    UNSUITABLE_CHANNEL = auto()
    UNSUITABLE_MODULE = auto()


class MeasurementPlanWidget(qt.QWidget):
    """
    Class to show short information from measurement plan.
    """

    COLOR_ERROR = "pink"
    COLOR_NORMAL = "white"
    COLOR_WARNING = "#E7F5FE"
    HEADERS = ["№", qApp.translate("t", "Модуль MUX"), qApp.translate("t", "Канал MUX"),
               qApp.translate("t", "Частота"), qApp.translate("t", "Напряжение"),
               qApp.translate("t", "Чувствительность"), qApp.translate("t", "Комментарий")]

    def __init__(self, parent):
        """
        :param parent: parent main window.
        """

        super().__init__()
        self.button_new_pin: qt.QPushButton = None
        self.progress_bar: qt.QProgressBar = None
        self.table_widget_info: qt.QTableWidget = None
        self._parent = parent
        self._dont_save_measurement: bool = False
        self._line_edits_channel_numbers: List[qt.QLineEdit] = []
        self._line_edits_comments: List[qt.QLineEdit] = []
        self._line_edits_module_numbers: List[qt.QLineEdit] = []
        # self._measurement_plan.add_callback_func_for_pin_changes(self.set_new_pin_parameters)
        self._selected_row: int = None
        self._init_ui()

    def _add_pin_to_table(self, pin_index: int, pin: Pin):
        """
        Method adds pin to table with information about measurement plan.
        :param pin_index: index of pin to be added;
        :param pin: pin to be added.
        """

        row_number = self.table_widget_info.rowCount()
        self.table_widget_info.insertRow(row_number)
        self.table_widget_info.setCellWidget(pin_index, 0, qt.QLabel(str(pin_index)))
        line_edit_module_number = qt.QLineEdit()
        line_edit_module_number.textEdited.connect(partial(self.check_channel_and_module_numbers, pin_index))
        line_edit_module_number.editingFinished.connect(lambda: self.save_mux_output(pin_index))
        line_edit_module_number.setValidator(QRegExpValidator(QRegExp(r"\d+")))
        if pin.multiplexer_output:
            line_edit_module_number.setText(str(pin.multiplexer_output.module_number))
        self.table_widget_info.setCellWidget(pin_index, 1, line_edit_module_number)
        self._line_edits_module_numbers.append(line_edit_module_number)
        line_edit_channel_number = qt.QLineEdit()
        line_edit_channel_number.textEdited.connect(partial(self.check_channel_and_module_numbers, pin_index))
        line_edit_channel_number.editingFinished.connect(lambda: self.save_mux_output(pin_index))
        line_edit_channel_number.setValidator(QRegExpValidator(QRegExp(r"\d+")))
        if pin.multiplexer_output:
            line_edit_channel_number.setText(str(pin.multiplexer_output.channel_number))
        self.table_widget_info.setCellWidget(pin_index, 2, line_edit_channel_number)
        self._line_edits_channel_numbers.append(line_edit_channel_number)
        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            freq_unit = qApp.translate("t", " Гц")
            label_frequency = qt.QLabel(f"{settings.probe_signal_frequency}{freq_unit}")
            self.table_widget_info.setCellWidget(pin_index, 3, label_frequency)
            voltage_unit = qApp.translate("t", " В")
            label_voltage = qt.QLabel(f"{settings.max_voltage}{voltage_unit}")
            self.table_widget_info.setCellWidget(pin_index, 4, label_voltage)
            label_resistance = qt.QLabel(str(settings.internal_resistance))
            self.table_widget_info.setCellWidget(pin_index, 5, label_resistance)
        else:
            self.table_widget_info.setCellWidget(pin_index, 3, qt.QLabel())
            self.table_widget_info.setCellWidget(pin_index, 4, qt.QLabel())
            self.table_widget_info.setCellWidget(pin_index, 5, qt.QLabel())
        line_edit_comment = qt.QLineEdit()
        line_edit_comment.editingFinished.connect(lambda: self.save_comment(pin_index))
        line_edit_comment.setText(pin.comment)
        self.table_widget_info.setCellWidget(pin_index, 6, line_edit_comment)
        self._line_edits_comments.append(line_edit_comment)
        self.table_widget_info.resizeRowsToContents()

    def _check_mux_output(self, channel_number: str, module_number: str) -> Tuple[bool, List[ChannelAndModuleErrors]]:
        """
        Method checks that given channel and module numbers are correct.
        :return: tuple with bool value and errors. If bool value is True then
        channel and module numbers are correct.
        """

        correct = True
        errors = []
        if not channel_number and not module_number:
            return correct, errors
        # Check channel number
        try:
            channel_number = int(channel_number)
            if not MIN_CHANNEL_NUMBER <= channel_number <= MAX_CHANNEL_NUMBER:
                correct = False
                errors.append(ChannelAndModuleErrors.INVALID_CHANNEL)
        except ValueError:
            correct = False
            errors.append(ChannelAndModuleErrors.INVALID_CHANNEL)
        # Check module number
        try:
            module_number = int(module_number)
            if len(self._parent.measurement_plan.multiplexer.get_chain_info()) < module_number:
                errors.append(ChannelAndModuleErrors.UNSUITABLE_MODULE)
            elif module_number < 1:
                correct = False
                errors.append(ChannelAndModuleErrors.INVALID_MODULE)
        except ValueError:
            errors.append(ChannelAndModuleErrors.INVALID_MODULE)
        return correct, errors

    def _clear_table(self):
        """
        Method clears all information from table for measurement plan and
        removes all rows in table.
        """

        self._line_edits_channel_numbers = []
        self._line_edits_comments = []
        self._line_edits_module_numbers = []
        for row in range(self.table_widget_info.rowCount(), -1, -1):
            self.table_widget_info.removeRow(row)
        self.table_widget_info.clearContents()

    def _fill_table(self):
        """
        Method fills table for measurement plan.
        """

        self.table_widget_info.itemSelectionChanged.disconnect()
        self._clear_table()
        self.table_widget_info.itemSelectionChanged.connect(self.set_pin_as_current)
        for pin_index, pin in self._parent.measurement_plan.all_pins_iterator():
            self._add_pin_to_table(pin_index, pin)
        self.select_row_for_current_pin()

    def _init_table(self):
        """
        Method initializes table for measurement plan.
        """

        self.table_widget_info = qt.QTableWidget()
        self.table_widget_info.setColumnCount(len(self.HEADERS))
        self.table_widget_info.setHorizontalHeaderLabels(self.HEADERS)
        self.table_widget_info.verticalHeader().setVisible(False)
        self.table_widget_info.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        self.table_widget_info.setSelectionMode(qt.QAbstractItemView.SingleSelection)
        self.table_widget_info.horizontalHeader().setStretchLastSection(True)
        self.table_widget_info.cellClicked.connect(self.set_pin_as_current)
        self.table_widget_info.itemSelectionChanged.connect(self.set_pin_as_current)

    def _init_ui(self):
        """
        Method initializes widgets on main widget.
        """

        self._init_table()
        name_and_tooltip = qApp.translate("t", "Новая точка")
        self.button_new_pin = qt.QPushButton(name_and_tooltip)
        self.button_new_pin.setToolTip(name_and_tooltip)
        self.button_new_pin.clicked.connect(self.add_pin_to_plan)
        self.progress_bar = qt.QProgressBar()
        self.progress_bar.setVisible(False)
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addWidget(self.progress_bar)
        h_box_layout.addStretch(1)
        h_box_layout.addWidget(self.button_new_pin)
        v_box_layout = qt.QVBoxLayout()
        v_box_layout.addWidget(self.table_widget_info)
        v_box_layout.addLayout(h_box_layout)
        self.setLayout(v_box_layout)

    def _paint_channel_number(self, line_edit_channel_number: qt.QLineEdit, errors: List[ChannelAndModuleErrors]):
        """
        Method paints line edit widget for given channel number in color
        depending on errors.
        :param line_edit_channel_number: line edit widget for given channel number;
        :param errors: list with errors.
        """

        if ChannelAndModuleErrors.INVALID_CHANNEL in errors:
            color = self.COLOR_ERROR
            tooltip = qApp.translate("t", "Неверный номер канала модуля (допустимые значения от 1 до 64 включительно)")
        else:
            color = self.COLOR_NORMAL
            tooltip = ""
        line_edit_channel_number.setStyleSheet(f"background-color: {color};")
        line_edit_channel_number.setToolTip(tooltip)

    def _paint_module_number(self, line_edit_module_number: qt.QLineEdit, errors: List[ChannelAndModuleErrors]):
        """
        Method paints line edit widget for given module number in color
        depending on errors.
        :param line_edit_module_number: line edit widget for given module number;
        :param errors: list with errors.
        """

        if ChannelAndModuleErrors.INVALID_MODULE in errors:
            color = self.COLOR_ERROR
            tooltip = qApp.translate("t", "Неверный номер модуля")
        elif ChannelAndModuleErrors.UNSUITABLE_MODULE in errors:
            color = self.COLOR_WARNING
            tooltip = qApp.translate("t", "Неверный номер модуля для текущей конфигурации мультиплексора (допустимые "
                                          "значения от 1 до {} включительно)")
            tooltip = tooltip.format(len(self._parent.measurement_plan.multiplexer.get_chain_info()))
        else:
            color = self.COLOR_NORMAL
            tooltip = ""
        line_edit_module_number.setStyleSheet(f"background-color: {color};")
        line_edit_module_number.setToolTip(tooltip)

    def _update_pin_in_table(self, pin_index: int, pin: Pin):
        """
        Method updates pin information in table.
        :param pin_index: index of pin to be updated;
        :param pin: pin to be updated.
        """

        module_number = "" if not pin.multiplexer_output else str(pin.multiplexer_output.module_number)
        self._line_edits_module_numbers[pin_index].setText(module_number)
        channel_number = "" if not pin.multiplexer_output else str(pin.multiplexer_output.channel_number)
        self._line_edits_channel_numbers[pin_index].setText(channel_number)
        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            freq_unit = qApp.translate("t", " Гц")
            label_frequency = qt.QLabel(f"{settings.probe_signal_frequency}{freq_unit}")
            self.table_widget_info.setCellWidget(pin_index, 3, label_frequency)
            voltage_unit = qApp.translate("t", " В")
            label_voltage = qt.QLabel(f"{settings.max_voltage}{voltage_unit}")
            self.table_widget_info.setCellWidget(pin_index, 4, label_voltage)
            label_resistance = qt.QLabel(str(settings.internal_resistance))
            self.table_widget_info.setCellWidget(pin_index, 5, label_resistance)
        else:
            self.table_widget_info.setCellWidget(pin_index, 3, qt.QLabel())
            self.table_widget_info.setCellWidget(pin_index, 4, qt.QLabel())
            self.table_widget_info.setCellWidget(pin_index, 5, qt.QLabel())
        self._line_edits_comments[pin_index].setText(pin.comment)

    @pyqtSlot()
    def add_pin_to_plan(self):
        """
        Slot adds pin to measurement plan.
        """

        self._parent.create_new_pin()

    @pyqtSlot(MultiplexerOutput)
    def add_pin_with_mux_output_to_plan(self, channel: MultiplexerOutput):
        """
        Slot adds pin to measurement plan.
        :param channel: channel from multiplexer to be added.
        """

        self._parent.create_new_pin(channel)

    @pyqtSlot(int, str)
    def check_channel_and_module_numbers(self, pin_index: int, _: str):
        """
        Slot checks correctness of module number entered by user.
        :param pin_index: pin index for which to check;
        :param _: unused.
        """

        line_edits = [self._line_edits_channel_numbers[pin_index], self._line_edits_module_numbers[pin_index]]
        channel_number = line_edits[0].text()
        module_number = line_edits[1].text()
        errors = self._check_mux_output(channel_number, module_number)[1]
        self._paint_channel_number(line_edits[0], errors)
        self._paint_module_number(line_edits[1], errors)

    def closeEvent(self, event: QCloseEvent):
        """
        Method handles close event.
        :param event: close event.
        """

        if self._parent.measurement_plan:
            self._parent.measurement_plan.remove_all_callback_funcs_for_pin_changes()
        super().closeEvent(event)

    def enable_widgets(self, work_mode: WorkMode):
        """
        Method enables or disables widgets on measurement plan widget according
        to given work mode.
        :param work_mode: work mode.
        """

        self.setEnabled(work_mode != WorkMode.COMPARE)
        self.button_new_pin.setEnabled(work_mode == WorkMode.WRITE)

    @pyqtSlot(int)
    def save_comment(self, pin_index: int):
        """
        Slot saves comment to pin.
        :param pin_index: pin index.
        """

        line_edit_comment = self._line_edits_comments[pin_index]
        pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
        if not pin:
            return
        pin.comment = line_edit_comment.text()
        self._parent.update_current_pin()

    @pyqtSlot(int)
    def save_mux_output(self, pin_index: int):
        """
        Slot saves multiplexer output to pin.
        :param pin_index: pin index.
        """

        channel_number = self._line_edits_channel_numbers[pin_index].text()
        module_number = self._line_edits_module_numbers[pin_index].text()
        if self._check_mux_output(channel_number, module_number)[0]:
            pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
            if not pin:
                return
            if channel_number and module_number:
                pin.multiplexer_output = MultiplexerOutput(channel_number=int(channel_number),
                                                           module_number=int(module_number))
            else:
                pin.multiplexer_output = None

    def select_row_for_current_pin(self):
        """
        Method selects row in table for current pin index.
        """

        if self._parent.work_mode != WorkMode.COMPARE:
            pin_index = self._parent.measurement_plan.get_current_index()
            self._selected_row = pin_index
            self.table_widget_info.selectRow(pin_index)
        else:
            self.table_widget_info.clearSelection()

    def set_new_pin_parameters(self, pin_index: int):
        """
        Method updates pin parameters in measurement plan table.
        """

        pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
        if self.table_widget_info.rowCount() <= pin_index:
            self._add_pin_to_table(pin_index, pin)
        else:
            self._update_pin_in_table(pin_index, pin)

    @pyqtSlot()
    def set_pin_as_current(self):
        """
        Slot sets pin activated on measurement plan table as current.
        """

        row = self.table_widget_info.currentRow()
        self._parent.go_to_selected_pin(row)

    def update_info(self):
        """
        Method updates information about measurement plan.
        """

        self._parent.measurement_plan.remove_all_callback_funcs_for_pin_changes()
        self._parent.measurement_plan.add_callback_func_for_pin_changes(self.set_new_pin_parameters)
        self._fill_table()
