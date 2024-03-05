import os
import sys
import unittest
from typing import Optional, Tuple
from PyQt5.QtWidgets import QApplication
from epcore.analogmultiplexer import AnalogMultiplexerVirtual
from epcore.filemanager import load_board_from_ufiv
from epcore.ivmeasurer import IVMeasurerVirtual
from epcore.measurementmanager import MeasurementPlan, MeasurementSystem
from epcore.product import EyePointProduct
from window.plancompatibility import PlanCompatibility


class SimpleMainWindow:
    """
    Class for modeling simple main window.
    """

    def __init__(self, mux_required: bool = False) -> None:
        """
        :param mux_required: if True, then it is needed to create a multiplexer.
        """

        multiplexers = [AnalogMultiplexerVirtual()] if mux_required else []
        self._measurement_system: MeasurementSystem = MeasurementSystem([IVMeasurerVirtual()], multiplexers)
        self._product: EyePointProduct = EyePointProduct()

    @property
    def measurement_system(self) -> MeasurementSystem:
        """
        :return: measurement system.
        """

        return self._measurement_system

    @property
    def measurer(self) -> Optional[IVMeasurerVirtual]:
        """
        :return: IV-measurer.
        """

        if self.measurement_system and self.measurement_system.measurers:
            return self.measurement_system.measurers[0]
        return None

    @property
    def multiplexer(self) -> Optional[AnalogMultiplexerVirtual]:
        """
        :return: multiplexer.
        """

        if self.measurement_system and self.measurement_system.multiplexers:
            return self.measurement_system.multiplexers[0]
        return None

    @property
    def product(self) -> EyePointProduct:
        """
        :return: product.
        """

        return self._product


def create_measurement_plan_from_file(board_name: str, measurer: IVMeasurerVirtual,
                                      multiplexer: Optional[AnalogMultiplexerVirtual] = None) -> MeasurementPlan:
    """
    :param board_name: file name with board;
    :param measurer: IV-measurer;
    :param multiplexer: multiplexer.
    :return: a measurement plan loaded from a file.
    """

    dir_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
    board_path = os.path.join(dir_name, board_name)
    board = load_board_from_ufiv(board_path)
    return MeasurementPlan(board, measurer, multiplexer)


def create_window_and_checker(mux_required: bool = False) -> Tuple[SimpleMainWindow, PlanCompatibility]:
    """
    :param mux_required:
    :return: simple main window and plan compatibility checker.
    """

    window = SimpleMainWindow(mux_required)
    checker = PlanCompatibility(window, window.measurement_system, window.product)
    return window, checker


class TestPlanCompatibility(unittest.TestCase):

    def setUp(self) -> None:
        self._app: QApplication = QApplication(sys.argv)

    def test_check_compatibility_with_mux(self) -> None:
        window, checker = create_window_and_checker(True)
        plan = create_measurement_plan_from_file("board_mux.json", window.measurer, window.multiplexer)
        self.assertTrue(checker._check_compatibility_with_mux(plan))

        plan = create_measurement_plan_from_file("simple_board.json", window.measurer, window.multiplexer)
        self.assertFalse(checker._check_compatibility_with_mux(plan))

    def test_check_compatibility_with_product(self) -> None:
        window, checker = create_window_and_checker(True)
        plan = create_measurement_plan_from_file("simple_board.json", window.measurer, window.multiplexer)
        self.assertTrue(checker._check_compatibility_with_product(plan))

        plan = create_measurement_plan_from_file("board_with_strange_settings.json", window.measurer,
                                                 window.multiplexer)
        self.assertFalse(checker._check_compatibility_with_product(plan))
