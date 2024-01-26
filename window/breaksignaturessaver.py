import json
import math
import os
from typing import Generator, Optional, Tuple, Union
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, QObject, QTimer
from epcore.elements import IVCurve, MeasurementSettings
from epcore.product import EyePointProduct, MeasurementParameterOption
from dialogs import ProgressWindow
from settings.autosettings import AutoSettings
from window.language import Language
from window import utils as ut


class BreakSignaturesSaver(QObject):

    TIMEOUT: int = 10
    new_settings_signal: pyqtSignal = pyqtSignal(MeasurementSettings)

    def __init__(self, product: EyePointProduct, auto_settings: AutoSettings) -> None:
        """
        :param product:
        :param auto_settings:
        """

        super().__init__()
        self._auto_settings: AutoSettings = auto_settings
        self._current_frequency: MeasurementParameterOption = None
        self._current_sensitive: MeasurementParameterOption = None
        self._current_voltage: MeasurementParameterOption = None
        self._dir: str = os.path.join(os.path.curdir, "break_signatures")
        self._is_running: bool = False
        self._language: Language = self._get_language()
        self._new_settings_required: bool = False
        self._product: EyePointProduct = product
        self._settings = None
        self._timer: QTimer = QTimer()
        self._timer.setInterval(BreakSignaturesSaver.TIMEOUT)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._send_settings)

    @property
    def auto_transition(self) -> bool:
        return self._auto_settings.get_auto_transition()

    @property
    def is_running(self) -> bool:
        return self._is_running

    def _check_break_signatures(self) -> bool:
        if not os.path.isdir(self._dir):
            return False

        for frequency, sensitive, voltage in iterate_settings(self._product):
            filename = create_filename(frequency, sensitive, voltage)
            path = os.path.join(self._dir, filename)
            if not os.path.exists(path):
                return False

        return True

    def _check_required_settings(self, settings: MeasurementSettings) -> bool:
        abs_tol = 1e-6
        if self._current_frequency and self._current_sensitive and self._current_voltage:
            return (math.isclose(settings.probe_signal_frequency, self._current_frequency.value[0], abs_tol=abs_tol) and
                    math.isclose(settings.internal_resistance, self._current_sensitive.value, abs_tol=abs_tol) and
                    math.isclose(settings.max_voltage, self._current_voltage.value, abs_tol=abs_tol))
        return False

    @staticmethod
    def _get_language() -> Language:
        language = qApp.instance().property("language")
        return Language.EN if language is None else language

    def _get_settings_info(self) -> str:

        def get_info(option: MeasurementParameterOption) -> str:
            return option.label_en if self._language is Language.EN else option.label_ru

        frequency_info = get_info(self._current_frequency)
        sensitive_info = get_info(self._current_sensitive)
        voltage_info = get_info(self._current_voltage)
        return f"{frequency_info}, {sensitive_info}, {voltage_info}..."

    def _get_settings_total_number(self) -> int:
        parameters = self._product.get_parameters()
        number = 1
        for param in (EyePointProduct.Parameter.frequency, EyePointProduct.Parameter.voltage,
                      EyePointProduct.Parameter.sensitive):
            number *= len(parameters[param].options)
        return number

    def _request_new_settings(self) -> None:
        self._new_settings_required = True

    def _save_signature(self, curve: IVCurve) -> None:
        filename = create_filename(self._current_frequency, self._current_sensitive, self._current_voltage)
        path = os.path.join(self._dir, filename)
        if not os.path.exists(self._dir):
            os.makedirs(self._dir, exist_ok=True)
        with open(path, "w") as file:
            json.dump(curve.to_json(), file)

    @pyqtSlot()
    def _send_settings(self) -> None:
        if self._new_settings_required:
            try:
                self._current_frequency, self._current_sensitive, self._current_voltage = next(self._settings)
                settings = create_settings(self._current_frequency, self._current_sensitive, self._current_voltage)
                self.new_settings_signal.emit(settings)
                info = self._get_settings_info()
                self._window.change_progress(info)
                self._new_settings_required = False
            except StopIteration:
                self._is_running = False
                return

        self._timer.start()

    def _start_settings_iteration(self) -> None:
        self._window: ProgressWindow = ProgressWindow(qApp.translate("t", "Сохранение сигнатур разрыва"))
        self._window.set_total_number_of_steps(self._get_settings_total_number())
        self._is_running = True
        self._timer.start()
        self._window.exec()

    def _update_product(self) -> None:
        self._settings = iterate_settings(self._product)

    def save_break_signatures_if_necessary(self) -> None:
        self._update_product()
        if self.auto_transition and not self._check_break_signatures():
            result = ut.show_message(qApp.translate("t", "Информация"),
                                     qApp.translate("t", "Чтобы включить автопереход в режиме тестирования по плану, "
                                                         "нужно измерить сигнатуры разрыва. Для этого:\n<ul>\n"
                                                         "<li>разомкните щупы;</li>\n"
                                                         "<li>нажмите 'Да';</li>\n"
                                                         "<li>дождитесь появления сообщения о завершении процедуры."
                                                         "</li>\n</ul>"), yes_button=True, no_button=True)
            if not result:
                self._request_new_settings()
                self._start_settings_iteration()

    def save_signature(self, curve: Optional[IVCurve] = None, settings: Optional[MeasurementSettings] = None) -> None:
        if self.is_running and curve and settings and self._check_required_settings(settings):
            self._save_signature(curve)
            self._request_new_settings()


def create_filename(frequency: Union[str, MeasurementParameterOption],
                    sensitive: Union[str, MeasurementParameterOption],
                    voltage: Union[str, MeasurementParameterOption]) -> str:

    def get_name(value: Union[str, MeasurementParameterOption]) -> str:
        if isinstance(value, MeasurementParameterOption):
            value = value.name
        return value

    frequency = get_name(frequency)
    sensitive = get_name(sensitive)
    voltage = get_name(voltage)
    return f"{frequency}-{sensitive}-{voltage}.json"


def create_settings(frequency: MeasurementParameterOption, sensitive: MeasurementParameterOption,
                    voltage: MeasurementParameterOption) -> MeasurementSettings:
    probe_frequency, sampling_rate = frequency.value
    return MeasurementSettings(sampling_rate=sampling_rate,
                               internal_resistance=sensitive.value,
                               max_voltage=voltage.value,
                               probe_signal_frequency=probe_frequency)


def iterate_settings(product: EyePointProduct) -> Generator[Tuple[MeasurementParameterOption,
                                                                  MeasurementParameterOption,
                                                                  MeasurementParameterOption], None, None]:
    parameters = product.get_parameters()
    for frequency in parameters[EyePointProduct.Parameter.frequency].options:
        for sensitive in parameters[EyePointProduct.Parameter.sensitive].options:
            for voltage in parameters[EyePointProduct.Parameter.voltage].options:
                yield frequency, sensitive, voltage
