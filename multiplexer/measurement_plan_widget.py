"""
File with class for widget to show short information from measurement plan.
"""

import os
from enum import auto, Enum
from typing import Dict, Generator, List, Tuple
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QCloseEvent, QColor, QIcon, QKeyEvent, QRegExpValidator
from PyQt5.QtWidgets import (QAbstractItemView, QHBoxLayout, QLineEdit, QProgressBar, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)
from epcore.analogmultiplexer.base import MAX_CHANNEL_NUMBER, MIN_CHANNEL_NUMBER
from epcore.elements import MeasurementSettings, MultiplexerOutput, Pin
from epcore.product import EyePointProduct
from window import utils as ut
from window.common import WorkMode
from window.language import Language
from window.scaler import update_scale_of_class


MAX_MODULE_NUMBER = 8
MIN_MODULE_NUMBER = 1


class ChannelAndModuleErrors(Enum):
    """
    Class to denote possible erroneous multiplexer outputs.
    """

    INVALID_CHANNEL = auto()
    INVALID_MODULE = auto()
    UNSUITABLE_OUTPUT = auto()


class LeftRight(Enum):
    """
    Class to denote left and right.
    """

    LEFT = auto()
    RIGHT = auto()


class ModifiedLineEdit(QLineEdit):
    """
    Class for line edit widget with additional handling of left and right keystrokes.
    """

    left_pressed: pyqtSignal = pyqtSignal()
    right_pressed: pyqtSignal = pyqtSignal()

    def keyPressEvent(self, key_press_event: QKeyEvent) -> None:
        """
        Method handles key press event.
        :param key_press_event: key press event.
        """

        super().keyPressEvent(key_press_event)
        if key_press_event.key() == Qt.Key_Left and self.cursorPosition() == 0:
            self.left_pressed.emit()
        elif key_press_event.key() == Qt.Key_Right and self.cursorPosition() == len(self.text()):
            self.right_pressed.emit()


