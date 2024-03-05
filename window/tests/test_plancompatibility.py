import os
import sys
import unittest
from typing import Tuple
from PyQt5.QtWidgets import QApplication
from epcore.elements import Element, MultiplexerOutput, Pin
from epcore.filemanager import load_board_from_ufiv
from epcore.ivmeasurer import IVMeasurerVirtual
from epcore.measurementmanager import MeasurementPlan, MeasurementSystem
from epcore.product import EyePointProduct
from window.plancompatibility import PlanCompatibility


class SimpleMainWindow:
    """
    Class for modeling simple main window.
    """

    def __init__(self, board_path: str) -> None:
        """
        :param board_path: path to file with board.
        """

        self._measurement_system: MeasurementSystem = MeasurementSystem([IVMeasurerVirtual()])
        self._measurement_plan: MeasurementPlan = self._create_measurement_plan(board_path)
        self._product: EyePointProduct = EyePointProduct()

    @property
    def measurement_plan(self) -> MeasurementPlan:
        """
        :return: measurement plan.
        """

        return self._measurement_plan

    @property
    def measurement_system(self) -> MeasurementSystem:
        """
        :return: measurement system.
        """

        return self._measurement_system

    @property
    def product(self) -> EyePointProduct:
        """
        :return: product.
        """

        return self._product

    def _create_measurement_plan(self, board_path: str) -> MeasurementPlan:
        """
        :param board_path: path to file with board.
        :return: a simple test plan loaded from a file.
        """

        board = load_board_from_ufiv(board_path)
        measurer = self.measurement_system.measurers[0]
        return MeasurementPlan(board, measurer)


class VerySimpleMainWindow:

    @staticmethod
    def get_default_pin_coordinates() -> Tuple[int, int]:
        return 0, 0


def prepare_data(board_name: str) -> Tuple[SimpleMainWindow, PlanCompatibility]:
    """
    :param board_name: file name with board.
    :return:
    """

    dir_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
    board_path = os.path.join(dir_name, board_name)
    window = SimpleMainWindow(board_path)
    checker = PlanCompatibility(window, window.measurement_system, window.product)
    return window, checker


class TestPlanCompatibility(unittest.TestCase):

    def setUp(self) -> None:
        self._app: QApplication = QApplication(sys.argv)

    def test_add_points(self) -> None:
        window = VerySimpleMainWindow()
        checker = PlanCompatibility(window, None, None)

        elements = []
        modules_number = 2
        channels_number = 10
        channels = {module: {channel: [] for channel in range(1, channels_number + 1)}
                    for module in range(1, modules_number + 1)}
        checker._add_points_from_mux_channels(elements, channels, [])
        self.assertEqual(len(elements), 1)
        channel = 1
        module = 1
        for element in elements:
            self.assertEqual(len(element.pins), channels_number * modules_number)
            for pin in element.pins:
                self.assertEqual(pin.multiplexer_output, MultiplexerOutput(channel, module))
                channel += 1
                if channel > channels_number:
                    channel = 1
                    module += 1

        pins_number = 3
        empty = [(0, i) for i in range(pins_number - 1, -1, -1)]
        pins = [Pin(x=i, y=i, comment=f"comment {i}") for i in range(pins_number)]
        elements = [Element(pins=pins)]
        checker._add_points_from_mux_channels(elements, channels, empty)
        self.assertEqual(len(elements), 1)
        channel = 1
        module = 1
        for element in elements:
            self.assertEqual(len(element.pins), channels_number * modules_number)
            for pin in element.pins:
                self.assertEqual(pin.multiplexer_output, MultiplexerOutput(channel, module))
                channel += 1
                if channel > channels_number:
                    channel = 1
                    module += 1

    def test_check_compatibility_with_product(self) -> None:
        window, checker = prepare_data("simple_board.json")
        self.assertTrue(checker._check_compatibility_with_product())

        window, checker = prepare_data("board_with_strange_settings.json")
        self.assertFalse(checker._check_compatibility_with_product())
