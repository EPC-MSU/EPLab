import os
import sys
import unittest
from typing import Tuple
from PyQt5.QtWidgets import QApplication
from window.measuredpinschecker import get_borders, MeasuredPinsChecker
from .simplemainwindow import SimpleMainWindow


def prepare_data(board_name: str) -> Tuple[SimpleMainWindow, MeasuredPinsChecker]:
    """
    :param board_name: file name with board.
    :return: an object that models a simple application window, and a checker for measurements in board pins.
    """

    dir_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
    window = SimpleMainWindow(os.path.join(dir_name, board_name))
    checker = MeasuredPinsChecker(window)
    checker.set_new_plan()
    return window, checker


class TestMeasuredPinsChecker(unittest.TestCase):

    def setUp(self) -> None:
        self._app: QApplication = QApplication(sys.argv)

    def test_check_empty_current_pin(self) -> None:
        window, checker = prepare_data("simple_board.json")
        self.assertFalse(checker.check_empty_current_pin())

        window.measurement_plan.go_next_pin()
        self.assertTrue(checker.check_empty_current_pin())

        window.measurement_plan.go_next_pin()
        self.assertFalse(checker.check_empty_current_pin())

    def test_check_measurement_plan_for_empty_pins(self) -> None:
        window, checker = prepare_data("simple_board.json")
        self.assertTrue(checker.check_measurement_plan_for_empty_pins())

    def test_get_borders(self) -> None:
        self.assertEqual(get_borders([1, 2, 3, 5, 6, 27, 34, 35, 36, 37]), [(1, 3), (5, 6), (27, 27), (34, 37)])

    def test_is_measured_pin(self) -> None:
        _, checker = prepare_data("simple_board.json")
        self.assertTrue(checker.is_measured_pin)
