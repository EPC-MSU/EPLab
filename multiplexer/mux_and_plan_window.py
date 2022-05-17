"""
File with class to show window with information about multiplexer and
measurement plan.
"""

import os
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtGui import QCloseEvent, QIcon, QShowEvent
from common import WorkMode
from multiplexer.measurement_plan_runner import MeasurementPlanRunner
from multiplexer.measurement_plan_widget import MeasurementPlanWidget
from multiplexer.multiplexer_pinout_widget import MultiplexerPinoutWidget

HEIGHT: int = 400
POS_X: int = 200
POS_Y: int = 200
WIDTH: int = 700


class MuxAndPlanWindow(qt.QWidget):
    """
    Class for dialog window to show information about multiplexer and measurement plan.
    """

    def __init__(self, parent, x: int = POS_X, y: int = POS_Y, width: int = WIDTH, height: int = HEIGHT):
        """
        :param parent: parent main window;
        :param x: initial horizontal position for dialog window;
        :param y: initial vertical position for dialog window;
        :param width: initial width for dialog window;
        :param height: initial height for dialog window.
        """

        super().__init__(None, Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.button_arrange_windows: qt.QPushButton = None
        self.measurement_plan_widget: MeasurementPlanWidget = None
        self.multiplexer_pinout_widget: MultiplexerPinoutWidget = None
        self._dir_name: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
        self._dont_react: bool = False
        self._height: int = height
        self._parent = parent
        self._pos_x: int = x
        self._pos_y: int = y
        self._was_closed: bool = True
        self._width: int = width
        self._init_ui()
        self.measurement_plan_runner: MeasurementPlanRunner = MeasurementPlanRunner(parent,
                                                                                    self.measurement_plan_widget)
        self.measurement_plan_runner.measurements_finished.connect()
        self.measurement_plan_runner.measurements_started.connect()

    def _continue_plan_measurement(self) -> bool:
        """
        Method asks user whether it is necessary to continue measurements according
        to measurement plan.
        :return: True if measurements should be continued.
        """

        msg_box = qt.QMessageBox()
        msg_box.setIcon(qt.QMessageBox.Information)
        msg_box.setWindowTitle(qApp.translate("t", "Внимание"))
        msg_box.setWindowIcon(QIcon(os.path.join(self._dir_name, "ico.png")))
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
        self.setWindowIcon(QIcon(os.path.join(self._dir_name, "ico.png")))
        self.button_arrange_windows = qt.QPushButton(qApp.translate("t", "Упорядочить окна"))
        self.button_arrange_windows.clicked.connect(self.arrange_windows)
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addStretch(1)
        h_box_layout.addWidget(self.button_arrange_windows)
        self.measurement_plan_widget = MeasurementPlanWidget(self._parent)
        self.multiplexer_pinout_widget = MultiplexerPinoutWidget(self._parent)
        self.multiplexer_pinout_widget.adding_channels_finished.connect(
            self.measurement_plan_widget.turn_off_standby_mode)
        self.multiplexer_pinout_widget.adding_channels_started.connect(
            self.measurement_plan_widget.turn_on_standby_mode)
        self.multiplexer_pinout_widget.channel_added.connect(
            self.measurement_plan_widget.add_pin_with_mux_output_to_plan)
        self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement.toggled.connect(
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

        print("Arrange windows")

    @pyqtSlot(WorkMode)
    def change_work_mode(self, new_work_mode: WorkMode):
        """
        Slot changes widgets according to new work mode.
        :param new_work_mode: new work mode.
        """

        self.measurement_plan_widget.set_work_mode(new_work_mode)
        self.multiplexer_pinout_widget.set_work_mode(new_work_mode)

    def closeEvent(self, event: QCloseEvent):
        """
        Method handles event to close dialog window.
        :param event: close event.
        """

        if not self._was_closed:
            self._height = self.height()
            self._pos_x = self.x()
            self._pos_y = self.y()
            self._width = self.width()
        self._was_closed = True

    def select_current_pin(self):
        self.measurement_plan_widget.select_row_for_current_pin()

    def showEvent(self, event: QShowEvent):
        """
        Method handles event to show dialog window.
        :param event: show event.
        """

        if self._was_closed:
            self.setGeometry(self._pos_x, self._pos_y, self._width, self._height)
            self._was_closed = False

    @pyqtSlot(bool)
    def start_or_stop_plan_measurement(self, status: bool):
        """
        Slot starts or stops measurements by multiplexer according to existing
        measurement plan.
        :param status: if True then measurements should be started.
        """

        if self._dont_react:
            self._dont_react = False
            return
        widgets = (self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement,
                   self._parent.start_or_stop_entire_plan_measurement_action)
        if status:
            if self.measurement_plan_runner.get_pins_without_multiplexer_outputs() and\
                    not self._continue_plan_measurement():
                self.sender().setChecked(False)
                return
            text = qApp.translate("t", "Остановить измерение всего плана")
            icon = QIcon(os.path.join(self._dir_name, "stop_auto_test.png"))
        else:
            text = qApp.translate("t", "Запустить измерение всего плана")
            icon = QIcon(os.path.join(self._dir_name, "start_auto_test.png"))
        for widget in widgets:
            widget.setIcon(icon)
            widget.setToolTip(text)
            if widget != self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement:
                widget.setText(text)
            if widget.isChecked() != status:
                self._dont_react = True
                widget.setChecked(status)
        self.measurement_plan_runner.start_or_stop_measurements(status)

    def update_info(self):
        """
        Method updates information about measurement plan and multiplexer.
        """

        self.measurement_plan_widget.update_info()
        self.multiplexer_pinout_widget.update_info()
