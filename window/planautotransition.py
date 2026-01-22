import logging
import math
import os
import time
from enum import auto, Enum
from typing import Callable, Dict, Optional
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QObject, QTimer
from epcore.elements import IVCurve, MeasurementSettings
from epcore.product import EyePointProduct
from connection_window.productname import ProductName
from settings.autosettings import AutoSettings
from .breaksignaturessaver import create_filename, iterate_settings, load_signature
from .common import WorkMode
from .scorewrapper import check_difference_not_greater_tolerance, ScoreWrapper


logger = logging.getLogger("eplab")


class PlanAutoTransition(QObject):
    """
    Class for performing automatic transition in testing mode according to plan.
    """

    class Process(Enum):
        """
        Class listing auto-transition stages.
        """

        GO_TO_NEXT = auto()
        MEASURE = auto()
        RAISE_PROBES = auto()
        SAVE = auto()
        WAIT = auto()

    BREAK_NUMBER: int = 1
    BREAK_TOLERANCE: float = 0.15
    FREQUENCY_TOLERANCE: float = 1e-6
    TIME_TO_SHOW_S: float = 0.3
    TIMEOUT_MS: int = 10
    go_to_next_signal: pyqtSignal = pyqtSignal(bool, bool)
    save_pin_signal: pyqtSignal = pyqtSignal()

    def __init__(self, product: EyePointProduct, auto_settings: AutoSettings, score_wrapper: ScoreWrapper,
                 calculate_score: Callable[[IVCurve, IVCurve, MeasurementSettings], float], dir_path: str,
                 frequency: Optional[str] = None, sensitive: Optional[str] = None) -> None:
        """
        :param product: product;
        :param auto_settings: object with basic application settings;
        :param score_wrapper: an object that determines whether a signature difference is valid or not;
        :param calculate_score: function to calculate the difference between two signatures;
        :param dir_path: path to the directory containing break signature files;
        :param frequency: name of the frequency mode for break signatures. If None, then each frequency requires its
        own break signature;
        :param sensitive: name of the sensitivity mode for break signatures. If None, then each sensitivity requires
        its own break signature.
        """

        super().__init__()
        self._auto_settings: AutoSettings = auto_settings
        self._break_number: int = 0
        self._break_signatures: Dict[str, IVCurve] = dict()
        self._calculate_score: Callable[[IVCurve, IVCurve, MeasurementSettings], float] = calculate_score
        self._dir: str = dir_path
        self._product: EyePointProduct = product
        self._process: "PlanAutoTransition.Process" = self.Process.MEASURE
        self._required_frequency: Optional[str] = frequency
        self._required_sensitive: Optional[str] = sensitive
        self._score_wrapper: ScoreWrapper = score_wrapper
        self._start_time: Optional[float] = None

        self._create_timer()
        self._load_break_signatures()

    @property
    def auto_transition(self) -> bool:
        """
        :return: True if auto-transition mode is saved in the settings.
        """

        return self._auto_settings.auto_transition

    def _calculate_score_for_curves(self, settings: MeasurementSettings, curve_1: Optional[IVCurve] = None,
                                    curve_2: Optional[IVCurve] = None) -> Optional[float]:
        """
        :param settings: measurement settings;
        :param curve_1: first signature;
        :param curve_2: second signature.
        :return: difference for two signatures at given measurement settings.
        """

        if None in (curve_1, curve_2):
            return None

        return self._calculate_score(curve_1, curve_2, settings)

    @staticmethod
    def _check_frequency(settings: MeasurementSettings) -> bool:
        """
        :param settings: measurement settings.
        :return: True if the specified frequency is valid. Auto transition can only occur when the frequency is not
        1 Hz (see #92265).
        """

        return not math.isclose(settings.probe_signal_frequency, 1, abs_tol=PlanAutoTransition.FREQUENCY_TOLERANCE)

    def _check_probes_raised(self, settings: MeasurementSettings, curve: IVCurve, break_signature: IVCurve) -> None:
        """
        Method checks that the probes are raised. The probes are considered to be raised if the measured signature
        matches the break signature a certain number of times.
        :param settings: measurement settings;
        :param curve: current measured signature;
        :param break_signature: break signature.
        """

        score = self._calculate_score_for_curves(settings, curve, break_signature)
        if score is not None and check_difference_not_greater_tolerance(score, PlanAutoTransition.BREAK_TOLERANCE):
            self._break_number += 1
            logger.info("Waiting for a break: score = %f, number of sequentially measured breaks = %d", score,
                        self._break_number)
        else:
            logger.info("Waiting for a break: score = %s. Score does not correspond to the break, the number of "
                        "sequentially measured breaks is reset to zero", score)
            self._break_number = 0

        if self._break_number >= PlanAutoTransition.BREAK_NUMBER:
            logger.info("Probes raised")
            self._break_number = 0
            self._process = self.Process.WAIT
            self._timer.start()

    def _create_timer(self) -> None:
        self._timer: QTimer = QTimer()
        self._timer.setInterval(PlanAutoTransition.TIMEOUT_MS)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.handle_timeout)

    def _get_break_signature_for_settings(self, settings: MeasurementSettings) -> Optional[IVCurve]:
        """
        :param settings: measurement settings.
        :return: signature for a given measurement settings.
        """

        options = self._product.settings_to_options(settings)
        frequency = options[EyePointProduct.Parameter.frequency] if self._required_frequency is None else \
            self._required_frequency
        sensitive = options[EyePointProduct.Parameter.sensitive] if self._required_sensitive is None else \
            self._required_sensitive
        voltage = options[EyePointProduct.Parameter.voltage]
        filename = create_filename(frequency, sensitive, voltage)
        return self._break_signatures.get(filename, None)

    def _load_break_signatures(self) -> None:
        """
        Method loads break signatures for all required measurement settings.
        """

        self._break_signatures = dict()
        if os.path.exists(self._dir):
            for frequency, sensitive, voltage in iterate_settings(self._product, self._required_frequency,
                                                                  self._required_sensitive):
                filename = create_filename(frequency, sensitive, voltage)
                path = os.path.join(self._dir, filename)
                self._break_signatures[filename] = load_signature(path)

    def _save_measurements(self) -> None:
        logger.info("Signal sent to save signature")
        self._process = self.Process.RAISE_PROBES
        self.save_pin_signal.emit()
        self._start_time = time.monotonic()

    def _send_signal_to_go_to_next_pin(self) -> None:
        logger.info("Signal sent to move to the next pin")
        self._process = self.Process.MEASURE
        self.go_to_next_signal.emit(False, True)

    def check_auto_transition(self, work_mode: WorkMode, product_name: ProductName, settings: MeasurementSettings,
                              curve_current: Optional[IVCurve] = None, curve_reference: Optional[IVCurve] = None
                              ) -> None:
        """
        Method checks whether the currently measured signature matches the reference signature.
        :param work_mode: work mode;
        :param product_name: product name;
        :param settings: measurement settings;
        :param curve_current: current measured signature;
        :param curve_reference: reference signature.
        """

        if product_name in (None, ProductName.EYEPOINT_H10) or work_mode is not WorkMode.TEST or \
                not self.auto_transition or not self._check_frequency(settings):
            return

        break_signature = self._get_break_signature_for_settings(settings)
        if break_signature is None:
            return

        if self._process is self.Process.RAISE_PROBES:
            self._check_probes_raised(settings, curve_current, break_signature)
            return

        if self._process is not self.Process.MEASURE:
            return

        score = self._calculate_score_for_curves(settings, curve_current, break_signature)
        if score is not None and check_difference_not_greater_tolerance(score, self._score_wrapper.tolerance):
            logger.warning("The signature matched the break: difference (%f) less then tolerance (%f)", score,
                           self._score_wrapper.tolerance)
            return

        score = self._calculate_score_for_curves(settings, curve_current, curve_reference)
        if score is not None and check_difference_not_greater_tolerance(score, self._score_wrapper.tolerance):
            logger.info("The signature matched the reference: difference (%f) less than tolerance (%f)", score,
                        self._score_wrapper.tolerance)
            self._process = self.Process.SAVE

    @pyqtSlot()
    def handle_timeout(self) -> None:
        if self._process is self.Process.WAIT:
            if time.monotonic() - self._start_time > PlanAutoTransition.TIME_TO_SHOW_S:
                self._process = self.Process.GO_TO_NEXT
                return

            self._timer.start()

    def save_measurements_or_go_to_next_pin(self) -> None:
        if self._process is self.Process.SAVE:
            self._save_measurements()
        elif self._process is self.Process.GO_TO_NEXT:
            self._send_signal_to_go_to_next_pin()

    def set_measure_process(self) -> None:
        self._process = self.Process.MEASURE
