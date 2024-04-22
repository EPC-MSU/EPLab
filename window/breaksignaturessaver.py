import json
import logging
import math
import os
from typing import Generator, Optional, Tuple, Union
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, QObject, QTimer
from PyQt5.QtWidgets import QMessageBox
from epcore.elements import IVCurve, MeasurementSettings
from epcore.product import EyePointProduct, MeasurementParameterOption
from dialogs import ProgressWindow
from settings.autosettings import AutoSettings
from window.language import get_language, Language
from window import utils as ut


logger = logging.getLogger("eplab")


class BreakSignaturesSaver(QObject):
    """
    Class for storing break signatures for different measurement settings.
    """

    DIR_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "break_signatures")
    TIMEOUT: int = 10
    new_settings_signal: pyqtSignal = pyqtSignal(MeasurementSettings)

    def __init__(self, product: EyePointProduct, auto_settings: AutoSettings, frequency: Optional[str] = None,
                 sensitive: Optional[str] = None) -> None:
        """
        :param product: product;
        :param auto_settings: object with basic application settings;
        :param frequency: name of the frequency mode for break signatures. If None, then each frequency requires its
        own break signature;
        :param sensitive: name of the sensitivity mode for break signatures. If None, then each sensitivity requires
        its own break signature.
        """

        super().__init__()
        self._auto_settings: AutoSettings = auto_settings
        self._current_frequency: MeasurementParameterOption = None
        self._current_sensitive: MeasurementParameterOption = None
        self._current_voltage: MeasurementParameterOption = None
        self._is_running: bool = False
        self._language: Language = get_language()
        self._new_settings_required: bool = False
        self._product: EyePointProduct = product
        self._required_frequency: Optional[str] = frequency
        self._required_sensitive: Optional[str] = sensitive
        self._settings = None
        self._timer: QTimer = QTimer()
        self._timer.setInterval(BreakSignaturesSaver.TIMEOUT)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._send_settings)

    @property
    def auto_transition(self) -> bool:
        """
        :return: True if auto-transition mode is saved in the settings.
        """

        return self._auto_settings.get_auto_transition()

    def _check_required_settings(self, settings: MeasurementSettings) -> bool:
        """
        :param settings: measurement settings.
        :return: True if the current settings are equal to the given measurement settings.
        """

        abs_tol = 1e-6
        if self._current_frequency and self._current_sensitive and self._current_voltage:
            return (math.isclose(settings.probe_signal_frequency, self._current_frequency.value[0], abs_tol=abs_tol) and
                    math.isclose(settings.internal_resistance, self._current_sensitive.value, abs_tol=abs_tol) and
                    math.isclose(settings.max_voltage, self._current_voltage.value, abs_tol=abs_tol))
        return False

    def _get_settings_info(self) -> str:
        """
        :return: brief information with current measurement settings.
        """

        def get_info(option: MeasurementParameterOption) -> str:
            return option.label_en if self._language is Language.EN else option.label_ru

        frequency_info = get_info(self._current_frequency)
        sensitive_info = get_info(self._current_sensitive)
        voltage_info = get_info(self._current_voltage)
        return f"{frequency_info}, {sensitive_info}, {voltage_info}..."

    def _get_settings_total_number(self) -> int:
        """
        :return: the total number of measurement settings for which to save breaks.
        """

        parameters = self._product.get_parameters()
        number = 1
        if self._required_frequency is None:
            number *= len(parameters[EyePointProduct.Parameter.frequency].options)
        if self._required_sensitive is None:
            number *= len(parameters[EyePointProduct.Parameter.sensitive].options)
        number *= len(parameters[EyePointProduct.Parameter.voltage].options)
        return number

    def _request_new_settings(self) -> None:
        self._new_settings_required = True

    def _save_signature(self, curve: IVCurve) -> None:
        """
        :param curve: signature to be saved to file.
        """

        filename = create_filename(self._current_frequency, self._current_sensitive, self._current_voltage)
        path = os.path.join(BreakSignaturesSaver.DIR_PATH, filename)
        if not os.path.exists(BreakSignaturesSaver.DIR_PATH):
            os.makedirs(BreakSignaturesSaver.DIR_PATH, exist_ok=True)
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
            except StopIteration as exc:
                logger.error("An error occurred while sending settings (%s)", exc)
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
        self._settings = iterate_settings(self._product, self._required_frequency, self._required_sensitive)

    def save_break_signatures_if_necessary(self) -> None:
        """
        Method checks whether there are files with the required break signatures. If there are no files, then a process
        is launched to save the break signatures.
        """

        self._update_product()
        if self.auto_transition and not check_break_signatures(BreakSignaturesSaver.DIR_PATH, self._product,
                                                               self._required_frequency, self._required_sensitive):
            result = ut.show_message(qApp.translate("t", "Информация"),
                                     qApp.translate("t", "Чтобы включить автопереход в режиме тестирования по плану, "
                                                         "нужно измерить сигнатуры разрыва. Для этого:\n<ul>\n"
                                                         "<li>Разомкните щупы.</li>\n"
                                                         "<li>Нажмите 'Да'.</li>\n"
                                                         "<li>Дождитесь завершения процедуры.</li>\n</ul>"),
                                     icon=QMessageBox.Information, yes_button=True, no_button=True)
            if not result:
                self._request_new_settings()
                self._start_settings_iteration()

    def save_signature(self, settings: MeasurementSettings, curve: Optional[IVCurve] = None) -> None:
        """
        :param settings: measurement settings;
        :param curve: signature to save.
        """

        if self._is_running and curve and self._check_required_settings(settings):
            self._save_signature(curve)
            self._request_new_settings()


