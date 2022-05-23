"""
Tests for measurement plan runner.
"""

import os
import sys
import unittest
from PyQt5.QtWidgets import QApplication
from multiplexer.measurement_plan_runner import MeasurementPlanRunner
from multiplexer.measurement_plan_widget import MeasurementPlanWidget
from .utils import create_dummy_main_window


class TestMeasurementPlanRunner(unittest.TestCase):

    def test_amount_of_pins_for_default_plan(self):
        """
        Test checks number of pins to test in default plan.
        """

        app = QApplication(sys.argv)
        dummy_main_window = create_dummy_main_window()
        measurement_plan_widget = MeasurementPlanWidget(dummy_main_window)
        measurement_plan_widget.update_info()
        runner = MeasurementPlanRunner(dummy_main_window, measurement_plan_widget)
        runner.start_or_stop_measurements(True)
        self.assertEqual(runner._amount_of_pins, 1)
        app.exit(0)

    def test_amount_of_pins_for_not_default_plan(self):
        """
        Test checks number of pins to test in not default plan.
        """

        app = QApplication(sys.argv)
        dummy_main_window = create_dummy_main_window()
        board_path = os.path.join(os.path.dirname(__file__), "test_data", "test_board.json")
        dummy_main_window.update_measurement_plan(board_path)
        measurement_plan_widget = MeasurementPlanWidget(dummy_main_window)
        measurement_plan_widget.update_info()
        runner = MeasurementPlanRunner(dummy_main_window, measurement_plan_widget)
        runner.start_or_stop_measurements(True)
        self.assertEqual(runner._amount_of_pins, 2)
        app.exit(0)