@update_scale_of_class
class MeasurementPlanWidget(QWidget):
    """
    Class for widget to show short information from measurement plan in table.
    """

    COLOR_ERROR_FRAME: str = "#FF0404"
    COLOR_ERROR: str = "#FFD8D8"
    COLOR_NORMAL: QColor = QColor.fromRgb(255, 255, 255)
    COLOR_NOT_TESTED: str = "#F9E154"
    HEADERS: List[str] = []

    def __init__(self, parent) -> None:
        """
        :param parent: parent main window.
        """

        super().__init__()
        self.button_new_pin: QPushButton = None
        self.HEADERS: List[str] = ["№", qApp.translate("t", "Модуль MUX"), qApp.translate("t", "Канал MUX"),
                                   qApp.translate("t", "Частота"), qApp.translate("t", "Напряжение"),
                                   qApp.translate("t", "Чувствительность"), qApp.translate("t", "Комментарий")]
        self.progress_bar: QProgressBar = None
        self.table_widget_info: QTableWidget = None
        self._dont_go_to_selected_pin: bool = False
        self._lang: Language = qApp.instance().property("language")
        self._line_edits_channel_numbers: List[QLineEdit] = []
        self._line_edits_comments: List[QLineEdit] = []
        self._line_edits_module_numbers: List[QLineEdit] = []
        self._parent = parent
        self._saved_mux_outputs: Dict[int, MultiplexerOutput] = {}
        self._standby_mode: bool = False
        self._init_ui()

    def _add_pin_to_table(self, pin_index: int, pin: Pin) -> None:
        """
        Method adds pin to table with information about measurement plan.
        :param pin_index: index of pin to be added;
        :param pin: pin to be added.
        """

        self.table_widget_info.insertRow(pin_index)
        item = QTableWidgetItem(str(pin_index))
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        self.table_widget_info.setItem(pin_index, 0, item)
        line_edit_module_number = ModifiedLineEdit()
        line_edit_module_number.textEdited.connect(lambda: self.check_channel_and_module_numbers(pin_index))
        line_edit_module_number.left_pressed.connect(lambda: self.move_left_or_right(LeftRight.LEFT))
        line_edit_module_number.right_pressed.connect(lambda: self.move_left_or_right(LeftRight.RIGHT))
        line_edit_module_number.setValidator(QRegExpValidator(QRegExp(r"\d+")))
        self.table_widget_info.setCellWidget(pin_index, 1, line_edit_module_number)
        self._line_edits_module_numbers.append(line_edit_module_number)
        line_edit_channel_number = ModifiedLineEdit()
        line_edit_channel_number.textEdited.connect(lambda: self.check_channel_and_module_numbers(pin_index))
        line_edit_channel_number.left_pressed.connect(lambda: self.move_left_or_right(LeftRight.LEFT))
        line_edit_channel_number.right_pressed.connect(lambda: self.move_left_or_right(LeftRight.RIGHT))
        line_edit_channel_number.setValidator(QRegExpValidator(QRegExp(r"\d+")))
        self.table_widget_info.setCellWidget(pin_index, 2, line_edit_channel_number)
        self._line_edits_channel_numbers.append(line_edit_channel_number)
        self._saved_mux_outputs[pin_index] = pin.multiplexer_output
        if pin.multiplexer_output:
            line_edit_module_number.setText(str(pin.multiplexer_output.module_number))
            line_edit_channel_number.setText(str(pin.multiplexer_output.channel_number))
        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            for index, value in enumerate(self._get_values_for_parameters(settings)):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table_widget_info.setItem(pin_index, 3 + index, item)
        else:
            for index in range(3):
                item = QTableWidgetItem()
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table_widget_info.setItem(pin_index, 3 + index, item)
        line_edit_comment = ModifiedLineEdit()
        line_edit_comment.editingFinished.connect(lambda: self.save_comment(pin_index))
        line_edit_comment.left_pressed.connect(lambda: self.move_left_or_right(LeftRight.LEFT))
        line_edit_comment.right_pressed.connect(lambda: self.move_left_or_right(LeftRight.RIGHT))
        line_edit_comment.setText(pin.comment)
        self.table_widget_info.setCellWidget(pin_index, 6, line_edit_comment)
        self._line_edits_comments.append(line_edit_comment)
        self.table_widget_info.resizeRowsToContents()

    def _check_mux_output(self, channel_number: str, module_number: str) -> Tuple[bool, List[ChannelAndModuleErrors]]:
        """
        Method checks that given channel and module numbers are correct.
        :param channel_number: channel number;
        :param module_number: module number.
        :return: tuple with bool value and errors. If bool value is True then channel and module numbers are correct.
        """

        valid = True
        errors = []
        if not channel_number and not module_number:
            errors.append(ChannelAndModuleErrors.UNSUITABLE_OUTPUT)
            return valid, errors
        # Check channel number
        try:
            channel_number = int(channel_number)
            if not MIN_CHANNEL_NUMBER <= channel_number <= MAX_CHANNEL_NUMBER:
                valid = False
                errors.append(ChannelAndModuleErrors.INVALID_CHANNEL)
        except ValueError:
            valid = False
            errors.append(ChannelAndModuleErrors.INVALID_CHANNEL)
        # Check module number
        try:
            module_number = int(module_number)
            if not MIN_MODULE_NUMBER <= module_number <= MAX_MODULE_NUMBER:
                valid = False
                errors.append(ChannelAndModuleErrors.INVALID_MODULE)
            elif self._parent.measurement_plan.multiplexer and\
                    not (MIN_MODULE_NUMBER <= module_number <=
                         len(self._parent.measurement_plan.multiplexer.get_chain_info())):
                errors.append(ChannelAndModuleErrors.UNSUITABLE_OUTPUT)
        except ValueError:
            valid = False
            errors.append(ChannelAndModuleErrors.INVALID_MODULE)
        return valid, errors

    def _clear_table(self) -> None:
        """
        Method clears all information from table for measurement plan and removes all rows in table.
        """

        self._line_edits_channel_numbers = []
        self._line_edits_comments = []
        self._line_edits_module_numbers = []
        self._saved_mux_outputs = {}
        for row in range(self.table_widget_info.rowCount(), -1, -1):
            self.table_widget_info.removeRow(row)
        self.table_widget_info.clearContents()

    def _enable_widgets(self, state: bool) -> None:
        """
        Method enables or disables widgets.
        :param state: if True then widgets will be enabled.
        """

        for widget in (self.button_new_pin, self.table_widget_info):
            widget.setEnabled(state)

    def _fill_table(self) -> None:
        """
        Method fills table for measurement plan.
        """

        self.table_widget_info.itemSelectionChanged.disconnect()
        self._clear_table()
        self.table_widget_info.itemSelectionChanged.connect(self.set_pin_as_current)
        for pin_index, pin in self._parent.measurement_plan.all_pins_iterator():
            self._add_pin_to_table(pin_index, pin)
            self.check_channel_and_module_numbers(pin_index)
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

        self.table_widget_info = QTableWidget()
        self.table_widget_info.setColumnCount(len(self.HEADERS))
        self.table_widget_info.setHorizontalHeaderLabels(self.HEADERS)
        self.table_widget_info.verticalHeader().setVisible(False)
        self.table_widget_info.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget_info.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_widget_info.horizontalHeader().setStretchLastSection(True)
        self.table_widget_info.cellClicked.connect(self.set_pin_as_current)
        self.table_widget_info.itemSelectionChanged.connect(self.set_pin_as_current)

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget.
        """

        self._init_table()
        name_and_tooltip = qApp.translate("t", "Новая точка")
        self.button_new_pin = QPushButton(name_and_tooltip)
        self.button_new_pin.setToolTip(name_and_tooltip)
        self.button_new_pin.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "newpoint.png")))
        self.button_new_pin.clicked.connect(self.add_pin_to_plan)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        h_box_layout_1 = QHBoxLayout()
        h_box_layout_1.addStretch(1)
        h_box_layout_1.addWidget(self.button_new_pin)
        h_box_layout_2 = QHBoxLayout()
        h_box_layout_2.addWidget(self.progress_bar, 2)
        h_box_layout_2.addStretch(1)
        v_box_layout = QVBoxLayout()
        v_box_layout.addLayout(h_box_layout_1)
        v_box_layout.addWidget(self.table_widget_info)
        v_box_layout.addLayout(h_box_layout_2)
        self.setLayout(v_box_layout)

    def _paint_errors(self, row: int, errors: List[ChannelAndModuleErrors]) -> None:
        """
        Method colors row with given index if there is invalid multiplexer output.
        :param row: row index to color;
        :param errors: list with errors for multiplexer output.
        """

        color = None
        if ChannelAndModuleErrors.INVALID_MODULE in errors:
            color = MeasurementPlanWidget.COLOR_ERROR
        if ChannelAndModuleErrors.INVALID_CHANNEL in errors:
            color = MeasurementPlanWidget.COLOR_ERROR
        for column in range(self.table_widget_info.columnCount()):
            if column in (1, 2, 6):
                widget = self.table_widget_info.cellWidget(row, column)
                widget.setStyleSheet("")  # set default style and then new style
                if color:
                    style = widget.styleSheet()
                    widget.setStyleSheet(style + f"background-color: {color};")
            else:
                item = self.table_widget_info.item(row, column)
                if color:
                    item.setBackground(QColor.fromRgb(int(color[1:], base=16)))
                else:
                    item.setBackground(MeasurementPlanWidget.COLOR_NORMAL)
        self._set_error_tooltip_to_mux_output(row, errors)

    def _paint_warnings(self, row: int, errors: List[ChannelAndModuleErrors]) -> None:
        """
        Method colors row with given index if there is invalid or unsuitable multiplexer output.
        :param row: row index to paint;
        :param errors: list with errors for multiplexer output.
        """

        color = None
        if errors:
            color = MeasurementPlanWidget.COLOR_NOT_TESTED
        for column in range(self.table_widget_info.columnCount()):
            if column in (1, 2, 6):
                widget = self.table_widget_info.cellWidget(row, column)
                widget.setStyleSheet("")
                if color:
                    style = widget.styleSheet()
                    widget.setStyleSheet(style + f"background-color: {color};")
            else:
                item = self.table_widget_info.item(row, column)
                if color:
                    item.setBackground(QColor.fromRgb(int(color[1:], base=16)))
                else:
                    item.setBackground(MeasurementPlanWidget.COLOR_NORMAL)
        self._set_error_tooltip_to_mux_output(row, errors)

    def _set_error_tooltip_to_mux_output(self, row: int, errors: List[ChannelAndModuleErrors]) -> None:
        """
        Method sets tooltip about error to multiplexer output fields on row with given index.
        :param row: row index;
        :param errors: list with errors for multiplexer output.
        """

        tooltips = ["", ""]
        if ChannelAndModuleErrors.INVALID_MODULE in errors:
            tooltips[0] = qApp.translate("t", "Поле Модуль MUX имеет некорректное значение (должно быть 1...8), "
                                              "точка не сохранена")
        if ChannelAndModuleErrors.INVALID_CHANNEL in errors:
            tooltips[1] = qApp.translate("t", "Поле Канал MUX имеет некорректное значение (должно быть 1...64), "
                                              "точка не сохранена")
        for index, tooltip in enumerate(tooltips):
            widget = self.table_widget_info.cellWidget(row, index + 1)
            widget.setToolTip(tooltip)
            if tooltip:
                style_sheet = widget.styleSheet()
                widget.setStyleSheet(style_sheet + f"border: 1px solid {MeasurementPlanWidget.COLOR_ERROR_FRAME}")

    def _update_pin_in_table(self, pin_index: int, pin: Pin) -> None:
        """
        Method updates pin information in table.
        :param pin_index: index of pin to be updated;
        :param pin: pin to be updated.
        """

        if pin.multiplexer_output:
            module_number = str(pin.multiplexer_output.module_number)
            self._line_edits_module_numbers[pin_index].setText(module_number)
            channel_number = str(pin.multiplexer_output.channel_number)
            self._line_edits_channel_numbers[pin_index].setText(channel_number)
        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            for index, value in enumerate(self._get_values_for_parameters(settings)):
                item = self.table_widget_info.item(pin_index, 3 + index)
                item.setText(value)
        else:
            for index in range(3):
                item = self.table_widget_info.item(pin_index, 3 + index)
                item.setText("")
        self._line_edits_comments[pin_index].setText(pin.comment)

    @pyqtSlot()
    def add_pin_to_plan(self) -> None:
        """
        Slot adds pin to measurement plan.
        """

        self._parent.create_new_pin()

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

    @pyqtSlot(int)
    def check_channel_and_module_numbers(self, pin_index: int) -> None:
        """
        Slot checks correctness of module number entered by user.
        :param pin_index: pin index for which to check.
        """

        channel_number = self._line_edits_channel_numbers[pin_index].text()
        module_number = self._line_edits_module_numbers[pin_index].text()
        valid, errors = self._check_mux_output(channel_number, module_number)
        self._paint_errors(pin_index, errors)
        pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
        if valid:
            if not pin:
                return
            if channel_number and module_number:
                pin.multiplexer_output = MultiplexerOutput(channel_number=int(channel_number),
                                                           module_number=int(module_number))
            else:
                pin.multiplexer_output = None
            self._saved_mux_outputs[pin_index] = pin.multiplexer_output
        elif pin:
            pin.multiplexer_output = None

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

        return self.table_widget_info.rowCount()

    def keyPressEvent(self, key_press_event: QKeyEvent) -> None:
        """
        Method performs additional processing of pressing left key on keyboard.
        :param key_press_event: key press event.
        """

        super().keyPressEvent(key_press_event)
        if key_press_event.key() == Qt.Key_Left and self.table_widget_info.currentColumn() == 0:
            self.move_left_or_right(LeftRight.LEFT)

    @pyqtSlot(LeftRight)
    def move_left_or_right(self, direction: LeftRight) -> None:
        """
        Slot moves focus in table between columns.
        :param direction: left or right direction in which to move focus.
        """

        column = self.table_widget_info.currentColumn()
        row = self.table_widget_info.currentRow()
        if direction == LeftRight.LEFT and column > 0:
            self.table_widget_info.setFocus()
            self.table_widget_info.setCurrentCell(row, column - 1)
        elif direction == LeftRight.LEFT and column == 0:
            if row > 0:
                row -= 1
                column = self.table_widget_info.columnCount() - 1
            self.table_widget_info.setFocus()
            self.table_widget_info.setCurrentCell(row, column)
        elif direction == LeftRight.RIGHT and column < self.table_widget_info.columnCount() - 1:
            self.table_widget_info.setFocus()
            self.table_widget_info.setCurrentCell(row, column + 1)
        elif direction == LeftRight.RIGHT and column == self.table_widget_info.columnCount() - 1:
            if row < self.table_widget_info.rowCount() - 1:
                row += 1
                column = 0
            self.table_widget_info.setFocus()
            self.table_widget_info.setCurrentCell(row, column)

    @pyqtSlot(int)
    def save_comment(self, pin_index: int) -> None:
        """
        Slot saves comment to pin.
        :param pin_index: pin index.
        """

        pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
        if not pin:
            return
        pin.comment = self._line_edits_comments[pin_index].text()
        self._parent.update_current_pin()

    @pyqtSlot(int)
    def save_mux_output(self, pin_index: int) -> None:
        """
        Slot saves multiplexer output to pin.
        :param pin_index: pin index.
        """

        channel_number = self._line_edits_channel_numbers[pin_index].text()
        module_number = self._line_edits_module_numbers[pin_index].text()
        valid, errors = self._check_mux_output(channel_number, module_number)
        if valid:
            pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
            if not pin:
                return
            if channel_number and module_number:
                pin.multiplexer_output = MultiplexerOutput(channel_number=int(channel_number),
                                                           module_number=int(module_number))
            else:
                pin.multiplexer_output = None
            self._saved_mux_outputs[pin_index] = pin.multiplexer_output

    def select_row_for_current_pin(self) -> None:
        """
        Method selects row in table for current pin index.
        """

        pin_index = self._parent.measurement_plan.get_current_index()
        if pin_index != self.table_widget_info.currentRow():
            self._dont_go_to_selected_pin = True
            self.table_widget_info.selectRow(pin_index)

    def set_new_pin_parameters(self, pin_index: int) -> None:
        """
        Method updates pin parameters in measurement plan table.
        :param pin_index: index of pin whose parameters need to be updated.
        """

        pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
        if self.table_widget_info.rowCount() <= pin_index:
            self._add_pin_to_table(pin_index, pin)
        else:
            self._update_pin_in_table(pin_index, pin)

    @pyqtSlot()
    def set_pin_as_current(self) -> None:
        """
        Slot sets pin activated on measurement plan table as current.
        """

        if not self._dont_go_to_selected_pin or self._standby_mode:
            row_index = self.table_widget_info.currentRow()
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
            self.button_new_pin.setEnabled(work_mode == WorkMode.WRITE)

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

        self._parent.measurement_plan.remove_all_callback_funcs_for_pin_changes()
        self._parent.measurement_plan.add_callback_func_for_pin_changes(self.set_new_pin_parameters)
        self._fill_table()

    def validate_mux_outputs_for_pins(self) -> None:
        """
        Method validates multiplexer outputs for pins in measurement plan.
        """

        for pin_index in range(self.table_widget_info.rowCount()):
            saved_mux_output = self._saved_mux_outputs[pin_index]
            if self._saved_mux_outputs[pin_index]:
                self._line_edits_channel_numbers[pin_index].setText(str(saved_mux_output.channel_number))
                self._line_edits_module_numbers[pin_index].setText(str(saved_mux_output.module_number))
            else:
                self._line_edits_channel_numbers[pin_index].clear()
                self._line_edits_module_numbers[pin_index].clear()
            pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
            pin.multiplexer_output = saved_mux_output
            channel_number = self._line_edits_channel_numbers[pin_index].text()
            module_number = self._line_edits_module_numbers[pin_index].text()
            errors = self._check_mux_output(channel_number, module_number)[1]
            self._paint_warnings(pin_index, errors)
