"""
File with class to run measurements according measurement plan.
"""

import logging
from typing import List, Optional
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QObject, QTimer
from .measurementplanwidget import MeasurementPlanWidget


logger = logging.getLogger("eplab")


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
        self._go_to_next_pin_required: bool = False
        self._is_running: bool = False
        self._main_window = main_window
        self._measurement_number_in_pin: int = 0
        self._measurement_plan_widget: MeasurementPlanWidget = measurement_plan_widget
        self._measurement_save_required: bool = False
        self.measurement_is_valid: bool = False

        self._create_timers()

    @property
    def is_running(self) -> bool:
        """
        :return: True if measurements according plan is running.
        """

        return self._is_running

    def _create_timers(self) -> None:
        self._timer_to_go_to_pin: QTimer = QTimer()
        self._timer_to_go_to_pin.timeout.connect(self._go_to_pin)
        self._timer_to_go_to_pin.setInterval(MeasurementPlanRunner.PERIOD)
        self._timer_to_go_to_pin.setSingleShot(True)

        self._timer_to_save_measurements: QTimer = QTimer()
        self._timer_to_save_measurements.timeout.connect(self._save_measurements)
        self._timer_to_save_measurements.setInterval(MeasurementPlanRunner.PERIOD)
        self._timer_to_save_measurements.setSingleShot(True)

    @pyqtSlot()
    def _go_to_pin(self) -> None:
        """
        Slot moves to the next pin in the measurement plan. Slot is executed on a timer so that the window does not
        freeze too much.
        """

        if isinstance(self._amount_of_pins, int) and isinstance(self._current_pin_index, int) and \
                self._current_pin_index < self._amount_of_pins:
            self._main_window.go_to_selected_pin(self._current_pin_index)
            self._go_to_next_pin_required = False
            logger.debug("The multiplexer has moved to pin %d", self._current_pin_index)
        else:
            self._stop_measurements()

    def _mark_completed_step(self) -> None:
        """
        Method is executed to mark that a step has been completed when measuring a test plan.
        """

        self.measurement_done.emit()
        self._go_to_next_pin_required = True
        self._measurement_number_in_pin = 0
        self._measurement_save_required = False
        self.measurement_is_valid = False
        self._current_pin_index += 1
        self._timer_to_go_to_pin.start()

    @pyqtSlot()
    def _save_measurements(self) -> None:
        """
        Slot is used to save the measurement in the current pin of the measurement plan. Slot is executed on a timer so
        that the window does not freeze too much.
        """

        self._main_window.save_pin()
        logger.debug("Measurement saved in pin %d", self._current_pin_index)
        self._mark_completed_step()

    def _start_measurements(self) -> None:
        """
        Method starts measurements according plan.
        """

        self._amount_of_pins = self._measurement_plan_widget.get_amount_of_pins()
        self._current_pin_index = 0
        self._go_to_next_pin_required = True
        self._is_running = True
        self._measurement_save_required = False
        self.measurement_is_valid = False
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

    def check_pins_without_multiplexer_outputs(self) -> bool:
        """
        Method gets list of indices of pins whose multiplexer output is None or output cannot be set using current
        multiplexer configuration.
        :return: True if there are such pins.
        """

        self._bad_pin_indexes = self._main_window.measurement_plan.get_pins_without_multiplexer_outputs()
        return bool(self._bad_pin_indexes)

    def determine_if_measurement_is_valid(self) -> None:
        """
        Method determines whether the measurement in the pin is valid. The measurement is valid if the multiplexer
        is moved to the desired pin and at least two measurements are made in this pin.
        """

        if not self.is_running or self._go_to_next_pin_required:
            return

        self._measurement_number_in_pin += 1
        self.measurement_is_valid = self._measurement_number_in_pin >= 2

    def determine_whether_to_save_measurement(self) -> None:
        """
        Method determines whether the measurement should be saved.
        """

        if not self.is_running:
            return

        if self._go_to_next_pin_required:
            self._measurement_save_required = False
            return

        self._measurement_save_required = True

    def save_measurements(self) -> None:
        """
        Method saves measurements in current pin if required.
        """

        if self.is_running and (self._measurement_save_required or self._current_pin_index in self._bad_pin_indexes):
            if self._current_pin_index not in self._bad_pin_indexes and self._main_window.measurement_can_be_saved:
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
