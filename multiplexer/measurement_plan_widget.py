"""
File with class for widget to show short information from measurement plan.
"""

from functools import partial
from typing import List
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp
from PyQt5.QtGui import QRegExpValidator
from epcore.analogmultiplexer import AnalogMultiplexerBase
from epcore.analogmultiplexer.base import MAX_CHANNEL_NUMBER, MIN_CHANNEL_NUMBER
from epcore.elements import MultiplexerOutput
from epcore.measurementmanager import MeasurementPlan


class MeasurementPlanWidget(qt.QWidget):
    """
    Class to show short information from measurement plan.
    """

    COLOR_ERROR = "pink"
    COLOR_NORMAL = "white"
    COLOR_WARNING = "#ADD8E6"
    HEADERS = ["№", qApp.translate("t", "Модуль MUX"), qApp.translate("t", "Канал MUX"),
               qApp.translate("t", "Частота"), qApp.translate("t", "Напряжение"),
               qApp.translate("t", "Чувствительность"), qApp.translate("t", "Комментарий")]

    def __init__(self, parent):
        """
        :param parent: parent main window.
        """

        super().__init__()
        self.button_new_point: qt.QPushButton = None
        self.progress_bar: qt.QProgressBar = None
        self.table_widget_info: qt.QTableWidget = None
        self._parent = parent
        self._line_edits_channel_numbers: List[qt.QLineEdit] = []
        self._line_edits_comments: List[qt.QLineEdit] = []
        self._line_edits_module_numbers: List[qt.QLineEdit] = []
        self._measurement_plan: MeasurementPlan = parent.measurement_plan
        self._multiplexer: AnalogMultiplexerBase = self._measurement_plan.multiplexer
        self._init_ui()

    def _init_ui(self):
        """
        Method initializes widgets on main widget.
        """

        self.create_table()
        name_and_tooltip = qApp.translate("t", "Новая точка")
        self.button_new_point = qt.QPushButton(name_and_tooltip)
        self.button_new_point.setToolTip(name_and_tooltip)
        self.progress_bar = qt.QProgressBar()
        self.progress_bar.setVisible(False)
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addWidget(self.progress_bar)
        h_box_layout.addStretch(1)
        h_box_layout.addWidget(self.button_new_point)
        v_box_layout = qt.QVBoxLayout()
        v_box_layout.addWidget(self.table_widget_info)
        v_box_layout.addLayout(h_box_layout)
        self.setLayout(v_box_layout)

    @pyqtSlot(int, str)
    def check_channel_number(self, pin_index: int, channel_number: str):
        """
        Slot checks correctness of channel number entered by user.
        :param pin_index: pin index for which to check;
        :param channel_number: channel number to check.
        """

        line_edit_channel_number = self._line_edits_channel_numbers[pin_index]
        try:
            channel_number = int(channel_number)
            if MIN_CHANNEL_NUMBER <= channel_number <= MAX_CHANNEL_NUMBER:
                color = self.COLOR_NORMAL
            else:
                color = self.COLOR_ERROR
        except Exception:
            color = self.COLOR_ERROR
        line_edit_channel_number.setStyleSheet(f"background-color: {color};")

    @pyqtSlot(int, str)
    def check_module_number(self, pin_index: int, module_number: str):
        """
        Slot checks correctness of module number entered by user.
        :param pin_index: pin index for which to check;
        :param module_number: module number to check.
        """

        line_edit_module_number = self._line_edits_module_numbers[pin_index]
        try:
            module_number = int(module_number)
            if 0 < module_number <= len(self._multiplexer.get_chain_info()):
                color = self.COLOR_NORMAL
            elif 0 < module_number:
                color = self.COLOR_WARNING
            else:
                color = self.COLOR_ERROR
        except Exception:
            color = self.COLOR_ERROR
        line_edit_module_number.setStyleSheet(f"background-color: {color};")

    def create_table(self):
        """
        Method creates table for measurement plan.
        """

        if self.table_widget_info:
            self.table_widget_info.clear()
        self.table_widget_info = qt.QTableWidget(len(list(self._measurement_plan.all_pins_iterator())),
                                                 len(self.HEADERS))
        self.table_widget_info.setHorizontalHeaderLabels(self.HEADERS)
        self.table_widget_info.verticalHeader().setVisible(False)
        self.table_widget_info.setSelectionMode(qt.QAbstractItemView.SingleSelection)
        for pin_index, pin in self._measurement_plan.all_pins_iterator():
            self.table_widget_info.setCellWidget(pin_index, 0, qt.QLabel(str(pin_index)))
            line_edit_module_number = qt.QLineEdit()
            line_edit_module_number.textEdited.connect(partial(self.check_module_number, pin_index))
            line_edit_module_number.setValidator(QRegExpValidator(QRegExp(r"\d+")))
            if pin.multiplexer_output:
                line_edit_module_number.setText(str(pin.multiplexer_output.module_number))
            self.table_widget_info.setCellWidget(pin_index, 1, line_edit_module_number)
            self._line_edits_module_numbers.append(line_edit_module_number)
            line_edit_channel_number = qt.QLineEdit()
            line_edit_channel_number.textEdited.connect(partial(self.check_channel_number, pin_index))
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
            self.table_widget_info.resizeColumnsToContents()
        self.table_widget_info.horizontalHeader().setStretchLastSection(True)

    @pyqtSlot(int)
    def save_comment(self, pin_index: int):
        """
        Slot saves comment to pin.
        :param pin_index: pin index.
        """

        current_index = self._measurement_plan.get_current_index()
        line_edit_comment = self._line_edits_comments[pin_index]
        if current_index != pin_index:
            self._measurement_plan.go_pin(pin_index)
        pin = self._measurement_plan.get_current_pin()
        pin.comment = line_edit_comment.text()
        if current_index != pin_index:
            self._measurement_plan.go_pin(current_index)
