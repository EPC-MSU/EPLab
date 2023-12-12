import sys
import unittest
from PyQt5.QtWidgets import QApplication
from epcore.elements import Board, Element, IVCurve, Measurement, MeasurementSettings, Pin
from epcore.measurementmanager import MeasurementPlan
from window.measuredpinschecker import get_borders, MeasuredPinsChecker


class SimpleMainWindow:
    """
    Class for simulating main window.
    """

    def __init__(self) -> None:
        self._measurement_plan: MeasurementPlan = self._create_simple_measurement_plan()

    @property
    def measurement_plan(self):
        return self._measurement_plan

    @staticmethod
    def _create_measured_pin() -> Pin:
        settings = MeasurementSettings(sampling_rate=1,
                                       internal_resistance=1,
                                       max_voltage=1,
                                       probe_signal_frequency=1)
        curve = IVCurve([0, 1, 2, 3], [0, 1, 2, 3])
        measurement = Measurement(settings, curve, is_reference=True)
        return Pin(x=0, y=0, measurements=[measurement])

    def _create_simple_measurement_plan(self) -> MeasurementPlan:
        measured_pin_1 = self._create_measured_pin()
        measured_pin_2 = self._create_measured_pin()
        board = Board(elements=[Element(pins=[measured_pin_1, Pin(x=0, y=0), measured_pin_2])])
        return MeasurementPlan(board, None)


class TestMeasuredPinsChecker(unittest.TestCase):

    def setUp(self) -> None:
        self._app: QApplication = QApplication(sys.argv[1:])
        self._window: SimpleMainWindow = SimpleMainWindow()
        self._checker: MeasuredPinsChecker = MeasuredPinsChecker(self._window)
        self._checker.set_new_plan()

    def test_check_empty_current_pin(self) -> None:
        self.assertFalse(self._checker.check_empty_current_pin())

        self._window.measurement_plan.go_next_pin()
        self.assertTrue(self._checker.check_empty_current_pin())

        self._window.measurement_plan.go_next_pin()
        self.assertFalse(self._checker.check_empty_current_pin())

    def test_get_borders(self) -> None:
        self.assertEqual(get_borders([1, 2, 3, 5, 6, 27, 34, 35, 36, 37]), [(1, 3), (5, 6), (27, 27), (34, 37)])
