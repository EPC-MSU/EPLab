"""
File with class for widget to show short information from measurement plan.
"""

from typing import Any, Generator, List, Optional
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QTableWidgetItem, QVBoxLayout, QWidget
from epcore.elements import MeasurementSettings, Pin
from epcore.product import EyePointProduct
from multiplexer.leftrightrunnabletable import LeftRightRunnableTable
from multiplexer.pinindextableitem import PinIndexTableItem
from window.common import WorkMode
from window.language import Language
from window.scaler import update_scale_of_class


@update_scale_of_class
class MeasurementPlanWidget(QWidget):
    """
    Class for widget to show short information from measurement plan in table.
    """

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self._dont_go_to_selected_pin: bool = False
        self._headers: List[str] = ["№", qApp.translate("t", "Модуль MUX"), qApp.translate("t", "Канал MUX"),
                                    qApp.translate("t", "Частота"), qApp.translate("t", "Напряжение"),
                                    qApp.translate("t", "Чувствительность")]
        self._lang: Language = qApp.instance().property("language")
        self._parent = main_window
        self._standby_mode: bool = False
        self._init_ui()

    def _add_pin_to_table(self, index: int, pin: Pin) -> None:
        """
        Method adds pin to table with information about measurement plan.
        :param index: index of pin to be added;
        :param pin: point to be added.
        """

        self.table_widget.insertRow(index)
        self.table_widget.setItem(index, 0, PinIndexTableItem(index))

        if pin.multiplexer_output:
            channel = pin.multiplexer_output.channel_number
            module = pin.multiplexer_output.module_number
        else:
            channel = None
            module = None
        item_module = self._create_table_item(module)
        self.table_widget.setItem(index, 1, item_module)
        item_channel = self._create_table_item(channel)
        self.table_widget.setItem(index, 2, item_channel)

        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            for i, value in enumerate(self._get_values_for_parameters(settings)):
                item = self._create_table_item(value)
                self.table_widget.setItem(index, 3 + i, item)
        else:
            for i in range(3):
                item = self._create_table_item()
                self.table_widget.setItem(index, 3 + i, item)

        self.table_widget.resizeRowsToContents()

    def _clear_table(self) -> None:
        """
        Method clears all information from table for measurement plan and removes all rows in table.
        """

        self.table_widget.disconnect_item_selection_changed_signal()
        _ = [self.table_widget.removeRow(row) for row in range(self.table_widget.rowCount(), -1, -1)]
        self.table_widget.clearContents()
        self.table_widget.connect_item_selection_changed_signal()

    @staticmethod
    def _create_table_item(value: Optional[Any] = None) -> QTableWidgetItem:
        item = QTableWidgetItem()
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        if value:
            item.setText(str(value))
        return item

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

        self._clear_table()
        for pin_index, pin in self._parent.measurement_plan.all_pins_iterator():
            self._add_pin_to_table(pin_index, pin)
        self.table_widget.select_row_for_current_point()

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

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget.
        """

        self.table_widget: LeftRightRunnableTable = LeftRightRunnableTable(self._parent, self._headers)
        layout = QVBoxLayout()
        layout.addWidget(self.table_widget)
        self.setLayout(layout)

    def _update_pin_in_table(self, pin_index: int, pin: Pin) -> None:
        """
        Method updates pin information in table.
        :param pin_index: index of pin to be updated;
        :param pin: pin to be updated.
        """

        if pin.multiplexer_output:
            values = pin.multiplexer_output.module_number, pin.multiplexer_output.channel_number
            for column, value in enumerate(values, start=1):
                item = self.table_widget.item(pin_index, column)
                item.setText(str(value))

        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            for index, value in enumerate(self._get_values_for_parameters(settings)):
                item = self.table_widget.item(pin_index, 3 + index)
                item.setText(value)
        else:
            for index in range(3):
                item = self.table_widget.item(pin_index, 3 + index)
                item.setText("")

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

    def select_row_for_current_pin(self) -> None:
        """
        Method selects row in table for current pin index.
        """

        self.table_widget.select_row_for_current_point()

    def set_new_pin_parameters(self, pin_index: int) -> None:
        """
        Method updates pin parameters in measurement plan table.
        :param pin_index: index of pin whose parameters need to be updated.
        """

        pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
        if self.table_widget.rowCount() <= pin_index:
            self._add_pin_to_table(pin_index, pin)
        else:
            self._update_pin_in_table(pin_index, pin)

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

    def turn_on_standby_mode(self, total_number: int) -> None:
        """
        Method turns on standby mode.
        :param total_number: number of steps in standby mode.
        """

        self._standby_mode = True
        self._enable_widgets(False)

    def update_info(self) -> None:
        """
        Method updates information about the measurement plan.
        """

        # self._parent.measurement_plan.remove_all_callback_funcs_for_pin_changes()
        self._parent.measurement_plan.add_callback_func_for_pin_changes(self.set_new_pin_parameters)
        self._fill_table()
