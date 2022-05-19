"""
File with class to run measurements according measurement plan.
"""

from typing import List
from PyQt5.QtCore import pyqtSignal, QObject
from multiplexer.measurement_plan_widget import MeasurementPlanWidget


class MeasurementPlanRunner(QObject):
    """
    Class to run measurements according plan.
    """

    measurements_finished: pyqtSignal = pyqtSignal()
    measurements_started: pyqtSignal = pyqtSignal(int)
    measurement_done: pyqtSignal = pyqtSignal()

    def __init__(self, parent, measurement_plan_widget: MeasurementPlanWidget):
        """
        :param parent: main window of application;
        :param measurement_plan_widget: measurement plan widget.
        """

        super().__init__()
        self._amount_of_pins: int = None
        self._bad_pin_indexes: List[int] = []
        self._current_pin_index: int = None
        self._is_running: bool = False
        self._measurement_plan_widget: MeasurementPlanWidget = measurement_plan_widget
        self._measurement_saved: bool = False
        self._need_to_save_measurement: bool = False
        self._parent = parent

    def _start_measurements(self):
        """
        Method starts measurements according plan.
        """

        self._amount_of_pins = self._measurement_plan_widget.get_amount_of_pins()
        self._current_pin_index = 0
        self._is_running = True
        self.measurements_started.emit(self._amount_of_pins)
        self.go_to_pin()

    def _stop_measurements(self):
        """
        Method stops measurements according plan.
        """

        self._amount_of_pins = None
        self._current_pin_index = None
        self._is_running = False
        self.measurements_finished.emit()

    def check_pin(self):
        """
        Method checks if all necessary parameters for current pin are set
        from the measurement plan.
        """

        if not self._measurement_saved:
            self._need_to_save_measurement = True

    def get_pins_without_multiplexer_outputs(self) -> bool:
        """
        Method gets list of indexes of pins whose multiplexer output is None
        or output cannot be set using current multiplexer configuration.
        :return: True if there are such pins.
        """

        self._bad_pin_indexes = self._parent.measurement_plan.get_pins_without_multiplexer_outputs()
        return bool(self._bad_pin_indexes)

    def go_to_pin(self):
        """
        Method moves to next pin in measurement plan.
        """

        if isinstance(self._amount_of_pins, int) and isinstance(self._current_pin_index, int) and\
                self._current_pin_index < self._amount_of_pins:
            self._parent.go_to_selected_pin(self._current_pin_index)
            self._measurement_saved = False
        else:
            self._stop_measurements()

    @property
    def is_running(self) -> bool:
        """
        :return: True if measurements according plan is running.
        """

        return self._is_running

    def save_pin(self):
        """
        Method saves measurement in current pin if required.
        """

        if self._is_running and (self._need_to_save_measurement or self._current_pin_index in self._bad_pin_indexes):
            if self._current_pin_index not in self._bad_pin_indexes:
                self._parent.save_pin()
            self.measurement_done.emit()
            self._measurement_saved = True
            self._need_to_save_measurement = False
            self._current_pin_index += 1
            self.go_to_pin()

    def start_or_stop_measurements(self, start: bool):
        """
        Method starts or stops measurements according measurement plan.
        """

        if start:
            self._start_measurements()
        else:
            self._stop_measurements()
