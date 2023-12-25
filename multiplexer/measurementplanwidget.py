"""
File with class for widget to show short information from measurement plan.
"""

from typing import Dict, Generator, List
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QCloseEvent, QKeyEvent, QRegExpValidator
from PyQt5.QtWidgets import (QAbstractItemView, QHBoxLayout, QProgressBar, QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)
from epcore.elements import MeasurementSettings, MultiplexerOutput, Pin
from epcore.product import EyePointProduct
from multiplexer.leftrightrunnabletable import LeftRight
from multiplexer.modifiedlineedit import ModifiedLineEdit
from multiplexer.pinindextableitem import PinIndexTableItem
from window.common import WorkMode
from window.language import Language
from window.scaler import update_scale_of_class


@update_scale_of_class
class MeasurementPlanWidget(QWidget):
    """
    Class for widget to show short information from measurement plan in table.
    """

    HEADERS: List[str] = []

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self.HEADERS: List[str] = ["№", qApp.translate("t", "Модуль MUX"), qApp.translate("t", "Канал MUX"),
                                   qApp.translate("t", "Частота"), qApp.translate("t", "Напряжение"),
                                   qApp.translate("t", "Чувствительность")]
        self.progress_bar: QProgressBar = None
        self.table_widget: QTableWidget = None
        self._dont_go_to_selected_pin: bool = False
        self._lang: Language = qApp.instance().property("language")
        self._parent = main_window
        self._saved_mux_outputs: Dict[int, MultiplexerOutput] = {}
        self._standby_mode: bool = False
        self._init_ui()

    def _add_point_to_table(self, index: int, point: Pin) -> None:
        """
        Method adds point to table with information about measurement plan.
        :param index: index of pin to be added;
        :param point: point to be added.
        """

        self.table_widget.insertRow(index)
        self.table_widget.setItem(index, 0, PinIndexTableItem(index))

        line_edit_module_number = ModifiedLineEdit()
        line_edit_module_number.left_pressed.connect(lambda: self.move_left_or_right(LeftRight.LEFT))
        line_edit_module_number.right_pressed.connect(lambda: self.move_left_or_right(LeftRight.RIGHT))
        self.table_widget.setCellWidget(index, 1, line_edit_module_number)

        line_edit_channel_number = ModifiedLineEdit()
        line_edit_channel_number.left_pressed.connect(lambda: self.move_left_or_right(LeftRight.LEFT))
        line_edit_channel_number.right_pressed.connect(lambda: self.move_left_or_right(LeftRight.RIGHT))
        line_edit_channel_number.setValidator(QRegExpValidator(QRegExp(r"\d+")))
        self.table_widget.setCellWidget(index, 2, line_edit_channel_number)

        self._saved_mux_outputs[index] = point.multiplexer_output
        if point.multiplexer_output:
            line_edit_module_number.setText(str(point.multiplexer_output.module_number))
            line_edit_channel_number.setText(str(point.multiplexer_output.channel_number))
        settings = point.get_reference_and_test_measurements()[-1]
        if settings:
            for index, value in enumerate(self._get_values_for_parameters(settings)):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table_widget.setItem(index, 3 + index, item)
        else:
            for index in range(3):
                item = QTableWidgetItem()
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table_widget.setItem(index, 3 + index, item)

        self.table_widget.resizeRowsToContents()

    def _clear_table(self) -> None:
        """
        Method clears all information from table for measurement plan and removes all rows in table.
        """

        self._saved_mux_outputs = {}
        for row in range(self.table_widget.rowCount(), -1, -1):
            self.table_widget.removeRow(row)
        self.table_widget.clearContents()

    def _enable_widgets(self, state: bool) -> None:
        """
        Method enables or disables widgets.
        :param state: if True then widgets will be enabled.
        """

        for widget in (self.table_widget,):
            widget.setEnabled(state)

    def _fill_table(self) -> None:
        """
        Method fills table for measurement plan.
        """

        self.table_widget.itemSelectionChanged.disconnect()
        self._clear_table()
        self.table_widget.itemSelectionChanged.connect(self.set_pin_as_current)
        for pin_index, pin in self._parent.measurement_plan.all_pins_iterator():
            self._add_point_to_table(pin_index, pin)
        self.select_row_for_current_pin()

    def _get_values_for_parameters(self, settings: MeasurementSettings) -> Generator:
        """
        Method returns values of frequency, voltage and sensitivity for given measurement settings.
        :param settings: measurement settings.
        :return: values of frequency, voltage and sensitivity.
        """

        options = self._parent.product.settings_to_options(settings)
        available = self._parent.product.get_available_options(settings)
        parameters = (EyePointProduct.Parameter.frequency, EyePointProduct.Parameter.voltage,
                      EyePointProduct.Parameter.sensitive)
        for parameter in parameters:
            for available_option in available[parameter]:
                if available_option.name == options[parameter]:
                    yield available_option.label_ru if self._lang is Language.RU else available_option.label_en

    def _init_table(self) -> None:
        """
        Method initializes table for measurement plan.
        """

        self.table_widget: QTableWidget = QTableWidget()
        self.table_widget.setColumnCount(len(MeasurementPlanWidget.HEADERS))
        self.table_widget.setHorizontalHeaderLabels(MeasurementPlanWidget.HEADERS)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.cellClicked.connect(self.set_pin_as_current)
        self.table_widget.itemSelectionChanged.connect(self.set_pin_as_current)

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget.
        """

        self._init_table()
        self.progress_bar: QProgressBar = QProgressBar()
        self.progress_bar.setVisible(False)

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.progress_bar, 2)
        h_layout.addStretch(1)

        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self.table_widget)
        v_box_layout.addLayout(h_layout)
        self.setLayout(v_box_layout)

    def _update_pin_in_table(self, pin_index: int, pin: Pin) -> None:
        """
        Method updates pin information in table.
        :param pin_index: index of pin to be updated;
        :param pin: pin to be updated.
        """

        if pin.multiplexer_output:
            module_number = str(pin.multiplexer_output.module_number)
            self.table_widget.cellWidget(pin_index, 1).setText(module_number)

            channel_number = str(pin.multiplexer_output.channel_number)
            self.table_widget.cellWidget(pin_index, 2).setText(channel_number)

        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            for index, value in enumerate(self._get_values_for_parameters(settings)):
                item = self.table_widget.item(pin_index, 3 + index)
                item.setText(value)
        else:
            for index in range(3):
                item = self.table_widget.item(pin_index, 3 + index)
                item.setText("")

    @pyqtSlot(MultiplexerOutput)
    def add_pin_with_mux_output_to_plan(self, channel: MultiplexerOutput) -> None:
        """
        Slot adds pin with multiplexer output to measurement plan.
        :param channel: channel from multiplexer to be added.
        """

        self._parent.create_new_pin(channel)
        self.change_progress()

    @pyqtSlot()
    def change_progress(self) -> None:
        """
        Slots changes value for progress bar.
        """

        value = self.progress_bar.value()
        self.progress_bar.setValue(value + 1)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Method handles close event.
        :param event: close event.
        """

        if self._parent.measurement_plan:
            self._parent.measurement_plan.remove_all_callback_funcs_for_pin_changes()
        super().closeEvent(event)

    def get_amount_of_pins(self) -> int:
        """
        Method returns amount of pins in measurement plan.
        :return: amount of pins.
        """

        return self.table_widget.rowCount()

    def keyPressEvent(self, key_press_event: QKeyEvent) -> None:
        """
        Method performs additional processing of pressing left key on keyboard.
        :param key_press_event: key press event.
        """

        super().keyPressEvent(key_press_event)
        if key_press_event.key() == Qt.Key_Left and self.table_widget.currentColumn() == 0:
            self.move_left_or_right(LeftRight.LEFT)

    @pyqtSlot(LeftRight)
    def move_left_or_right(self, direction: LeftRight) -> None:
        """
        Slot moves focus in table between columns.
        :param direction: left or right direction in which to move focus.
        """

        column = self.table_widget.currentColumn()
        row = self.table_widget.currentRow()
        if direction == LeftRight.LEFT and column > 0:
            self.table_widget.setFocus()
            self.table_widget.setCurrentCell(row, column - 1)
        elif direction == LeftRight.LEFT and column == 0:
            if row > 0:
                row -= 1
                column = self.table_widget.columnCount() - 1
            self.table_widget.setFocus()
            self.table_widget.setCurrentCell(row, column)
        elif direction == LeftRight.RIGHT and column < self.table_widget.columnCount() - 1:
            self.table_widget.setFocus()
            self.table_widget.setCurrentCell(row, column + 1)
        elif direction == LeftRight.RIGHT and column == self.table_widget.columnCount() - 1:
            if row < self.table_widget.rowCount() - 1:
                row += 1
                column = 0
            self.table_widget.setFocus()
            self.table_widget.setCurrentCell(row, column)

    def select_row_for_current_pin(self) -> None:
        """
        Method selects row in table for current pin index.
        """

        pin_index = self._parent.measurement_plan.get_current_index()
        if pin_index != self.table_widget.currentRow():
            self._dont_go_to_selected_pin = True
            self.table_widget.selectRow(pin_index)

    def set_new_pin_parameters(self, pin_index: int) -> None:
        """
        Method updates pin parameters in measurement plan table.
        :param pin_index: index of pin whose parameters need to be updated.
        """

        pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
        if self.table_widget.rowCount() <= pin_index:
            self._add_point_to_table(pin_index, pin)
        else:
            self._update_pin_in_table(pin_index, pin)

    @pyqtSlot()
    def set_pin_as_current(self) -> None:
        """
        Slot sets pin activated on measurement plan table as current.
        """

        if not self._dont_go_to_selected_pin or self._standby_mode:
            row_index = self.table_widget.currentRow()
            self._parent.go_to_selected_pin(row_index)
        elif self._dont_go_to_selected_pin:
            self._dont_go_to_selected_pin = False

    def set_work_mode(self, work_mode: WorkMode) -> None:
        """
        Method enables or disables widgets on measurement plan widget according to given work mode.
        :param work_mode: work mode.
        """

        if not self._standby_mode:
            self.setEnabled(work_mode != WorkMode.COMPARE)

    def turn_off_standby_mode(self) -> None:
        """
        Method turns off standby mode.
        """

        self._standby_mode = False
        self._enable_widgets(True)
        self.progress_bar.setVisible(False)

    def turn_on_standby_mode(self, total_number: int) -> None:
        """
        Method turns on standby mode.
        :param total_number: number of steps in standby mode.
        """

        self._standby_mode = True
        self._enable_widgets(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(total_number)
        self.progress_bar.setValue(0)

    def update_info(self) -> None:
        """
        Method updates information about measurement plan.
        """

        # self._parent.measurement_plan.remove_all_callback_funcs_for_pin_changes()
        self._parent.measurement_plan.add_callback_func_for_pin_changes(self.set_new_pin_parameters)
        self._fill_table()
