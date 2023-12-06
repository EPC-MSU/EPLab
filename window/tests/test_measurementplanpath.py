import os
import sys
import unittest
from PyQt5.QtWidgets import QApplication
from window.measurementplanpath import MeasurementPlanPath


class DummyMainWindow:

    def __init__(self) -> None:
        self.measurement_plan = True
        self.measurement_plan_name: str = None
        self.measurement_plan_path: MeasurementPlanPath = MeasurementPlanPath(self)
        self.measurement_plan_path.name_changed.connect(self.change_title)

    def change_title(self, measurement_plan_name: str) -> None:
        self.measurement_plan_name = measurement_plan_name


class TestMeasurementPlanPath(unittest.TestCase):

    def setUp(self) -> None:
        self._app: QApplication = QApplication(sys.argv[1:])
        self._dummy_window: DummyMainWindow = DummyMainWindow()

    def test_empty_name(self) -> None:
        """
        It checks that when there is no measurement plan, an empty name is obtained.
        """

        self._dummy_window.measurement_plan = None
        self._dummy_window.measurement_plan_path.path = None
        self.assertEqual(self._dummy_window.measurement_plan_name, "")

    def test_set_path(self) -> None:
        """
        It is tested that when specifying a path, the correct plan name is obtained.
        """

        self._dummy_window.measurement_plan = True
        self._dummy_window.measurement_plan_path.path = os.path.join("path", "to", "dir", "board_name.uzf")
        self.assertEqual(self._dummy_window.measurement_plan_name, "board_name.uzf")

    def test_untitled(self) -> None:
        """
        It is tested that when there is a measurement plan, but the path is not specified, then the name of the plan is
        Untitled.
        """

        self._dummy_window.measurement_plan = True
        self._dummy_window.measurement_plan_path.path = None
        self.assertEqual(self._dummy_window.measurement_plan_name, "Untitled")
