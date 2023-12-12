from typing import List, Optional, Set, Tuple
from PyQt5.QtCore import pyqtSignal, QCoreApplication as qApp, QObject
from epcore.elements import Pin
from epcore.measurementmanager import MeasurementPlan
from window import utils as ut


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
        self._empty_pins: Set[int] = set()
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
            self._empty_pins.discard(pin_index)
            self._measured_pins.add(pin_index)
        else:
            self._empty_pins.add(pin_index)
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

        self._empty_pins.clear()
        self._measured_pins.clear()
        if self.measurement_plan:
            for index, pin in self.measurement_plan.all_pins_iterator():
                if self._check_pin(pin):
                    self._measured_pins.add(index)
                else:
                    self._empty_pins.add(index)

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

    def check_measurement_plan_for_empty_pins(self) -> bool:
        """
        :return: True if there are pins without measurements in measurement plan.
        """

        if len(self._empty_pins) > 0:
            empty = True
            empty_pins = list(self._empty_pins)
            if len(empty_pins) > 1:
                borders = get_borders(sorted(empty_pins))
                borders_text = get_borders_as_text(borders)
                text = qApp.translate("t", "Точки {} не содержат сохраненных измерений. Для сохранения плана "
                                           "тестирования все точки должны содержать измерения.").format(borders_text)
            else:
                text = qApp.translate("t", "Точка {} не содержит сохраненных измерений. Для сохранения плана "
                                           "тестирования все точки должны содержать измерения."
                                      ).format(empty_pins[0] + 1)
            ut.show_message(qApp.translate("t", "Ошибка"), text)
        else:
            empty = False
        return empty

    def set_new_plan(self) -> None:
        """
        Method must be executed when a new measurement plan is initialized.
        """

        self._set_new_plan()
        self._handle_measurement_plan_change(0)
        if self.measurement_plan:
            self.measurement_plan.add_callback_func_for_pin_changes(self._handle_measurement_plan_change)


def get_borders(array: List[int]) -> List[Tuple[int, int]]:
    """
    For example, a function receives a list:
    [1, 2, 3, 5, 6, 27, 39, 40, 41]
    Then the function will return the boundaries:
    [(1, 3), (5, 6), (27, 27), (39, 41)]
    :param array: sorted list of numbers.
    :return: borders.
    """

    def get_segment(array_: List[int], shift: int) -> Tuple[int, int]:
        i = 0
        while i + 1 < len(array_) and array_[i] + 1 == array_[i + 1]:
            i += 1
        return shift, i + shift

    borders = []
    i_left = 0
    while i_left < len(array):
        i_left, i_right = get_segment(array[i_left:], i_left)
        borders.append((array[i_left], array[i_right]))
        i_left = i_right + 1
    return borders


def get_borders_as_text(borders: List[Tuple[int, int]]) -> str:
    borders_str = []
    for left, right in borders:
        if left != right:
            borders_str.append(f"{left + 1} - {right + 1}")
        else:
            borders_str.append(f"{left + 1}")
    return ", ".join(borders_str)
