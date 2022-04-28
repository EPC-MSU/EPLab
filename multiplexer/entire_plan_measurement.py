"""
File to run entire plan measurement on multiplexer.
"""

from typing import List
from PyQt5.QtCore import pyqtSignal, QObject
from epcore.ivmeasurer import IVMeasurerBase
from epcore.measurementmanager import MeasurementPlan


class EntirePlanRunner(QObject):
    """
    Class to run entire plan measurement.
    """

    measurement_in_pin_finished: pyqtSignal = pyqtSignal()
    measurements_finished: pyqtSignal = pyqtSignal()

    def __init__(self, parent):
        """
        :param parent: main window.
        """

        super().__init__()
        self._is_running: bool = False
        self._measurement_plan: MeasurementPlan = None
        self._measurer: IVMeasurerBase = None
        self._parent = parent
        self._stop_process: bool = False
        self._uncorrect_pin_indexes: List[int] = None

    @property
    def is_running(self) -> bool:
        """
        :return: True if entire plan measurement is running.
        """

        return self._is_running

    def _take_measurement_in_pin(self):
        """
        Method takes measurement in current pin.
        """

        if self._measurement_plan.get_current_index() in self._uncorrect_pin_indexes:
            pin = self._measurement_plan.get_current_pin()
            settings = pin.get_reference_and_test_measurements()[2]
            self._measurer.set_settings(settings)
        self.measurement_in_pin_finished.emit()
        import time
        time.sleep(1)

    def go_to_next_pin(self):
        """
        Method performs measurement in next pin.
        """

        if self._stop_process:
            self._is_running = False
            self.measurements_finished.emit()
            return
        self._measurement_plan.go_next_pin()
        index = self._measurement_plan.get_current_index()
        print(index)
        if index == 0:
            self._is_running = False
            self.measurements_finished.emit()
            return
        self._take_measurement_in_pin()

    def start_measurements(self):
        """
        Method starts entire plan measurement.
        """

        self._is_running = True
        self._measurement_plan = self._parent.measurement_plan
        self._measurer = self._measurement_plan.measurer
        self._stop_process = False
        self._uncorrect_pin_indexes = self._measurement_plan.get_pins_without_multiplexer_outputs()
        self._measurement_plan.go_pin(0)
        self._take_measurement_in_pin()

    def stop_measurements(self):
        """
        Method stops entire plan measurements.
        """

        self._stop_process = True
