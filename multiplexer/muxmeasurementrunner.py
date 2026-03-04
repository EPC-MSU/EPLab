"""
File with class to run measurements according measurement plan.
"""

import logging
from copy import deepcopy
from typing import Optional
from PyQt5.QtCore import pyqtSignal, QThread
from epcore.elements import Measurement, MeasurementSettings
from epcore.measurementmanager import MeasurementPlan
from window.common import DeviceErrorsHandler, WorkMode


logger = logging.getLogger("eplab")


class MuxMeasurementRunner(QThread):
    """
    Class for performing measurements according to a measurement plan using a multiplexer.
    """

    device_errors_occurred: pyqtSignal = pyqtSignal()
    measurement_done: pyqtSignal = pyqtSignal()
    measurements_finished: pyqtSignal = pyqtSignal()
    measurements_started: pyqtSignal = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self._default_measurement_settings: Optional[MeasurementSettings] = None
        self._device_errors_handler: DeviceErrorsHandler = DeviceErrorsHandler()
        self._is_running: bool = False
        self._measurement_plan: Optional[MeasurementPlan] = None
        self._must_be_running: bool = False
        self._work_mode: Optional[WorkMode] = None

    @property
    def is_running(self) -> bool:
        """
        :return: True if measurements according plan is running.
        """

        return self._is_running

    def _do_measurements(self) -> None:
        logger.debug("Measurements launched according to plan using a multiplexer")

        for i, pin in self._measurement_plan.all_pins_iterator():
            if not self._must_be_running:
                logger.debug("The execution of measurements according to plan using a multiplexer stopped at "
                             "pin %d of %d", i, self._measurement_plan.pins_number)
                break

            logger.debug("Measurement is performed at pin %d", i)
            self._measurement_plan.go_pin(i)
            reference_measurement = pin.get_reference_measurement()
            if reference_measurement is not None:
                measurement_settings = reference_measurement.settings
            else:
                measurement_settings = None

            if self._work_mode is WorkMode.WRITE:
                if measurement_settings is None:
                    measurement_settings = self._default_measurement_settings
            elif self._work_mode is WorkMode.TEST:
                if measurement_settings is None:
                    self.measurement_done.emit()
                    continue
            else:
                self.measurement_done.emit()
                continue

            self._measurement_plan.measurer.set_settings(measurement_settings)
            self._measurement_plan.measurer.trigger_measurement()
            while not self._measurement_plan.measurer.measurement_is_ready():
                QThread.msleep(1)

            curve = self._measurement_plan.measurer.get_last_iv_curve()
            measurement = Measurement(settings=deepcopy(measurement_settings), ivc=curve, is_reference=True)
            if self._work_mode is WorkMode.WRITE:
                pin.set_reference_measurement(measurement, True)
            else:
                measurement.is_reference = False
                pin.set_test_measurement(measurement)

            self.measurement_done.emit()
            QThread.msleep(10)

        if self._must_be_running:
            logger.debug("Measurements according to plan using a multiplexer are completed")

    def run(self) -> None:
        while True:
            if self._must_be_running:
                self._is_running = True
                self.measurements_started.emit(self._measurement_plan.pins_number)

                with self._device_errors_handler:
                    self._do_measurements()

                if not self._device_errors_handler.all_ok:
                    self.device_errors_occurred.emit()

                self._is_running = False
                self._must_be_running = False
                self.measurements_finished.emit()

            QThread.msleep(300)

    def start_measurements(self, measurement_plan: MeasurementPlan, work_mode: WorkMode,
                           measurement_settings: MeasurementSettings) -> None:
        """
        :param measurement_plan: measurement plan;
        :param work_mode: application operating mode;
        :param measurement_settings: measurement settings to use by default.
        """

        self._device_errors_handler.reset_error()
        self._default_measurement_settings = measurement_settings
        self._measurement_plan = measurement_plan
        self._work_mode = work_mode
        self._must_be_running = True

    def stop_measurements(self) -> None:
        self._must_be_running = False
