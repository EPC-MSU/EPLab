"""
File with class to show window with information about multiplexer and measurement plan.
"""

import logging
import os
from typing import Any, Callable, Optional, Tuple
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QPoint, QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSplitter, QToolBar,
                             QVBoxLayout, QWidget)
from epcore.analogmultiplexer.base import AnalogMultiplexerBase, MAX_CHANNEL_NUMBER, MultiplexerOutput
from dialogs import ProgressWindow
from dialogs.save_geometry import update_widget_to_save_geometry
from window import utils as ut
from window.common import WorkMode
from window.pedalhandler import add_pedal_handler
from .measurementplanwidget import MeasurementPlanWidget
from .multiplexerpinoutwidget import MultiplexerPinoutWidget
from .muxmeasurementrunner import MuxMeasurementRunner


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
        self._previous_main_window_pos: Optional[QPoint] = None
        self._previous_main_window_size: Optional[QSize] = None
        self._previous_window_pos: Optional[QPoint] = None
        self._previous_window_size: Optional[QSize] = None
        self._init_ui()
        self._create_mux_measurement_runner()

    @property
    def multiplexer(self) -> Optional[AnalogMultiplexerBase]:
        """
        :return: multiplexer.
        """

        if self._main_window.measurement_plan:
            return self._main_window.measurement_plan.multiplexer

        return None

    @property
    def mux_measurements_are_running(self) -> bool:
        """
        :return: True if the measurements according to the plan are performed using a multiplexer.
        """

        return self._mux_measurement_runner.is_running

    @staticmethod
    def _continue_plan_measurement(text: str) -> bool:
        """
        Method asks user whether it is necessary to continue measurements according to the measurement plan.
        :param text: message text for the user.
        :return: True if measurements should be continued.
        """

        result = ut.show_message(qApp.translate("t", "Внимание"), text, icon=QMessageBox.Icon.Information,
                                 yes_button=True, no_button=True)
        return result == QMessageBox.ButtonRole.AcceptRole

    def _create_mux_measurement_runner(self) -> None:
        self._mux_measurement_runner: MuxMeasurementRunner = MuxMeasurementRunner()
        self._mux_measurement_runner.device_errors_occurred.connect(
            self._main_window.set_device_errors_from_mux_measurement_runner)
        self._mux_measurement_runner.measurements_finished.connect(
            self._main_window.update_state_after_measurement_by_multiplexer)
        self._mux_measurement_runner.start()

    def _create_top_widget(self) -> QWidget:
        """
        :return: widgets that are located at the top of the dialog box.
        """

        self.label: QLabel = QLabel(qApp.translate("mux", "Режим тестирования:"))
        self.tool_bar: QToolBar = QToolBar()
        self.tool_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.tool_bar.addAction(self._main_window.writing_mode_action)
        self.tool_bar.addAction(self._main_window.testing_mode_action)
        self.tool_bar.addAction(self._main_window.start_plan_measurement_action)
        self.multiplexer_pinout_widget: MultiplexerPinoutWidget = MultiplexerPinoutWidget(self._main_window)
        self.multiplexer_pinout_widget.mux_output_turned_on.connect(self.handle_mux_output_turned_on)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(0)
        h_layout.setContentsMargins(self.MARGIN, 0, self.MARGIN, 0)
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

        self.setWindowTitle(qApp.translate("mux", "Мультиплексор и план тестирования"))
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))

        self.button_arrange_windows: QPushButton = QPushButton(qApp.translate("mux", "Упорядочить окна"))
        self.button_arrange_windows.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "arrange_windows.png")))
        self.button_arrange_windows.clicked.connect(self.arrange_windows)

        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(self.button_arrange_windows)

        self.measurement_plan_widget: MeasurementPlanWidget = MeasurementPlanWidget(self._main_window)

        self.splitter: QSplitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self._create_top_widget())
        self.splitter.addWidget(self.measurement_plan_widget)
        self.splitter.setHandleWidth(1)
        self.splitter.handle(1).setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.splitter.setStyleSheet("QSplitter::handle {background-color: gray; margin: 5px 0px;}"
                                    "QSplitter::handle:hover {background-color: black; margin: 5px 0px;}")

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(h_layout)
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        self.change_work_mode(self._main_window.work_mode)
        self.setMinimumWidth(self.MIN_WIDTH)

    def _is_arranged(self) -> Tuple[bool, QPoint, QSize, QPoint, QSize]:
        """
        Method checks if the main application window and the multiplexer dialog are in order.
        :return: True if windows are ordered by size and position.
        """

        geometry = qApp.instance().primaryScreen().availableGeometry()
        height = geometry.height()
        width = geometry.width()
        main_window_pos = QPoint(geometry.x(), geometry.y())
        border_height = self._main_window.frameGeometry().height() - self._main_window.geometry().height()
        height -= border_height
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

        self._mux_measurement_runner.stop_measurements()

    @pyqtSlot()
    def arrange_windows(self) -> None:
        """
        Slot arranges the application's main window and this dialog window.
        """

        main_window_pos, main_window_size, window_pos, window_size = self._is_arranged()[1:]

        if self._main_window.isMaximized():
            self._main_window.setWindowState(self._main_window.windowState() & ~Qt.WindowState.WindowMaximized)

        if self.isMaximized():
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMaximized)

        self._main_window.move(main_window_pos)
        self._main_window.resize(main_window_size)
        self.move(window_pos)
        self.resize(window_size)

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

    @pyqtSlot(MultiplexerOutput)
    def handle_mux_output_turned_on(self, output: MultiplexerOutput) -> None:
        """
        Slot processes the signal to turn on the given multiplexer output.
        :param output: multiplexer output.
        """

        index = (output.module_number - 1) * MAX_CHANNEL_NUMBER + output.channel_number - 1
        self._main_window.go_to_selected_pin(index)

    def select_current_pin(self) -> None:
        """
        Method selects row in table for measurement plan for current pin index.
        """

        self.measurement_plan_widget.select_row()

        index = self._main_window.measurement_plan.get_current_index()
        if index is not None:
            module_number = index // MAX_CHANNEL_NUMBER + 1
            channel_number = index % MAX_CHANNEL_NUMBER + 1
            self.multiplexer_pinout_widget.show_connected_output(MultiplexerOutput(channel_number=channel_number,
                                                                                   module_number=module_number))

    @pyqtSlot()
    def start_plan_measurement(self) -> None:
        """
        Slot starts measurements by the multiplexer according to the measurement plan.
        """

        color = '<span style="background-color: {};">{}</span>'.format(self.COLOR_NOT_TESTED,
                                                                       qApp.translate("mux", "жёлтым"))
        text = qApp.translate("mux", "Не все точки имеют выходы мультиплексора и/или не все выходы могут быть "
                                     "установлены. Поэтому исключенные из теста точки будут выделены {} цветом. Хотите "
                                     "продолжить?")
        pins_not_in_multiplexer = bool(self._main_window.measurement_plan.get_pins_without_multiplexer_outputs())
        if pins_not_in_multiplexer and not self._continue_plan_measurement(text.format(color)):
            return

        text = qApp.translate("mux", "В плане тестирования есть эталонные сигнатуры. При запуске измерений в режиме "
                                     "записи плана все имеющиеся сигнатуры будут перезаписаны. Вы точно хотите "
                                     "запустить измерение всех точек?")
        if self._main_window.is_measured_pin and self._main_window.work_mode is WorkMode.WRITE and \
                not self._continue_plan_measurement(text):
            return

        parent = self if QApplication.activeWindow() is self else self._main_window
        progress_window = ProgressWindow(parent, qApp.translate("mux", "Измерение всех точек"))
        progress_window.stopped.connect(self._stop_plan_measurement)
        self._mux_measurement_runner.measurement_done.connect(progress_window.change_progress)
        self._mux_measurement_runner.measurements_started.connect(progress_window.set_total_number_of_steps)
        self._mux_measurement_runner.measurements_finished.connect(progress_window.close_window)
        self._main_window.remove_callbacks_from_measurement_plan()
        self._mux_measurement_runner.start_measurements(self._main_window.measurement_plan,
                                                        self._main_window.work_mode,
                                                        self._main_window._msystem.get_settings())
        progress_window.exec()

    def update_info(self) -> None:
        """
        Method updates information about the measurement plan and the multiplexer.
        """

        self.measurement_plan_widget.update_info()
        self.multiplexer_pinout_widget.update_info()
