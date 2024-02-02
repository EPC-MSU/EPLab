"""
File with class for widget to show short information from measurement plan.
"""

from typing import Any, Generator, List, Optional
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QTableWidgetItem
from epcore.analogmultiplexer.base import MultiplexerOutput
from epcore.elements import MeasurementSettings, Pin
from epcore.product import EyePointProduct
from window.common import WorkMode
from window.language import get_language, Language
from window.pinindextableitem import PinIndexTableItem
from window.scaler import update_scale_of_class
from window.tablewidget import TableWidget


@update_scale_of_class
class MeasurementPlanWidget(TableWidget):
    """
    Class for widget to show short information from measurement plan in table.
    """

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        headers: List[str] = ["№", qApp.translate("mux", "Модуль MUX"), qApp.translate("mux", "Канал MUX"),
                              qApp.translate("mux", "Частота"), qApp.translate("mux", "Напряжение"),
                              qApp.translate("mux", "Чувствительность")]
        super().__init__(main_window, headers)
        self._lang: Language = get_language()
        self._standby_mode: bool = False

    def _add_pin_to_table(self, index: int, pin: Pin) -> None:
        """
        Method adds pin to table with information about measurement plan.
        :param index: index of pin to be added;
        :param pin: point to be added.
        """

        self.insertRow(index)
        self.setItem(index, 0, PinIndexTableItem(index))

        if pin.multiplexer_output:
            channel = pin.multiplexer_output.channel_number
            module = pin.multiplexer_output.module_number
        else:
            channel = None
            module = None
        item_module = self._create_table_item(module)
        self.setItem(index, 1, item_module)
        item_channel = self._create_table_item(channel)
        self.setItem(index, 2, item_channel)

        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            for i, value in enumerate(self._get_values_for_parameters(settings)):
                item = self._create_table_item(value)
                self.setItem(index, 3 + i, item)
        else:
            for i in range(3):
                item = self._create_table_item()
                self.setItem(index, 3 + i, item)

    def _clear_table(self) -> None:
        """
        Method clears all information from table for measurement plan and removes all rows in table.
        """

        self.disconnect_item_selection_changed_signal()
        _ = [self.removeRow(row) for row in range(self.rowCount(), -1, -1)]
        self.clearContents()
        self.connect_item_selection_changed_signal()

    @staticmethod
    def _create_table_item(value: Optional[Any] = None) -> QTableWidgetItem:
        item = QTableWidgetItem()
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        if value:
            item.setText(str(value))
        return item

    def _fill_table(self) -> None:
        """
        Method fills table for measurement plan.
        """

        self._clear_table()
        for pin_index, pin in self._main_window.measurement_plan.all_pins_iterator():
            self._add_pin_to_table(pin_index, pin)
        self.select_row_for_current_pin()

    def _get_values_for_parameters(self, settings: MeasurementSettings) -> Generator:
        """
        Method returns values of frequency, voltage and sensitivity for given measurement settings.
        :param settings: measurement settings.
        :return: values of frequency, voltage and sensitivity.
        """

        options = self._main_window.product.settings_to_options(settings)
        available = self._main_window.product.get_available_options(settings)
        parameters = (EyePointProduct.Parameter.frequency, EyePointProduct.Parameter.voltage,
                      EyePointProduct.Parameter.sensitive)
        for parameter in parameters:
            for available_option in available[parameter]:
                if available_option.name == options[parameter]:
                    yield available_option.label_ru if self._lang is Language.RU else available_option.label_en

    def _update_pin_in_table(self, pin_index: int, pin: Pin) -> None:
        """
        Method updates pin information in table.
        :param pin_index: index of pin to be updated;
        :param pin: pin to be updated.
        """

        if pin.multiplexer_output:
            values = pin.multiplexer_output.module_number, pin.multiplexer_output.channel_number
            for column, value in enumerate(values, start=1):
                item = self.item(pin_index, column)
                item.setText(str(value))

        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            for index, value in enumerate(self._get_values_for_parameters(settings)):
                item = self.item(pin_index, 3 + index)
                item.setText(value)
        else:
            for index in range(3):
                item = self.item(pin_index, 3 + index)
                item.setText("")

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Method handles close event.
        :param event: close event.
        """

        if self._main_window.measurement_plan:
            self._main_window.measurement_plan.remove_all_callback_funcs_for_pin_changes()
        super().closeEvent(event)

    def get_amount_of_pins(self) -> int:
        """
        Method returns amount of pins in measurement plan.
        :return: amount of pins.
        """

        return self.rowCount()

    def get_pin_index(self, mux_output: MultiplexerOutput) -> Optional[int]:
        """
        :param mux_output: multiplexer output.
        :return: pin index with a given multiplexer output.
        """

        channel = str(mux_output.channel_number)
        module = str(mux_output.module_number)
        for index in range(self.rowCount()):
            pin_module = self.item(index, 1).text()
            pin_channel = self.item(index, 2).text()
            if pin_channel == channel and pin_module == module:
                return index

    def handle_current_pin_change(self, index: int) -> None:
        """
        Method handles changing the current pin in the measurement plan.
        :param index: index of the current pin in the measurement plan.
        """

        pin = self._main_window.measurement_plan.get_pin_with_index(index)
        if self._main_window.measurement_plan.pins_number > self.rowCount():
            self._add_pin_to_table(index, pin)
        elif self._main_window.measurement_plan.pins_number < self.rowCount():
            if index is None:
                index = 0
            self._remove_row(index)
        elif index is not None:
            self._update_pin_in_table(index, pin)
        self._update_indexes(index)

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
        self.setEnabled(True)

    def turn_on_standby_mode(self) -> None:
        """
        Method turns on standby mode.
        """

        self._standby_mode = True
        self.setEnabled(False)

    def update_info(self) -> None:
        """
        Method updates information about the measurement plan.
        """

        self._fill_table()