def check_break_signatures(dir_path: str, product: EyePointProduct, required_frequency: Optional[str] = None,
                           required_sensitive: Optional[str] = None) -> bool:
    """
    :param dir_path: directory containing files with break signatures;
    :param product: product;
    :param required_frequency: name of the frequency mode for break signatures. If None, then each frequency requires
    its own break signature;
    :param required_sensitive: name of the sensitivity mode for break signatures. If None, then each sensitivity
    requires its own break signature.
    :return: True if all required break signatures are present.
    """

    if not os.path.isdir(dir_path):
        return False

    try:
        for frequency, sensitive, voltage in iterate_settings(product, required_frequency, required_sensitive):
            filename = create_filename(frequency, sensitive, voltage)
            path = os.path.join(dir_path, filename)
            if not os.path.exists(path):
                return False

            load_signature(path)
    except Exception as exc:
        logger.error("An error occurred while checking break signatures (%s)", exc)
        return False

    return True


def create_filename(frequency: Union[str, MeasurementParameterOption],
                    sensitive: Union[str, MeasurementParameterOption],
                    voltage: Union[str, MeasurementParameterOption]) -> str:
    """
    :param frequency: frequency;
    :param sensitive: sensitive;
    :param voltage: voltage.
    :return: file name for break signature.
    """

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
    """
    :param frequency: frequency;
    :param sensitive: sensitive;
    :param voltage: voltage.
    :return: measurement settings.
    """

    probe_frequency, sampling_rate = frequency.value
    return MeasurementSettings(sampling_rate=sampling_rate,
                               internal_resistance=sensitive.value,
                               max_voltage=voltage.value,
                               probe_signal_frequency=probe_frequency)


def iterate_settings(product: EyePointProduct, required_frequency: Optional[str] = None,
                     required_sensitive: Optional[str] = None
                     ) -> Generator[Tuple[MeasurementParameterOption, MeasurementParameterOption,
                                          MeasurementParameterOption], None, None]:
    """
    :param product: product;
    :param required_frequency: name of the frequency mode for break signatures. If None, then each frequency requires
    its own break signature;
    :param required_sensitive: name of the sensitivity mode for break signatures. If None, then each sensitivity
    requires its own break signature.
    :return: frequency, sensitive and voltage.
    """

    parameters = product.get_parameters()
    for frequency in parameters[EyePointProduct.Parameter.frequency].options:
        if required_frequency is not None and required_frequency.lower() != frequency.name.lower():
            continue

        for sensitive in parameters[EyePointProduct.Parameter.sensitive].options:
            if required_sensitive is not None and required_sensitive.lower() != sensitive.name.lower():
                continue

            for voltage in parameters[EyePointProduct.Parameter.voltage].options:
                yield frequency, sensitive, voltage


def load_signature(path: str) -> Optional[IVCurve]:
    """
    :param path: path to the signature file.
    :return: signature.
    """

    if os.path.exists(path):
        with open(path, "r") as file:
            return IVCurve.create_from_json(json.load(file))
    return None
