"""
Tests for widget that displays measurement plan table.
"""

import os
import sys
import unittest
from PyQt5.QtWidgets import QApplication
from multiplexer.measurement_plan_widget import MeasurementPlanWidget
from .utils import create_dummy_main_window


class TestMeasurementPlanWidget(unittest.TestCase):

    def test_table_creation(self):
        """
        Test checks creation of empty table for measurement plan.
        """

        app = QApplication(sys.argv)
        dummy_main_window = create_dummy_main_window()
        measurement_plan_widget = MeasurementPlanWidget(dummy_main_window)
        self.assertEqual(measurement_plan_widget.table_widget_info.rowCount(), 0)
        app.exit(0)

    def test_table_update(self):
        """
        Test checks updating of table for measurement plan.
        """

        app = QApplication(sys.argv)
        dummy_main_window = create_dummy_main_window()
        board_path = os.path.join(os.path.dirname(__file__), "test_data", "test_board.json")
        dummy_main_window.update_measurement_plan(board_path)
        measurement_plan_widget = MeasurementPlanWidget(dummy_main_window)
        measurement_plan_widget.update_info()
        self.assertEqual(measurement_plan_widget.table_widget_info.rowCount(), 2)
        app.exit(0)

    def test_table_content(self):
        """
        Test checks content of table for measurement plan.
        """

        app = QApplication(sys.argv)
        dummy_main_window = create_dummy_main_window()
        board_path = os.path.join(os.path.dirname(__file__), "test_data", "test_board.json")
        dummy_main_window.update_measurement_plan(board_path)
        measurement_plan_widget = MeasurementPlanWidget(dummy_main_window)
        measurement_plan_widget.update_info()
        content = [["0", "", "", "100 Hz", "5.0 V", "Middle", ""],
                   ["1", "2", "45", "100 Hz", "5.0 V", "Middle", ""]]
        for row in range(2):
            for column in range(5):
                if column in (1, 2, 6):
                    widget_or_item = measurement_plan_widget.table_widget_info.cellWidget(row, column)
                else:
                    widget_or_item = measurement_plan_widget.table_widget_info.item(row, column)
                self.assertEqual(widget_or_item.text(), content[row][column])
        app.exit(0)
