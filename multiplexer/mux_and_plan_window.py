"""
File with class to show window with information about multiplexer and
measurement plan.
"""

import os
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from common import WorkMode
from multiplexer.measurement_plan_runner import MeasurementPlanRunner
from multiplexer.measurement_plan_widget import MeasurementPlanWidget
from multiplexer.multiplexer_pinout_widget import MultiplexerPinoutWidget

DIR_MEDIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")


class MuxAndPlanWindow(qt.QWidget):
    """
    Class for dialog window to show information about multiplexer and measurement plan.
    """

    def __init__(self, parent):
        """
        :param parent: parent main window.
        """

        super().__init__(None, Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.button_arrange_windows: qt.QPushButton = None
        self.measurement_plan_widget: MeasurementPlanWidget = None
        self.multiplexer_pinout_widget: MultiplexerPinoutWidget = None
        self._parent = parent
        self._init_ui()
        self.measurement_plan_runner: MeasurementPlanRunner = MeasurementPlanRunner(parent,
                                                                                    self.measurement_plan_widget)
        self.measurement_plan_runner.measurement_done.connect(self.measurement_plan_widget.change_progress)
        self.measurement_plan_runner.measurements_finished.connect(self.turn_off_standby_mode)
        self.measurement_plan_runner.measurements_finished.connect(self.create_report)
        self.measurement_plan_runner.measurements_started.connect(self.turn_on_standby_mode)

    def _change_widgets_to_start_plan_measurement(self, status: bool):
        """
        Method changes widgets to start or stop plan measurements according
        status of one of them.
        :param status: status of one of widgets to start plan measurements.
        """

        widgets = (self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement,
                   self._parent.start_or_stop_entire_plan_measurement_action)
        if status:
            if self.measurement_plan_runner.get_pins_without_multiplexer_outputs() and \
                    not self._continue_plan_measurement():
                self.sender().setChecked(False)
                return
            text = qApp.translate("t", "Остановить измерение всего плана")
            icon = QIcon(os.path.join(DIR_MEDIA, "stop_auto_test.png"))
        else:
            text = qApp.translate("t", "Запустить измерение всего плана")
            icon = QIcon(os.path.join(DIR_MEDIA, "start_auto_test.png"))
        for widget in widgets:
            widget.setIcon(icon)
            widget.setToolTip(text)
            if widget != self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement:
                widget.setText(text)
            if widget.isChecked() != status:
                widget.setChecked(status)

    @staticmethod
    def _continue_plan_measurement() -> bool:
        """
        Method asks user whether it is necessary to continue measurements according
        to measurement plan.
        :return: True if measurements should be continued.
        """

        msg_box = qt.QMessageBox()
        msg_box.setIcon(qt.QMessageBox.Information)
        msg_box.setWindowTitle(qApp.translate("t", "Внимание"))
        msg_box.setWindowIcon(QIcon(os.path.join(DIR_MEDIA, "ico.png")))
        msg_box.setText(qApp.translate("t", "Не во всех точках из плана тестирования будут проведены измерения."
                                            " Продолжить?"))
        msg_box.addButton(qApp.translate("t", "Да"), qt.QMessageBox.YesRole)
        msg_box.addButton(qApp.translate("t", "Нет"), qt.QMessageBox.NoRole)
        return not msg_box.exec_()

    def _init_ui(self):
        """
        Method initializes widgets on dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "Мультиплексор и план измерения"))
        self.setWindowIcon(QIcon(os.path.join(DIR_MEDIA, "ico.png")))
        self.button_arrange_windows = qt.QPushButton()
        self.button_arrange_windows.setIcon(QIcon(os.path.join(DIR_MEDIA, "arrange_windows.png")))
        self.button_arrange_windows.setToolTip(qApp.translate("t", "Упорядочить окна"))
        self.button_arrange_windows.clicked.connect(self.arrange_windows)
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addStretch(1)
        h_box_layout.addWidget(self.button_arrange_windows)
        self.measurement_plan_widget = MeasurementPlanWidget(self._parent)
        self.multiplexer_pinout_widget = MultiplexerPinoutWidget(self._parent)
        self.multiplexer_pinout_widget.adding_channels_finished.connect(self.turn_off_standby_mode)
        self.multiplexer_pinout_widget.adding_channels_started.connect(self.turn_on_standby_mode)
        self.multiplexer_pinout_widget.channel_added.connect(
            self.measurement_plan_widget.add_pin_with_mux_output_to_plan)
        self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement.clicked.connect(
            self.start_or_stop_plan_measurement)
        splitter = qt.QSplitter(Qt.Vertical)
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(self.multiplexer_pinout_widget)
        splitter.addWidget(self.measurement_plan_widget)
        layout = qt.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(h_box_layout)
        layout.addWidget(splitter)
        self.setLayout(layout)
        self.change_work_mode(self._parent.work_mode)

    @pyqtSlot()
    def arrange_windows(self):
        """
        Slot arranges windows.
        """

        desktop = qApp.instance().desktop()
        height = desktop.availableGeometry().height()
        width = desktop.availableGeometry().width()
        self._parent.move(0, 0)
        self._parent.resize(width // 2, height - 50)
        self.move(width // 2, 0)
        self.resize(width // 2, height - 50)

    @pyqtSlot(WorkMode)
    def change_work_mode(self, new_work_mode: WorkMode):
        """
        Slot changes widgets according to new work mode.
        :param new_work_mode: new work mode.
        """

        self.measurement_plan_widget.set_work_mode(new_work_mode)
        self.multiplexer_pinout_widget.set_work_mode(new_work_mode)

    @pyqtSlot()
    def create_report(self):
        """
        Slot generates report after testing according to plan.
        """

        if self._parent.work_mode is WorkMode.TEST:
            self._parent.create_report(True)

    def select_current_pin(self):
        """
        Method selects row in table for measurement plan for current pin index.
        """

        self.measurement_plan_widget.select_row_for_current_pin()

    @pyqtSlot(bool)
    def start_or_stop_plan_measurement(self, status: bool):
        """
        Slot starts or stops measurements by multiplexer according to existing
        measurement plan.
        :param status: if True then measurements should be started.
        """

        self._change_widgets_to_start_plan_measurement(status)
        self.measurement_plan_runner.start_or_stop_measurements(status)

    @pyqtSlot()
    def turn_off_standby_mode(self):
        """
        Slot turns off standby mode.
        """

        if self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement.isChecked():
            self._change_widgets_to_start_plan_measurement(False)
        self.measurement_plan_widget.turn_off_standby_mode()
        self.multiplexer_pinout_widget.enable_widgets(True)
        self._parent.enable_widgets(True)
        self._parent.connection_action.setEnabled(True)

    @pyqtSlot(int)
    def turn_on_standby_mode(self, total_number: int):
        """
        Slot turns on standby mode.
        :param total_number: number of steps in standby mode.
        """

        self.measurement_plan_widget.turn_on_standby_mode(total_number)
        self.multiplexer_pinout_widget.enable_widgets(False)
        self._parent.enable_widgets(False)
        self._parent.connection_action.setEnabled(False)
        if self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement.isChecked():
            self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement.setEnabled(True)
            self._parent.start_or_stop_entire_plan_measurement_action.setEnabled(True)

    def update_info(self):
        """
        Method updates information about measurement plan and multiplexer.
        """

        self.measurement_plan_widget.update_info()
        self.multiplexer_pinout_widget.update_info()
