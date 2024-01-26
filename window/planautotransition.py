import json
import os
import time
from enum import auto, Enum
from typing import Callable, Dict, Optional
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QTimer
from epcore.elements import IVCurve, MeasurementSettings
from epcore.product import EyePointProduct
from settings.autosettings import AutoSettings
from window.breaksignaturessaver import create_filename, iterate_settings
from window.common import WorkMode
from window.scorewrapper import ScoreWrapper


class PlanAutoTransition(QObject):

    class Process(Enum):
        GO_TO_NEXT = auto()
        MEASURE = auto()
        SAVE = auto()

    BREAK_THRESHOLD: float = 0.15
    TIME_TO_GO_TO_NEXT: float = 6
    TIME_TO_SHOW: float = 2
    go_to_next_signal: pyqtSignal = pyqtSignal(bool)
    save_pin_signal: pyqtSignal = pyqtSignal()

    def __init__(self, product: EyePointProduct, auto_settings: AutoSettings, score_wrapper: ScoreWrapper,
                 calculate_score: Callable[[IVCurve, IVCurve, MeasurementSettings], float]) -> None:
        """
        :param product:
        :param auto_settings:
        :param score_wrapper:
        :param calculate_score:
        """

        super().__init__()
        self._auto_settings: AutoSettings = auto_settings
        self._break_signatures: Dict[str, IVCurve] = dict()
        self._calculate_score: Callable[[IVCurve, IVCurve, MeasurementSettings], float] = calculate_score
        self._dir: str = os.path.join(os.path.curdir, "break_signatures")
        self._need_to_save: bool = False
        self._product: EyePointProduct = product
        self._process: "PlanAutoTransition.Process" = self.Process.MEASURE
        self._score_wrapper: ScoreWrapper = score_wrapper
        self._start_time: float = None
        self._timer: QTimer = QTimer()
        self._timer.setInterval(10)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.handle_timeout)

        self._load_break_signatures()

    @property
    def auto_transition(self) -> bool:
        return self._auto_settings.get_auto_transition()

    def _calculate_score_for_curves(self, curve_1: Optional[IVCurve] = None, curve_2: Optional[IVCurve] = None,
                                    settings: Optional[MeasurementSettings] = None) -> Optional[float]:
        if None in (curve_1, curve_2, settings):
            return None

        return self._calculate_score(curve_1, curve_2, settings)

    def _get_break_signature_for_settings(self, settings: MeasurementSettings) -> Optional[IVCurve]:
        options = self._product.settings_to_options(settings)
        frequency = options[EyePointProduct.Parameter.frequency]
        sensitive = options[EyePointProduct.Parameter.sensitive]
        voltage = options[EyePointProduct.Parameter.voltage]
        filename = create_filename(frequency, sensitive, voltage)
        return self._break_signatures.get(filename, None)

    @staticmethod
    def _load_break_signature(path: str) -> Optional[IVCurve]:
        if os.path.exists(path):
            with open(path, "r") as file:
                return IVCurve.create_from_json(json.load(file))
        return None

    def _load_break_signatures(self) -> None:
        self._break_signatures = dict()
        if os.path.exists(self._dir):
            for frequency, sensitive, voltage in iterate_settings(self._product):
                filename = create_filename(frequency, sensitive, voltage)
                path = os.path.join(self._dir, filename)
                self._break_signatures[filename] = self._load_break_signature(path)

    def check_auto_transition(self, work_mode: WorkMode, curve_current: Optional[IVCurve] = None,
                              curve_reference: Optional[IVCurve] = None, settings: Optional[MeasurementSettings] = None
                              ) -> None:
        self._need_to_save = False
        if self._process != self.Process.MEASURE:
            return

        break_signature = self._get_break_signature_for_settings(settings)
        if work_mode is not WorkMode.TEST or not self.auto_transition or break_signature is None:
            return

        score = self._calculate_score_for_curves(curve_current, break_signature, settings)
        if score is not None and self._score_wrapper.check_score(score):
            return

        score = self._calculate_score_for_curves(curve_current, curve_reference, settings)
        if score is not None and self._score_wrapper.check_score(score):
            self._need_to_save = True

    @pyqtSlot()
    def handle_timeout(self) -> None:
        if self._process == self.Process.SAVE and time.monotonic() - self._start_time > self.TIME_TO_SHOW:
            self.go_to_next_signal.emit(False)
            self._process = self.Process.GO_TO_NEXT
            self._start_time = time.monotonic()
        elif self._process == self.Process.GO_TO_NEXT and time.monotonic() - self._start_time > self.TIME_TO_GO_TO_NEXT:
            self._process = self.Process.MEASURE
            return

        self._timer.start()

    def save_pin(self) -> None:
        if self._need_to_save:
            self._need_to_save = False
            self.save_pin_signal.emit()
            self._process = self.Process.SAVE
            self._start_time = time.monotonic()
            self._timer.start()
