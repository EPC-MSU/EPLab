"""
File with class for widget to show short information from measurement plan.
"""

import os
from enum import auto, Enum
from functools import partial
from typing import Generator, List, Tuple
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QCloseEvent, QIcon, QKeyEvent, QRegExpValidator
from epcore.analogmultiplexer.base import MAX_CHANNEL_NUMBER, MIN_CHANNEL_NUMBER
from epcore.elements import MeasurementSettings, MultiplexerOutput, Pin
from epcore.product import EyePointProduct
from common import WorkMode
from language import Language

DIR_MEDIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")


class ChannelAndModuleErrors(Enum):
    """
    Class to denote possible erroneous multiplexer outputs.
    """

    INVALID_CHANNEL = auto()
    INVALID_MODULE = auto()
    UNSUITABLE_CHANNEL = auto()
    UNSUITABLE_MODULE = auto()


class LeftRight(Enum):
    """
    Class to denote left and right.
    """

    LEFT = auto()
    RIGHT = auto()


class ModifiedLineEdit(qt.QLineEdit):
    """
    Class for line edit widget with additional handling of left and right keystrokes.
    """

    left_pressed: pyqtSignal = pyqtSignal()
    right_pressed: pyqtSignal = pyqtSignal()

    def __init__(self):
        super().__init__()

    def keyPressEvent(self, key_press_event: QKeyEvent):
        """
        Method handles key press event.
        :param key_press_event: key press event.
        """

        super().keyPressEvent(key_press_event)
        if key_press_event.key() == Qt.Key_Left and self.cursorPosition() == 0:
            self.left_pressed.emit()
        elif key_press_event.key() == Qt.Key_Right and self.cursorPosition() == len(self.text()):
            self.right_pressed.emit()


