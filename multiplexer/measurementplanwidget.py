"""
File with class for widget to show short information from measurement plan.
"""

from typing import Generator, List, Optional
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtGui import QCloseEvent
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

    def _add_pin(self, index: int, pin: Pin) -> None:
        """
        Method adds pin to table with information about measurement plan.
        :param index: index of pin to be added;
        :param pin: pin to be added.
        """

        self.insertRow(index)
        self.setItem(index, 0, PinIndexTableItem(index))

        for column in range(1, 7):
            item = self._create_table_item()
            self.setItem(index, column, item)
        self._write_pin_info_into_table(index, pin)

    def _fill_table(self) -> None:
        """
        Method fills table for measurement plan.
        """

        for pin_index, pin in self._main_window.measurement_plan.all_pins_iterator():
            self._add_pin(pin_index, pin)

    def _get_values_for_parameters(self, settings: MeasurementSettings) -> Generator[str, None, None]:
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

    def _write_pin_info_into_table(self, index: int, pin: Pin) -> None:
        """
        Method writes pin information into the table.
        :param index: pin index;
        :param pin: pin.
        """

        if pin.multiplexer_output:
            channel = pin.multiplexer_output.channel_number
            module = pin.multiplexer_output.module_number
        else:
            channel = None
            module = None
        for column, value in enumerate((module, channel), start=1):
            item = self.item(index, column)
            if value:
                item.setText(str(value))

        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            for i, value in enumerate(self._get_values_for_parameters(settings)):
                item = self.item(index, 3 + i)
                item.setText(value)
        else:
            for i in range(3):
                item = self.item(index, 3 + i)
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
        :return: amount of pins in measurement plan.
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

        return None

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

        self._clear_table()
        self._fill_table()
        self.select_row()
