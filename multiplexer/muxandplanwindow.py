"""
File with class to show window with information about multiplexer and measurement plan.
"""

import logging
import os
from typing import Any, Callable, Optional, Tuple
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QPoint, QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QSplitter, QStyle, QToolBar,
                             QVBoxLayout, QWidget)
from epcore.analogmultiplexer.base import AnalogMultiplexerBase, MultiplexerOutput
from epcore.analogmultiplexer.epmux.epmux import UrpcDeviceUndefinedError
from dialogs.save_geometry import update_widget_to_save_geometry
from window import utils as ut
from window.common import WorkMode
from window.pedalhandler import add_pedal_handler
from window.scaler import update_scale_of_class
from .measurementplanrunner import MeasurementPlanRunner
from .measurementplanwidget import MeasurementPlanWidget
from .multiplexerpinoutwidget import MultiplexerPinoutWidget


logger = logging.getLogger("eplab")


def check_multiplexer(func: Callable[..., Any]):
    """
    Decorator checks for a connected multiplexer.
    :param func: function to be decorated.
    """

    def wrapper(self, *args, **kwargs) -> Any:
        if not self.multiplexer:
            return None
        return func(self, *args, **kwargs)

    return wrapper


@add_pedal_handler
@update_widget_to_save_geometry
@update_scale_of_class
class MuxAndPlanWindow(QWidget):
    """
    Class for dialog window to show information about multiplexer and measurement plan.
    """

    COLOR_NOT_TESTED: str = "#F9E154"
    MARGIN: int = 10
    MIN_WIDTH: int = 700

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self._main_window = main_window
        self._manual_stop: bool = False
        self._previous_main_window_pos: Optional[QPoint] = None
        self._previous_main_window_size: Optional[QSize] = None
        self._previous_window_pos: Optional[QPoint] = None
        self._previous_window_size: Optional[QSize] = None
        self._init_ui()

        self.measurement_plan_runner: MeasurementPlanRunner = MeasurementPlanRunner(main_window,
                                                                                    self.measurement_plan_widget)
        self.measurement_plan_runner.measurement_done.connect(self.change_progress)
        self.measurement_plan_runner.measurements_finished.connect(self.turn_off_standby_mode)
        self.measurement_plan_runner.measurements_finished.connect(self.create_report)
        self.measurement_plan_runner.measurements_started.connect(self.turn_on_standby_mode)

    @property
    def multiplexer(self) -> Optional[AnalogMultiplexerBase]:
        """
        :return: multiplexer.
        """

        if self._main_window.measurement_plan:
            return self._main_window.measurement_plan.multiplexer
        return None

    def _change_widgets_to_start_measurements_according_plan(self, status: bool) -> None:
        """
        Method changes the text and icon of widgets that launch measurements according to plan.
        :param status: if True then measurements should be started.
        """

        if status:
            text = qApp.translate("mux", "Остановить измерение всех точек")
            icon = QIcon(os.path.join(ut.DIR_MEDIA, "stop_auto_test.png"))
        else:
            text = qApp.translate("mux", "Запустить измерение всех точек")
            icon = QIcon(os.path.join(ut.DIR_MEDIA, "start_auto_test.png"))
        widget = self._main_window.start_or_stop_entire_plan_measurement_action
        widget.setIcon(icon)
        widget.setText(text)
        if widget.isChecked() != status:
            widget.setChecked(status)

    def _check_multiplexer_connection(self) -> None:
        """
        Method checks the connection of the multiplexer.
        """

        try:
            self._main_window.measurement_plan.multiplexer.get_identity_information()
        except UrpcDeviceUndefinedError as exc:
            logger.error("Failed to get identity information from multiplexer (%s)", exc)
            self.multiplexer_pinout_widget.set_visible(False)
        else:
            self.multiplexer_pinout_widget.set_visible(True)

    @staticmethod
    def _continue_plan_measurement(text: str) -> bool:
        """
        Method asks user whether it is necessary to continue measurements according to the measurement plan.
        :param text: message text for the user.
        :return: True if measurements should be continued.
        """

        return not ut.show_message(qApp.translate("t", "Внимание"), text, icon=QMessageBox.Information, yes_button=True,
                                   no_button=True)

    def _create_bottom_widget(self) -> QWidget:
        """
        :return: widgets that are located at the bottom of the dialog box.
        """

        self.measurement_plan_widget: MeasurementPlanWidget = MeasurementPlanWidget(self._main_window)
        self.progress_bar: QProgressBar = QProgressBar()
        self.progress_bar.setVisible(False)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(0)
        h_layout.setContentsMargins(MuxAndPlanWindow.MARGIN, 0, MuxAndPlanWindow.MARGIN, MuxAndPlanWindow.MARGIN)
        h_layout.addWidget(self.progress_bar, 2)
        h_layout.addStretch(1)

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(MuxAndPlanWindow.MARGIN, 0, MuxAndPlanWindow.MARGIN, 0)
        v_layout.addWidget(self.measurement_plan_widget)
        v_layout.addLayout(h_layout)
        widget = QWidget()
        widget.setLayout(v_layout)
        return widget

    def _create_top_widget(self) -> QWidget:
        """
        :return: widgets that are located at the top of the dialog box.
        """

        self.label: QLabel = QLabel(qApp.translate("mux", "Режим тестирования:"))
        self.tool_bar: QToolBar = QToolBar()
        self.tool_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.tool_bar.addAction(self._main_window.writing_mode_action)
        self.tool_bar.addAction(self._main_window.testing_mode_action)
        self.tool_bar.addAction(self._main_window.start_or_stop_entire_plan_measurement_action)
        self.multiplexer_pinout_widget: MultiplexerPinoutWidget = MultiplexerPinoutWidget(self._main_window)
        self.multiplexer_pinout_widget.mux_output_turned_on.connect(self.handle_mux_output_turned_on)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(0)
        h_layout.setContentsMargins(MuxAndPlanWindow.MARGIN, 0, MuxAndPlanWindow.MARGIN, 0)
        h_layout.addWidget(self.label)
        h_layout.addWidget(self.tool_bar)
        h_layout.addStretch(1)

        v_layout = QVBoxLayout()
        v_layout.setSpacing(0)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self.multiplexer_pinout_widget)
        v_layout.addLayout(h_layout)

        widget = QWidget()
        widget.setLayout(v_layout)
        return widget

    def _init_ui(self) -> None:
        """
        Method initializes widgets on dialog window.
        """

        self.setWindowTitle(qApp.translate("mux", "Мультиплексор и план измерения"))
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))

        self.button_arrange_windows: QPushButton = QPushButton(qApp.translate("mux", "Упорядочить окна"))
        self.button_arrange_windows.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "arrange_windows.png")))
        self.button_arrange_windows.clicked.connect(self.arrange_windows)

        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(self.button_arrange_windows)

        self.splitter: QSplitter = QSplitter(Qt.Vertical)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self._create_top_widget())
        self.splitter.addWidget(self._create_bottom_widget())
        self.splitter.setHandleWidth(1)
        self.splitter.handle(1).setAttribute(Qt.WA_Hover)
        self.splitter.setStyleSheet("QSplitter::handle {background-color: gray; margin: 5px 0px;}"
                                    "QSplitter::handle:hover {background-color: black; margin: 5px 0px;}")

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(h_layout)
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        self.change_work_mode(self._main_window.work_mode)
        self.setMinimumWidth(MuxAndPlanWindow.MIN_WIDTH)

    def _is_arranged(self) -> Tuple[bool, QPoint, QSize, QPoint, QSize]:
        """
        Method checks if the main application window and the multiplexer dialog are in order.
        :return: True if windows are ordered by size and position.
        """

        geometry = qApp.instance().desktop().availableGeometry()
        height = geometry.height()
        width = geometry.width()
        main_window_pos = QPoint(geometry.x(), geometry.y())
        height -= self.style().pixelMetric(QStyle.PM_TitleBarHeight)
        if width > 1280:
            main_window_size = QSize(width // 2, height)
            window_pos = QPoint(main_window_pos.x() + main_window_size.width(), main_window_pos.y())
            window_size = QSize(width // 2, height)
        elif width < 1280:
            main_window_size = QSize(self._main_window.minimumWidth(), height)
            window_size = QSize(self.minimumWidth(), height)
            window_pos = QPoint(main_window_pos.x() + width - window_size.width(), main_window_pos.y())
        else:
            main_window_size = QSize(self._main_window.minimumWidth(), height)
            window_pos = QPoint(main_window_pos.x() + main_window_size.width(), main_window_pos.y())
            window_size = QSize(width - main_window_size.width(), height)
        current_main_window_pos = self._main_window.pos()
        current_main_window_size = self._main_window.size()
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
        Method stops measurements by the multiplexer according to the measurement plan.
        """

        self._manual_stop = True
        self._change_widgets_to_start_measurements_according_plan(False)
        self.measurement_plan_runner.start_or_stop_measurements(False)
        self.setEnabled(False)

    @pyqtSlot()
    def arrange_windows(self) -> None:
        """
        Slot arranges the application's main window and this dialog window.
        """

        main_window_pos, main_window_size, window_pos, window_size = self._is_arranged()[1:]
        self._main_window.move(main_window_pos)
        self._main_window.resize(main_window_size)
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

    def close_and_stop_plan_measurement(self) -> None:
        """
        Method closes dialog window and stops measurements according to plan.
        """

        self._stop_plan_measurement()
        self.close()

    @pyqtSlot()
    def create_report(self) -> None:
        """
        Slot generates report after testing according to plan.
        """

        if self._main_window.work_mode is WorkMode.TEST and not self._manual_stop:
            self._main_window.create_report(True)
        self._manual_stop = False

    @pyqtSlot(MultiplexerOutput)
    def handle_mux_output_turned_on(self, mux_output: MultiplexerOutput) -> None:
        """
        Slot processes the signal to turn on the given multiplexer output.
        :param mux_output: multiplexer output.
        """

        index = self.measurement_plan_widget.get_pin_index(mux_output)
        if index is not None:
            self._main_window.handle_changing_pin_in_mux(index)

    def select_current_pin(self) -> None:
        """
        Method selects row in table for measurement plan for current pin index.
        """

        self.measurement_plan_widget.select_row()

    @check_multiplexer
    def set_connection_mode(self) -> None:
        """
        Method switches window to mode when devices are connected to application.
        """

        self.setEnabled(True)
        self._check_multiplexer_connection()

    @check_multiplexer
    def set_disconnection_mode(self) -> None:
        """
        Method switches window to mode when devices are disconnected from application.
        """

        if self.isEnabled():
            self._stop_plan_measurement()
        self._check_multiplexer_connection()

    @pyqtSlot(bool)
    def start_or_stop_plan_measurement(self, status: bool) -> None:
        """
        Slot starts or stops measurements by the multiplexer according to the measurement plan.
        :param status: if True then measurements should be started.
        """

        color = '<span style="background-color: {};">{}</span>'.format(MuxAndPlanWindow.COLOR_NOT_TESTED,
                                                                       qApp.translate("mux", "жёлтым"))
        text = qApp.translate("mux", "Не все точки имеют выходы мультиплексора и/или не все выходы могут быть "
                                     "установлены. Поэтому исключенные из теста точки будут выделены {} цветом. Хотите "
                                     "продолжить?")
        if status and self.measurement_plan_runner.check_pins_without_multiplexer_outputs() and \
                not self._continue_plan_measurement(text.format(color)):
            self.sender().setChecked(False)
            return

        text = qApp.translate("mux", "В плане тестирования есть эталонные сигнатуры. При запуске измерений в режиме "
                                     "записи плана все имеющиеся сигнатуры будут перезаписаны. Вы точно хотите "
                                     "запустить измерение всех точек?")
        if status and self._main_window.is_measured_pin and self._main_window.work_mode is WorkMode.WRITE and \
                not self._continue_plan_measurement(text):
            self.sender().setChecked(False)
            return

        self._change_widgets_to_start_measurements_according_plan(status)
        self.measurement_plan_runner.start_or_stop_measurements(status)

    @pyqtSlot()
    def turn_off_standby_mode(self) -> None:
        """
        Slot turns off standby mode.
        """

        if self._main_window.start_or_stop_entire_plan_measurement_action.isChecked():
            self._change_widgets_to_start_measurements_according_plan(False)
        self.measurement_plan_widget.turn_off_standby_mode()
        self.progress_bar.setVisible(False)

        self.multiplexer_pinout_widget.enable_widgets(True)
        self._main_window.enable_widgets(True)
        if self._main_window.work_mode is WorkMode.TEST:
            self._main_window.search_optimal_action.setEnabled(False)
        for action in (self._main_window.connection_action, self._main_window.new_point_action,
                       self._main_window.open_file_action, self._main_window.remove_point_action):
            action.setEnabled(True)
        for action in (self._main_window.new_point_action, self._main_window.remove_point_action):
            action.setEnabled(False)
        self._main_window.set_enabled_save_point_action_at_test_mode()

    @pyqtSlot(int)
    def turn_on_standby_mode(self, total_number: int) -> None:
        """
        Slot turns on standby mode.
        :param total_number: number of steps in standby mode.
        """

        self.measurement_plan_widget.turn_on_standby_mode()
        self.progress_bar.setVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(total_number)
        self.progress_bar.setValue(0)

        self.multiplexer_pinout_widget.enable_widgets(False)
        self._main_window.enable_widgets(False)
        for action in (self._main_window.connection_action, self._main_window.open_file_action):
            action.setEnabled(False)
        self._main_window.open_mux_window_action.setEnabled(True)
        if self._main_window.start_or_stop_entire_plan_measurement_action.isChecked():
            self._main_window.start_or_stop_entire_plan_measurement_action.setEnabled(True)

    def update_info(self) -> None:
        """
        Method updates information about the measurement plan and the multiplexer.
        """

        self.measurement_plan_widget.update_info()
        self.multiplexer_pinout_widget.update_info()