class MeasurementPlanWidget(qt.QWidget):
    """
    Class to show short information from measurement plan.
    """

    COLOR_ERROR: str = "pink"
    COLOR_NORMAL: str = "white"
    COLOR_WARNING: str = "#E7F5FE"
    HEADERS: List[str] = []

    def __init__(self, parent):
        """
        :param parent: parent main window.
        """

        super().__init__()
        self.button_new_pin: qt.QPushButton = None
        self.HEADERS: List[str] = ["№", qApp.translate("t", "Модуль MUX"), qApp.translate("t", "Канал MUX"),
                                   qApp.translate("t", "Частота"), qApp.translate("t", "Напряжение"),
                                   qApp.translate("t", "Чувствительность"), qApp.translate("t", "Комментарий")]
        self.progress_bar: qt.QProgressBar = None
        self.table_widget_info: qt.QTableWidget = None
        self._parent = parent
        self._dont_go_to_selected_pin: bool = False
        self._lang: Language = qApp.instance().property("language")
        self._line_edits_channel_numbers: List[qt.QLineEdit] = []
        self._line_edits_comments: List[qt.QLineEdit] = []
        self._line_edits_module_numbers: List[qt.QLineEdit] = []
        self._standby_mode: bool = False
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
        line_edit_module_number = ModifiedLineEdit()
        line_edit_module_number.textChanged.connect(partial(self.check_channel_and_module_numbers, pin_index))
        line_edit_module_number.editingFinished.connect(lambda: self.save_mux_output(pin_index))
        line_edit_module_number.left_pressed.connect(lambda: self.move_left_or_right(LeftRight.LEFT))
        line_edit_module_number.right_pressed.connect(lambda: self.move_left_or_right(LeftRight.RIGHT))
        line_edit_module_number.setValidator(QRegExpValidator(QRegExp(r"\d+")))
        self.table_widget_info.setCellWidget(pin_index, 1, line_edit_module_number)
        self._line_edits_module_numbers.append(line_edit_module_number)
        line_edit_channel_number = ModifiedLineEdit()
        line_edit_channel_number.textChanged.connect(partial(self.check_channel_and_module_numbers, pin_index))
        line_edit_channel_number.editingFinished.connect(lambda: self.save_mux_output(pin_index))
        line_edit_channel_number.left_pressed.connect(lambda: self.move_left_or_right(LeftRight.LEFT))
        line_edit_channel_number.right_pressed.connect(lambda: self.move_left_or_right(LeftRight.RIGHT))
        line_edit_channel_number.setValidator(QRegExpValidator(QRegExp(r"\d+")))
        self.table_widget_info.setCellWidget(pin_index, 2, line_edit_channel_number)
        self._line_edits_channel_numbers.append(line_edit_channel_number)
        if pin.multiplexer_output:
            line_edit_module_number.setText(str(pin.multiplexer_output.module_number))
            line_edit_channel_number.setText(str(pin.multiplexer_output.channel_number))
        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            for index, value in enumerate(self._get_values_for_parameters(settings)):
                label = qt.QLabel(value)
                self.table_widget_info.setCellWidget(pin_index, 3 + index, label)
        else:
            for index in range(3):
                self.table_widget_info.setCellWidget(pin_index, 3 + index, qt.QLabel())
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
        :return: tuple with bool value and errors. If bool value is True then
        channel and module numbers are correct.
        """

        correct = True
        errors = []
        if not channel_number and not module_number:
            return correct, errors
        if not self._parent.measurement_plan.multiplexer:
            errors.append(ChannelAndModuleErrors.UNSUITABLE_CHANNEL)
            errors.append(ChannelAndModuleErrors.UNSUITABLE_MODULE)
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
            if self._parent.measurement_plan.multiplexer and\
                    len(self._parent.measurement_plan.multiplexer.get_chain_info()) < module_number:
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

    def _enable_widgets(self, state: bool):
        """
        Method enables or disables widgets.
        :param state: if True then widgets will be enabled.
        """

        for widget in (self.button_new_pin, self.table_widget_info):
            widget.setEnabled(state)

    def _fill_table(self):
        """
        Method fills table for measurement plan.
        """

        self.table_widget_info.itemSelectionChanged.disconnect()
        self._clear_table()
        self.table_widget_info.itemSelectionChanged.connect(self.set_pin_as_current)
        for pin_index, pin in self._parent.measurement_plan.all_pins_iterator():
            self._add_pin_to_table(pin_index, pin)
            self.check_channel_and_module_numbers(pin_index, "")
        self.select_row_for_current_pin()

    def _fix_bad_multiplexer_output(self, pin_index: int):
        """
        Method fixes bad multiplexer output for pin with given index.
        :param pin_index: pin index.
        """

        if not self._check_mux_output(self._line_edits_channel_numbers[pin_index].text(),
                                      self._line_edits_module_numbers[pin_index].text())[0]:
            pin = self._parent.measurement_plan.get_pin_with_index(pin_index)
            if pin.multiplexer_output:
                self._line_edits_channel_numbers[pin_index].setText(str(pin.multiplexer_output.channel_number))
                self._line_edits_module_numbers[pin_index].setText(str(pin.multiplexer_output.module_number))
            else:
                self._line_edits_channel_numbers[pin_index].clear()
                self._line_edits_module_numbers[pin_index].clear()

    def _get_values_for_parameters(self, settings: MeasurementSettings) -> Generator:
        """
        Method returns values of frequency, voltage and sensitivity for given
        measurement settings.
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
        self.button_new_pin.setIcon(QIcon(os.path.join(DIR_MEDIA, "newpoint.png")))
        self.button_new_pin.clicked.connect(self.add_pin_to_plan)
        self.progress_bar = qt.QProgressBar()
        self.progress_bar.setVisible(False)
        h_box_layout_1 = qt.QHBoxLayout()
        h_box_layout_1.addStretch(1)
        h_box_layout_1.addWidget(self.button_new_pin)
        h_box_layout_2 = qt.QHBoxLayout()
        h_box_layout_2.addWidget(self.progress_bar, 2)
        h_box_layout_2.addStretch(1)
        v_box_layout = qt.QVBoxLayout()
        v_box_layout.addLayout(h_box_layout_1)
        v_box_layout.addWidget(self.table_widget_info)
        v_box_layout.addLayout(h_box_layout_2)
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
        elif ChannelAndModuleErrors.UNSUITABLE_CHANNEL in errors:
            color = self.COLOR_WARNING
            tooltip = qApp.translate("t", "Нет мультиплексора")
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
        elif ChannelAndModuleErrors.UNSUITABLE_MODULE in errors and not self._parent.measurement_plan.multiplexer:
            color = self.COLOR_WARNING
            tooltip = qApp.translate("t", "Нет мультиплексора")
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

        if pin.multiplexer_output:
            module_number = str(pin.multiplexer_output.module_number)
            self._line_edits_module_numbers[pin_index].setText(module_number)
            channel_number = str(pin.multiplexer_output.channel_number)
            self._line_edits_channel_numbers[pin_index].setText(channel_number)
        settings = pin.get_reference_and_test_measurements()[-1]
        if settings:
            for index, value in enumerate(self._get_values_for_parameters(settings)):
                label = self.table_widget_info.cellWidget(pin_index, 3 + index)
                label.setText(value)
        else:
            for index in range(3):
                label = self.table_widget_info.cellWidget(pin_index, 3 + index)
                label.setText("")
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
        self.change_progress()

    @pyqtSlot()
    def change_progress(self):
        """
        Slots changes value for progress bar.
        """

        value = self.progress_bar.value()
        self.progress_bar.setValue(value + 1)

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

    def get_amount_of_pins(self) -> int:
        """
        Method returns amount of pins in measurement plan.
        :return: amount of pins.
        """

        return self.table_widget_info.rowCount()

    def keyPressEvent(self, key_press_event: QKeyEvent):
        """
        Method handles
        :param key_press_event:
        """

        super().keyPressEvent(key_press_event)
        if key_press_event.key() == Qt.Key_Left and self.table_widget_info.currentColumn() == 0:
            self.move_left_or_right(LeftRight.LEFT)

    @pyqtSlot(LeftRight)
    def move_left_or_right(self, direction: LeftRight):
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

        pin_index = self._parent.measurement_plan.get_current_index()
        if pin_index != self.table_widget_info.currentRow():
            self._dont_go_to_selected_pin = True
            self.table_widget_info.selectRow(pin_index)

    def set_new_pin_parameters(self, pin_index: int):
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
    def set_pin_as_current(self):
        """
        Slot sets pin activated on measurement plan table as current.
        """

        if not self._dont_go_to_selected_pin or self._standby_mode:
            row_index = self.table_widget_info.currentRow()
            self._fix_bad_multiplexer_output(row_index)
            self._parent.go_to_selected_pin(row_index)
        elif self._dont_go_to_selected_pin:
            self._dont_go_to_selected_pin = False

    def set_work_mode(self, work_mode: WorkMode):
        """
        Method enables or disables widgets on measurement plan widget according
        to given work mode.
        :param work_mode: work mode.
        """

        if not self._standby_mode:
            self.setEnabled(work_mode != WorkMode.COMPARE)
            self.button_new_pin.setEnabled(work_mode == WorkMode.WRITE)

    def turn_off_standby_mode(self):
        """
        Method turns off standby mode.
        """

        self._standby_mode = False
        self._enable_widgets(True)
        self.progress_bar.setVisible(False)

    def turn_on_standby_mode(self, total_number: int):
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

    def update_info(self):
        """
        Method updates information about measurement plan.
        """

        self._parent.measurement_plan.remove_all_callback_funcs_for_pin_changes()
        self._parent.measurement_plan.add_callback_func_for_pin_changes(self.set_new_pin_parameters)
        self._fill_table()
