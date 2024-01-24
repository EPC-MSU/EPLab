import os
from typing import Generator, Tuple
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, QObject, Qt, QTimer
from PyQt5.QtWidgets import QDialog, QLayout, QProgressBar, QTextEdit, QVBoxLayout
from epcore.elements import MeasurementSettings
from epcore.product import EyePointProduct, MeasurementParameterOption
from settings.autosettings import AutoSettings
from window import utils as ut
from window.scaler import update_scale_of_class


class PlanAutoTransition(QObject):

    def __init__(self, auto_settings: AutoSettings) -> None:
        """
        :param auto_settings:
        """

        super().__init__()
        self._auto_settings: AutoSettings = auto_settings
        self._break_signature_saver: BreakSignaturesSaver = None
        self._dir: str = os.path.join(os.path.curdir, "break_signatures")
        self._product: EyePointProduct = None

    @property
    def auto_transition(self) -> bool:
        return self._auto_settings.get_auto_transition()

    def _create_dir(self) -> None:
        os.makedirs(self._dir, exist_ok=True)

    def _get_settings_total_number(self) -> int:
        parameters = self._product.get_parameters()
        number = 1
        for param in (EyePointProduct.Parameter.frequency, EyePointProduct.Parameter.voltage,
                      EyePointProduct.Parameter.sensitive):
            number *= len(parameters[param].options)
        return number

    def _iterate_settings(self) -> Generator[Tuple[MeasurementParameterOption, MeasurementParameterOption,
                                                   MeasurementParameterOption], None, None]:
        parameters = self._product.get_parameters()
        for frequency in parameters[EyePointProduct.Parameter.frequency].options:
            for voltage in parameters[EyePointProduct.Parameter.voltage].options:
                for sensitive in parameters[EyePointProduct.Parameter.sensitive].options:
                    yield frequency, voltage, sensitive

    def _save_break_signatures(self) -> None:
        self._create_dir()
        self._break_signature_saver = BreakSignaturesSaver(self._iterate_settings())
        self._break_signature_saver._iterate_settings()

    def save_break_signatures_if_necessary(self, product: EyePointProduct) -> None:
        """
        :param product:
        """

        self._product = product
        if self.auto_transition and not self._check_break_signatures():
            result = ut.show_message(qApp.translate("t", "Информация"),
                                     qApp.translate("t", "Чтобы включить автопереход в режиме тестирования по плану, "
                                                         "нужно измерить сигнатуры разрыва. Для этого:\n<ul>\n"
                                                         "<li>разомкните щупы;</li>\n"
                                                         "<li>нажмите 'OK';</li>\n"
                                                         "<li>дождитесь появления сообщения о завершении процедуры."
                                                         "</li>\n</ul>"), yes_button=True, no_button=True)
            if not result:
                self._save_break_signatures()


def create_name(frequency: MeasurementParameterOption, voltage: MeasurementParameterOption,
                sensitive: MeasurementParameterOption) -> str:
    return f"{frequency.name}-{voltage.name}-{sensitive.name}.txt"


class BreakSignaturesSaver(QObject):

    TIMEOUT: int = 10
    new_settings_signal: pyqtSignal = pyqtSignal(MeasurementSettings)

    def __init__(self, main_window, auto_settings: AutoSettings) -> None:
        super().__init__()
        self._auto_settings: AutoSettings = auto_settings
        self._dir: str = os.path.join(os.path.curdir, "break_signatures")
        self._is_running: bool = False
        self._main_window = main_window
        self._new_settings_required: bool = True
        self._product: EyePointProduct = None
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

        for frequency, voltage, sensitive in self._iterate_settings():
            filename = create_name(frequency, voltage, sensitive)
            path = os.path.join(self._dir, filename)
            if not os.path.exists(path):
                return False

        return True

    @staticmethod
    def _get_settings(frequence: MeasurementParameterOption, voltage: MeasurementParameterOption,
                      sensitive: MeasurementParameterOption) -> MeasurementSettings:
        probe_frequency, sampling_rate = frequence.value
        return MeasurementSettings(sampling_rate=sampling_rate,
                                   internal_resistance=sensitive.value,
                                   max_voltage=voltage.value,
                                   probe_signal_frequency=probe_frequency)

    def _get_settings_total_number(self) -> int:
        parameters = self._product.get_parameters()
        number = 1
        for param in (EyePointProduct.Parameter.frequency, EyePointProduct.Parameter.voltage,
                      EyePointProduct.Parameter.sensitive):
            number *= len(parameters[param].options)
        return number

    def _iterate_settings(self) -> Generator[Tuple[MeasurementParameterOption, MeasurementParameterOption,
                                                   MeasurementParameterOption], None, None]:
        parameters = self._product.get_parameters()
        for frequency in parameters[EyePointProduct.Parameter.frequency].options:
            for voltage in parameters[EyePointProduct.Parameter.voltage].options:
                for sensitive in parameters[EyePointProduct.Parameter.sensitive].options:
                    yield frequency, voltage, sensitive

    def _request_new_settings(self) -> None:
        self._new_settings_required = True

    @pyqtSlot()
    def _send_settings(self) -> None:
        if self._new_settings_required:
            try:
                self.new_settings_signal.emit(self._get_settings(*next(self._settings)))
                self._window.change_progress()
                self._new_settings_required = False
            except StopIteration:
                self._is_running = False
                return

        self._timer.start()

    def _start_settings_iteration(self) -> None:
        self._window: ProgressWindow = ProgressWindow(self._main_window)
        self._window.set_total_number_of_steps(self._get_settings_total_number())
        self._is_running = True
        self._timer.start()
        self._window.exec()

    def _update_product(self, product: EyePointProduct) -> None:
        self._product = product
        self._settings = self._iterate_settings()

    def save_signature(self) -> None:
        if self.is_running:
            self._request_new_settings()

    def save_break_signatures_if_necessary(self, product: EyePointProduct) -> None:
        self._update_product(product)
        if self.auto_transition and not self._check_break_signatures():
            result = ut.show_message(qApp.translate("t", "Информация"),
                                     qApp.translate("t", "Чтобы включить автопереход в режиме тестирования по плану, "
                                                         "нужно измерить сигнатуры разрыва. Для этого:\n<ul>\n"
                                                         "<li>разомкните щупы;</li>\n"
                                                         "<li>нажмите 'OK';</li>\n"
                                                         "<li>дождитесь появления сообщения о завершении процедуры."
                                                         "</li>\n</ul>"), yes_button=True, no_button=True)
            if not result:
                self._start_settings_iteration()


@update_scale_of_class
class ProgressWindow(QDialog):

    def __init__(self, parent) -> None:
        """
        :param parent:
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._number_of_steps_done: int = 0
        self._total_number: int = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle(qApp.translate("t", "Генератор отчетов"))
        self.progress_bar: QProgressBar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.text_edit_info: QTextEdit = QTextEdit()
        self.text_edit_info.setMaximumHeight(100)
        self.text_edit_info.setReadOnly(True)

        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self.progress_bar)
        v_box_layout.addWidget(self.text_edit_info)
        v_box_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(v_box_layout)
        self.adjustSize()

    @pyqtSlot()
    def change_progress(self) -> None:
        self._number_of_steps_done += 1
        self.progress_bar.setValue(int(self._number_of_steps_done / self._total_number * 100))

    @pyqtSlot(int)
    def set_total_number_of_steps(self, number: int) -> None:
        """
        :param number: total number of steps to generate a report.
        """

        self._total_number = number
