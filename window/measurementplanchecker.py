from typing import Optional, Set
from epcore.elements import Pin
from epcore.measurementmanager import MeasurementPlan
from PyQt5.QtCore import pyqtSignal, QObject


class MeasurementPlanChecker(QObject):

    measured_pin_in_plan_signal: pyqtSignal = pyqtSignal(bool)

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self._main_window = main_window
        self._measured_pins: Set[int] = set()

    @property
    def measurement_plan(self) -> Optional[MeasurementPlan]:
        return self._main_window.measurement_plan

    def _check_measured_pin(self, pin_index: int) -> None:
        if 0 <= pin_index < len(self.measurement_plan._all_pins):
            pin = self.measurement_plan._all_pins[pin_index]
            if self._check_pin(pin):
                self._measured_pins.add(pin_index)
            else:
                self._measured_pins.discard(pin_index)

    @staticmethod
    def _check_pin(pin: Pin) -> bool:
        for measurement in pin.measurements:
            if measurement.is_reference:
                return True
        return False

    def _handle_measurement_plan_change(self, pin_index: int) -> None:
        if self.measurement_plan:
            self._check_measured_pin(pin_index)
        measured = len(self._measured_pins) != 0
        self.measured_pin_in_plan_signal.emit(measured)

    def _set_new_plan(self) -> None:
        self._measured_pins.clear()
        if self.measurement_plan:
            for index, pin in self.measurement_plan.all_pins_iterator():
                if self._check_pin(pin):
                    self._measured_pins.add(index)

    def set_new_plan(self) -> None:
        self._set_new_plan()
        self._handle_measurement_plan_change(0)
        if self.measurement_plan:
            self.measurement_plan.add_callback_func_for_pin_changes(self._handle_measurement_plan_change)