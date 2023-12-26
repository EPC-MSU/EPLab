"""
File with class to show window with information about multiplexer and measurement plan.
"""

import os
from typing import Tuple
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QPoint, QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QSplitter, QVBoxLayout, QWidget
from epcore.analogmultiplexer.epmux.epmux import UrpcDeviceUndefinedError
from dialogs.save_geometry import update_widget_to_save_geometry
from multiplexer.measurementplanrunner import MeasurementPlanRunner
from multiplexer.measurementplanwidget import MeasurementPlanWidget
from multiplexer.multiplexerpinoutwidget import MultiplexerPinoutWidget
from window import utils as ut
from window.common import WorkMode
from window.pedalhandler import add_pedal_handler
from window.scaler import update_scale_of_class


@add_pedal_handler
@update_widget_to_save_geometry
@update_scale_of_class
class MuxAndPlanWindow(QWidget):
    """
    Class for dialog window to show information about multiplexer and measurement plan.
    """

    COLOR_NOT_TESTED: str = "#F9E154"
    DEFAULT_HEIGHT: int = 500
    DEFAULT_MUX_HEIGHT: int = 300
    DEFAULT_WIDTH: int = 700

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self._manual_stop: bool = False
        self._parent = main_window
        self._previous_main_window_pos: QPoint = None
        self._previous_main_window_size: QSize = None
        self._previous_window_pos: QPoint = None
        self._previous_window_size: QSize = None
        self._init_ui()
        self.measurement_plan_runner: MeasurementPlanRunner = MeasurementPlanRunner(main_window,
                                                                                    self.measurement_plan_widget)
        self.measurement_plan_runner.measurement_done.connect(self.change_progress)
        self.measurement_plan_runner.measurements_finished.connect(self.turn_off_standby_mode)
        self.measurement_plan_runner.measurements_finished.connect(self.create_report)
        self.measurement_plan_runner.measurements_started.connect(self.turn_on_standby_mode)

    def _change_widgets_to_start_plan_measurement(self, status: bool) -> None:
        """
        Method changes widgets to start or stop plan measurements according status of one of them.
        :param status: status of one of widgets to start plan measurements.
        """

        if status:
            text = qApp.translate("t", "Остановить измерение всех точек")
            icon = QIcon(os.path.join(ut.DIR_MEDIA, "stop_auto_test.png"))
        else:
            text = qApp.translate("t", "Запустить измерение всех точек")
            icon = QIcon(os.path.join(ut.DIR_MEDIA, "start_auto_test.png"))
        for widget in (self.button_start_or_stop_plan_measurement,
                       self._parent.start_or_stop_entire_plan_measurement_action):
            widget.setIcon(icon)
            widget.setText(text)
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

    @staticmethod
    def _continue_plan_measurement() -> bool:
        """
        Method asks user whether it is necessary to continue measurements according to measurement plan.
        :return: True if measurements should be continued.
        """

        color = '<span style="background-color: {};">{}</span>'.format(MuxAndPlanWindow.COLOR_NOT_TESTED,
                                                                       qApp.translate("t", "жёлтым"))
        text = qApp.translate("t", "Не все точки имеют выходы мультиплексора и/или не все выходы могут быть "
                                   "установлены. Поэтому исключенные из теста точки будут выделены {} цветом. Хотите "
                                   "продолжить?")
        return not ut.show_message(qApp.translate("t", "Внимание"), text.format(color), icon=QMessageBox.Information,
                                   yes_button=True, no_button=True)

    def _create_bottom_widget(self) -> QWidget:
        self.measurement_plan_widget: MeasurementPlanWidget = MeasurementPlanWidget(self._parent)
        self.progress_bar: QProgressBar = QProgressBar()
        self.progress_bar.setVisible(False)

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.progress_bar, 2)
        h_layout.addStretch(1)
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.measurement_plan_widget)
        v_layout.addWidget(self.progress_bar)
        widget = QWidget()
        widget.setLayout(v_layout)
        return widget

    def _create_top_widget(self) -> QWidget:
        self.label: QLabel = QLabel(qApp.translate("t", "Режим тестирования"))
        self.button_write_mode: QPushButton = QPushButton(qApp.translate("t", "Запись плана тестирования"))
        self.button_write_mode.setCheckable(True)
        self.button_test_mode: QPushButton = QPushButton(qApp.translate("t", "Тестирование по плану"))
        self.button_test_mode.setCheckable(True)
        self.button_start_or_stop_plan_measurement: QPushButton = QPushButton(
            qApp.translate("t", "Запустить измерение всех точек"))
        self.button_start_or_stop_plan_measurement.clicked.connect(self.start_or_stop_plan_measurement)
        self.button_start_or_stop_plan_measurement.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "start_auto_test.png")))
        self.button_start_or_stop_plan_measurement.setCheckable(True)
        self.multiplexer_pinout_widget: MultiplexerPinoutWidget = MultiplexerPinoutWidget(self._parent)

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.label)
        h_layout.addWidget(self.button_write_mode)
        h_layout.addWidget(self.button_test_mode)
        h_layout.addStretch(1)
        h_layout.addWidget(self.button_start_or_stop_plan_measurement)

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.multiplexer_pinout_widget)
        v_layout.addLayout(h_layout)

        widget = QWidget()
        widget.setLayout(v_layout)
        return widget

    def _init_ui(self) -> None:
        """
        Method initializes widgets on dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "Мультиплексор и план измерения"))
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))

        self.button_arrange_windows: QPushButton = QPushButton()
        self.button_arrange_windows.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "arrange_windows.png")))
        self.button_arrange_windows.setToolTip(qApp.translate("t", "Упорядочить окна"))
        self.button_arrange_windows.clicked.connect(self.arrange_windows)
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(self.button_arrange_windows)

        top_widget = self._create_top_widget()
        bottom_widget = self._create_bottom_widget()

        self.splitter: QSplitter = QSplitter(Qt.Vertical)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(top_widget)
        self.splitter.addWidget(bottom_widget)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(h_layout)
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        self.change_work_mode(self._parent.work_mode)

    def _is_arranged(self) -> Tuple[bool, QPoint, QSize, QPoint, QSize]:
        """
        Method checks if windows are arranged.
        :return: True if windows are arranged, position and size for main window, position and size for dialog window.
        """

        desktop = qApp.instance().desktop()
        height = desktop.availableGeometry().height()
        width = desktop.availableGeometry().width()
        main_window_pos = QPoint(desktop.availableGeometry().x(), desktop.availableGeometry().y())
        height -= 50
        if width > 1280:
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

    @pyqtSlot()
    def change_progress(self) -> None:
        """
        Slots changes value for progress bar.
        """

        value = self.progress_bar.value()
        self.progress_bar.setValue(value + 1)

    @pyqtSlot(WorkMode)
    def change_work_mode(self, new_work_mode: WorkMode) -> None:
        """
        Slot changes widgets according to new work mode.
        :param new_work_mode: new work mode.
        """

        self.measurement_plan_widget.set_work_mode(new_work_mode)

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

        if self.button_start_or_stop_plan_measurement.isChecked():
            self._change_widgets_to_start_plan_measurement(False)
        self.measurement_plan_widget.turn_off_standby_mode()
        self.progress_bar.setVisible(False)
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
        self.progress_bar.setVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(total_number)
        self.progress_bar.setValue(0)

        self.multiplexer_pinout_widget.enable_widgets(False)
        self._parent.enable_widgets(False)
        self._parent.connection_action.setEnabled(False)
        self._parent.open_mux_window_action.setEnabled(True)
        if self.button_start_or_stop_plan_measurement.isChecked():
            self.button_start_or_stop_plan_measurement.setEnabled(True)
            self._parent.start_or_stop_entire_plan_measurement_action.setEnabled(True)

    def update_info(self) -> None:
        """
        Method updates information about measurement plan and multiplexer.
        """

        self.measurement_plan_widget.update_info()
        self.multiplexer_pinout_widget.update_info()
