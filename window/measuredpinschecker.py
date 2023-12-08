from typing import Optional, Set
from epcore.elements import Pin
from epcore.measurementmanager import MeasurementPlan
from PyQt5.QtCore import pyqtSignal, QObject


class MeasuredPinsChecker(QObject):
    """
    Class for checking a measurement plan for the presence of pins with measured reference IV-curves.
    """

    measured_pin_in_plan_signal: pyqtSignal = pyqtSignal(bool)

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self._main_window = main_window
        self._measured_pins: Set[int] = set()

    @property
    def is_measured_pin(self) -> bool:
        """
        :return: True, if the measurement plan contains a pin with a measured reference IV-curve.
        """

        return len(self._measured_pins) != 0

    @property
    def measurement_plan(self) -> Optional[MeasurementPlan]:
        """
        :return: measurement plan.
        """

        return self._main_window.measurement_plan

    @staticmethod
    def _check_pin(pin: Pin) -> bool:
        """
        Method checks whether there is a reference IV-curve in a given pin.
        :param pin: pin in which to check the presence of a measured reference IV-curve.
        :return: True, if the reference IV-curve is measured in the pin.
        """

        for measurement in pin.measurements:
            if measurement.is_reference:
                return True
        return False

    def _check_pin_with_index(self, pin_index: int) -> None:
        """
        Method checks whether there is a reference IV-curve in a pin with a given index.
        :param pin_index: pin index in which to check the presence of a measured reference IV-curve.
        """

        pin = self.measurement_plan.get_pin_with_index(pin_index)
        if pin is not None and self._check_pin(pin):
            self._measured_pins.add(pin_index)
        else:
            self._measured_pins.discard(pin_index)

    def _handle_measurement_plan_change(self, pin_index: int) -> None:
        """
        :param pin_index: pin index that has changed.
        """

        if self.measurement_plan:
            self._check_pin_with_index(pin_index)
        measured = len(self._measured_pins) != 0
        self.measured_pin_in_plan_signal.emit(measured)

    def _set_new_plan(self) -> None:
        """
        Method checks a new measurement plan for the presence of pins with measured reference IV-curves.
        """

        self._measured_pins.clear()
        if self.measurement_plan:
            for index, pin in self.measurement_plan.all_pins_iterator():
                if self._check_pin(pin):
                    self._measured_pins.add(index)

    def check_empty_current_pin(self) -> bool:
        """
        Method checks that the current pin does not have a measured reference IV-curve.
        :return: True if there is no measured reference IV-curve in the current pin.
        """

        pin = self.measurement_plan.get_current_pin()
        for measurement in pin.measurements:
            if measurement.is_reference:
                return False
        return True

    def get_next_measured_pin(self, left: bool = False) -> int:
        """
        :param left: if True, then in search of the next pin with the measured reference IV-curve you need to move
        through the list to the left (towards decreasing indices), otherwise - to the right (towards increasing
        indices).
        :return: the index of the next pin in which the reference IV-curve is measured.
        """

        def get_next_pin_index(current_index: int) -> int:
            if left:
                index = current_index - 1
                if index < 0:
                    index = number_of_pins - 1
            else:
                index = current_index + 1
                if index >= number_of_pins:
                    index = 0
            return index

        number_of_pins = len(self.measurement_plan._all_pins)
        start_index = self.measurement_plan.get_current_index()
        pin_index = start_index
        while True:
            pin_index = get_next_pin_index(pin_index)
            pin = self.measurement_plan.get_pin_with_index(pin_index)
            if (pin and self._check_pin(pin)) or pin_index == start_index:
                return pin_index

    def set_new_plan(self) -> None:
        """
        Method must be executed when a new measurement plan is initialized.
        """

        self._set_new_plan()
        self._handle_measurement_plan_change(0)
        if self.measurement_plan:
            self.measurement_plan.add_callback_func_for_pin_changes(self._handle_measurement_plan_change)
