"""
File with class to show window with information about multiplexer and
measurement plan.
"""

import os
from typing import Tuple
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QPoint, QSize, Qt
from PyQt5.QtGui import QIcon
from epcore.analogmultiplexer.epmux.epmux import UrpcDeviceUndefinedError
from eplab.common import WorkMode
from multiplexer.measurement_plan_runner import MeasurementPlanRunner
from multiplexer.measurement_plan_widget import MeasurementPlanWidget
from multiplexer.multiplexer_pinout_widget import MultiplexerPinoutWidget


DIR_MEDIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")


class MuxAndPlanWindow(qt.QWidget):
    """
    Class for dialog window to show information about multiplexer and measurement plan.
    """

    COLOR_NOT_TESTED: str = "#F9E154"
    DEFAULT_HEIGHT: int = 500
    DEFAULT_MUX_HEIGHT: int = 300
    DEFAULT_WIDTH: int = 700

    def __init__(self, parent) -> None:
        """
        :param parent: parent main window.
        """

        super().__init__(None, Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.button_arrange_windows: qt.QPushButton = None
        self.measurement_plan_widget: MeasurementPlanWidget = None
        self.multiplexer_pinout_widget: MultiplexerPinoutWidget = None
        self.splitter: qt.QSplitter = None
        self._manual_stop: bool = True
        self._parent = parent
        self._previous_main_window_pos: QPoint = None
        self._previous_main_window_size: QSize = None
        self._previous_window_pos: QPoint = None
        self._previous_window_size: QSize = None
        self._init_ui()
        self.measurement_plan_runner: MeasurementPlanRunner = MeasurementPlanRunner(parent,
                                                                                    self.measurement_plan_widget)
        self.measurement_plan_runner.measurement_done.connect(self.measurement_plan_widget.change_progress)
        self.measurement_plan_runner.measurements_finished.connect(self.turn_off_standby_mode)
        self.measurement_plan_runner.measurements_finished.connect(self.create_report)
        self.measurement_plan_runner.measurements_started.connect(self.turn_on_standby_mode)

    def _change_widgets_to_start_plan_measurement(self, status: bool) -> None:
        """
        Method changes widgets to start or stop plan measurements according status of one of them.
        :param status: status of one of widgets to start plan measurements.
        """

        widgets = (self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement,
                   self._parent.start_or_stop_entire_plan_measurement_action)
        if status:
            text = qApp.translate("t", "Остановить измерение всего плана")
            icon = QIcon(os.path.join(DIR_MEDIA, "stop_auto_test.png"))
        else:
            text = qApp.translate("t", "Запустить измерение всего плана")
            icon = QIcon(os.path.join(DIR_MEDIA, "start_auto_test.png"))
        for widget in widgets:
            widget.setIcon(icon)
            widget.setText(text)
            widget.setToolTip(text)
            if widget.isChecked() != status:
                widget.setChecked(status)

    def _check_multiplexer_connection(self) -> None:
        """
        Method checks connection of multiplexer.
        """

        try:
            self._parent.measurement_plan.multiplexer.get_identity_information()
        except UrpcDeviceUndefinedError:
            self.multiplexer_pinout_widget.set_visible(False)
        else:
            self.multiplexer_pinout_widget.set_visible(True)
        self.multiplexer_pinout_widget.stop_sending_channels()

    def _continue_plan_measurement(self) -> bool:
        """
        Method asks user whether it is necessary to continue measurements according to measurement plan.
        :return: True if measurements should be continued.
        """

        msg_box = qt.QMessageBox()
        msg_box.setIcon(qt.QMessageBox.Information)
        msg_box.setWindowTitle(qApp.translate("t", "Внимание"))
        msg_box.setWindowIcon(QIcon(os.path.join(DIR_MEDIA, "ico.png")))
        color = '<span style="background-color: {};">{}</span>'.format(self.COLOR_NOT_TESTED,
                                                                       qApp.translate("t", "жёлтым"))
        text = qApp.translate("t", "Не все точки имеют выходы мультиплексора и/или не все выходы могут быть "
                                   "установлены. Поэтому исключенные из теста точки будут выделены {} цветом. Хотите "
                                   "продолжить?")
        msg_box.setText(text.format(color))
        msg_box.addButton(qApp.translate("t", "Да"), qt.QMessageBox.YesRole)
        msg_box.addButton(qApp.translate("t", "Нет"), qt.QMessageBox.NoRole)
        return not msg_box.exec_()

    def _init_ui(self) -> None:
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
        self.splitter = qt.QSplitter(Qt.Vertical)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.multiplexer_pinout_widget)
        self.splitter.addWidget(self.measurement_plan_widget)
        layout = qt.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(h_box_layout)
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        self.change_work_mode(self._parent.work_mode)

    def _is_arranged(self) -> Tuple:
        """
        Method checks if windows are arranged.
        :return: True if windows are arranged, position and size for main window, position and size for dialog window.
        """

        desktop = qApp.instance().desktop()
        height = desktop.availableGeometry().height()
        width = desktop.availableGeometry().width()
        main_window_pos = QPoint(desktop.availableGeometry().x(), desktop.availableGeometry().y())
        height -= 50
        if 1280 < width:
            main_window_size = QSize(width // 2, height)
            window_pos = QPoint(main_window_pos.x() + main_window_size.width(), main_window_pos.y())
            window_size = QSize(width // 2, height)
        elif width < 1280:
            main_window_size = QSize(self._parent.minimumWidth(), height)
            window_size = QSize(self.minimumWidth(), height)
            window_pos = QPoint(main_window_pos.x() + width - window_size.width(), main_window_pos.y())
        else:
            main_window_size = QSize(self._parent.minimumWidth(), height)
            window_pos = QPoint(main_window_pos.x() + main_window_size.width(), main_window_pos.y())
            window_size = QSize(width - main_window_size.width(), height)
        current_main_window_pos = self._parent.pos()
        current_main_window_size = self._parent.size()
        current_window_pos = self.pos()
        current_window_size = self.size()
        if current_main_window_pos != main_window_pos or current_main_window_size != main_window_size or\
                current_window_pos != window_pos or current_window_size != window_size:
            arranged = False
            self._previous_main_window_pos = current_main_window_pos
            self._previous_main_window_size = current_main_window_size
            self._previous_window_pos = current_window_pos
            self._previous_window_size = current_window_size
        else:
            arranged = True
            main_window_pos = self._previous_main_window_pos
            main_window_size = self._previous_main_window_size
            window_pos = self._previous_window_pos
            window_size = self._previous_window_size
        return arranged, main_window_pos, main_window_size, window_pos, window_size

    def _resize_window(self) -> None:
        """
        Method resizes window depending on presence of multiplexer.
        """

        if not self._parent.measurement_plan or not self._parent.measurement_plan.multiplexer or\
                self._is_arranged()[0] or self.isVisible():
            return
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self.splitter.setSizes([self.DEFAULT_MUX_HEIGHT, self.DEFAULT_HEIGHT - self.DEFAULT_MUX_HEIGHT])

    def _stop_plan_measurement(self) -> None:
        """
        Method stops measurements by multiplexer according to measurement plan.
        """

        self._manual_stop = True
        self._change_widgets_to_start_plan_measurement(False)
        self.measurement_plan_runner.start_or_stop_measurements(False)
        self.setEnabled(False)

    @pyqtSlot()
    def arrange_windows(self) -> None:
        """
        Slot arranges windows.
        """

        main_window_pos, main_window_size, window_pos, window_size = self._is_arranged()[1:]
        self._parent.move(main_window_pos)
        self._parent.resize(main_window_size)
        self.move(window_pos)
        self.resize(window_size)

    @pyqtSlot(WorkMode)
    def change_work_mode(self, new_work_mode: WorkMode) -> None:
        """
        Slot changes widgets according to new work mode.
        :param new_work_mode: new work mode.
        """

        self.measurement_plan_widget.set_work_mode(new_work_mode)
        self.multiplexer_pinout_widget.set_work_mode(new_work_mode)

    @pyqtSlot()
    def create_report(self) -> None:
        """
        Slot generates report after testing according to plan.
        """

        if self._parent.work_mode is WorkMode.TEST and not self._manual_stop:
            self._parent.create_report(True)
        self._manual_stop = False

    def select_current_pin(self) -> None:
        """
        Method selects row in table for measurement plan for current pin index.
        """

        self.measurement_plan_widget.select_row_for_current_pin()

    def set_connection_mode(self) -> None:
        """
        Method switches window to mode when devices are connected to application.
        """

        if not self._parent.measurement_plan.multiplexer:
            return
        self.setEnabled(True)
        self._check_multiplexer_connection()

    def set_disconnection_mode(self) -> None:
        """
        Method switches window to mode when devices are disconnected from application.
        """

        if not self._parent.measurement_plan.multiplexer:
            return
        if self.isEnabled():
            self._stop_plan_measurement()
        self._check_multiplexer_connection()

    @pyqtSlot(bool)
    def start_or_stop_plan_measurement(self, status: bool) -> None:
        """
        Slot starts or stops measurements by multiplexer according to existing measurement plan.
        :param status: if True then measurements should be started.
        """

        self.measurement_plan_widget.validate_mux_outputs_for_pins()
        if status and self.measurement_plan_runner.get_pins_without_multiplexer_outputs() and \
                not self._continue_plan_measurement():
            self.sender().setChecked(False)
            return
        self._change_widgets_to_start_plan_measurement(status)
        self.measurement_plan_runner.start_or_stop_measurements(status)

    @pyqtSlot()
    def turn_off_standby_mode(self) -> None:
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
    def turn_on_standby_mode(self, total_number: int) -> None:
        """
        Slot turns on standby mode.
        :param total_number: number of steps in standby mode.
        """

        self.measurement_plan_widget.turn_on_standby_mode(total_number)
        self.multiplexer_pinout_widget.enable_widgets(False)
        self._parent.enable_widgets(False)
        self._parent.connection_action.setEnabled(False)
        self._parent.open_mux_window_action.setEnabled(True)
        if self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement.isChecked():
            self.multiplexer_pinout_widget.button_start_or_stop_entire_plan_measurement.setEnabled(True)
            self._parent.start_or_stop_entire_plan_measurement_action.setEnabled(True)

    def update_info(self) -> None:
        """
        Method updates information about measurement plan and multiplexer.
        """

        self.measurement_plan_widget.update_info()
        self.multiplexer_pinout_widget.update_info()
        self._resize_window()
