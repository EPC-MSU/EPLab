import os
from typing import Optional
from PyQt5.QtCore import pyqtSignal, QObject


class MeasurementPlanPath(QObject):

    name_changed: pyqtSignal = pyqtSignal(str)

    def __init__(self, main_window, path: Optional[str] = None) -> None:
        """
        :param main_window: main window of application.
        :param path: path to measurement plan.
        """

        super().__init__()
        self._main_window = main_window
        self._path: str = None
        self.path = path

    @property
    def path(self) -> str:
        """
        :return: path to measurement plan.
        """

        return self._path

    @path.setter
    def path(self, new_path: Optional[str]) -> None:
        """
        :param new_path: path to new measurement plan.
        """

        self._path = new_path
        self._send_new_name()

    def _send_new_name(self) -> None:
        if self._main_window.measurement_plan is None:
            measurement_plan_name = ""
        elif self._path is None:
            measurement_plan_name = "Untitled"
        else:
            measurement_plan_name = os.path.split(self._path)[1]
        self.name_changed.emit(measurement_plan_name)
