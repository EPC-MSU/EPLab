"""
File with class to run measurements according measurement plan.
"""

from typing import List, Optional
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QTimer
from .measurementplanwidget import MeasurementPlanWidget


class MeasurementPlanRunner(QObject):
    """
    Class for carrying out measurements according to plan.
    """

    PERIOD: int = 10
    go_to_pin_signal: pyqtSignal = pyqtSignal(int, bool)
    measurement_done: pyqtSignal = pyqtSignal()
    measurements_finished: pyqtSignal = pyqtSignal()
    measurements_started: pyqtSignal = pyqtSignal(int)

    def __init__(self, main_window, measurement_plan_widget: MeasurementPlanWidget) -> None:
        """
        :param main_window: main window of application;
        :param measurement_plan_widget: measurement plan widget.
        """

        super().__init__()
        self._amount_of_pins: Optional[int] = None
        self._bad_pin_indexes: List[int] = []
        self._current_pin_index: Optional[int] = None
        self._is_running: bool = False
        self._main_window = main_window
        self._measurement_plan_widget: MeasurementPlanWidget = measurement_plan_widget
        self._need_to_go_to_pin: bool = False
        self._need_to_save_measurement: bool = False

        self._timer_to_go_to_pin: QTimer = QTimer()
        self._timer_to_go_to_pin.timeout.connect(self._go_to_pin)
        self._timer_to_go_to_pin.setInterval(MeasurementPlanRunner.PERIOD)
        self._timer_to_go_to_pin.setSingleShot(True)

        self._timer_to_save_measurements: QTimer = QTimer()
        self._timer_to_save_measurements.timeout.connect(self._save_measurements)
        self._timer_to_save_measurements.setInterval(MeasurementPlanRunner.PERIOD)
        self._timer_to_save_measurements.setSingleShot(True)

    @property
    def is_running(self) -> bool:
        """
        :return: True if measurements according plan is running.
        """

        return self._is_running

    @pyqtSlot()
    def _go_to_pin(self) -> None:
        """
        Slot moves to the next pin in the measurement plan. Slot is executed on a timer so that the window does not
        freeze too much.
        """

        if isinstance(self._amount_of_pins, int) and isinstance(self._current_pin_index, int) and \
                self._current_pin_index < self._amount_of_pins:
            self._main_window.go_to_selected_pin(self._current_pin_index)
            self._need_to_go_to_pin = False
        else:
            self._stop_measurements()

    def _mark_completed_step(self) -> None:
        """
        Method is executed to mark that a step has been completed when measuring a test plan.
        """

        self.measurement_done.emit()
        self._need_to_go_to_pin = True
        self._need_to_save_measurement = False
        self._current_pin_index += 1
        self._timer_to_go_to_pin.start()

    @pyqtSlot()
    def _save_measurements(self) -> None:
        """
        Slot is used to save the measurement in the current pin of the measurement plan. Slot is executed on a timer so
        that the window does not freeze too much.
        """

        self._main_window.save_pin()
        self._mark_completed_step()

    def _start_measurements(self) -> None:
        """
        Method starts measurements according plan.
        """

        self._amount_of_pins = self._measurement_plan_widget.get_amount_of_pins()
        self._current_pin_index = 0
        self._is_running = True
        self.measurements_started.emit(self._amount_of_pins)
        self._go_to_pin()

    def _stop_measurements(self) -> None:
        """
        Method stops measurements according plan.
        """

        self._amount_of_pins = None
        self._current_pin_index = None
        self._is_running = False
        self._timer_to_go_to_pin.stop()
        self._timer_to_save_measurements.stop()
        self.measurements_finished.emit()

    def check_pin(self) -> None:
        """
        Method checks whether the measurement plan is in the desired pin.
        """

        if not self._need_to_go_to_pin:
            self._need_to_save_measurement = True

    def check_pins_without_multiplexer_outputs(self) -> bool:
        """
        Method gets list of indices of pins whose multiplexer output is None or output cannot be set using current
        multiplexer configuration.
        :return: True if there are such pins.
        """

        self._bad_pin_indexes = self._main_window.measurement_plan.get_pins_without_multiplexer_outputs()
        return bool(self._bad_pin_indexes)

    def save_measurements(self) -> None:
        """
        Method saves measurements in current pin if required.
        """

        if self.is_running and (self._need_to_save_measurement or self._current_pin_index in self._bad_pin_indexes):
            if self._current_pin_index not in self._bad_pin_indexes and self._main_window.can_be_measured:
                self._timer_to_save_measurements.start()
            else:
                self._mark_completed_step()

    def start_or_stop_measurements(self, start: bool) -> None:
        """
        Method starts or stops measurements according measurement plan.
        :param start: if True then measurements will be started.
        """

        if start:
            self._start_measurements()
        else:
            self._stop_measurements()
