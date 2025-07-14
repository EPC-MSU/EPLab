import copy
import os
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QLayout
from window import utils as ut
from window.scaler import update_scale_of_class
from .settings import Settings
from .utils import InvalidParameterValueError, MissingParameterError


@update_scale_of_class
class SettingsWindow(QDialog):
    """
    Class for dialog window with measurement settings.
    """

    THRESHOLD_STEP: float = 0.05
    apply_settings_signal: pyqtSignal = pyqtSignal(Settings)

    def __init__(self, main_window, init_settings: Settings, settings_directory: str = None) -> None:
        """
        :param main_window: main window of application;
        :param init_settings: initial settings of the application;
        :param settings_directory: directory for settings file.
        """

        super().__init__(main_window, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._init_settings: Settings = init_settings
        self._settings: Settings = copy.copy(init_settings)
        self._settings_directory: str = settings_directory or ut.get_dir_name()
        self._init_ui()
        self._update_options(self._init_settings)

    @property
    def settings_directory(self) -> str:
        """
        :return: the directory in which the configuration file with settings was last saved or opened from.
        """

        return self._settings_directory

    def _init_ui(self) -> None:
        dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uic.loadUi(os.path.join(dir_name, "gui", "settings.ui"), self)
        self.button_tolerance_minus.clicked.connect(self.decrease_tolerance)
        self.button_tolerance_plus.clicked.connect(self.increase_tolerance)
        self.check_box_auto_transition.stateChanged.connect(self.update_auto_transition)
        if self.parent().measurement_plan and self.parent().measurement_plan.multiplexer:
            self.label_auto_transition.hide()
            self.check_box_auto_transition.hide()
        self.check_box_pin_shift_warning_info.stateChanged.connect(self.update_pin_shift_warning_info)
        self.spin_box_tolerance.valueChanged.connect(self.update_tolerance)
        self.spin_box_max_optimal_voltage.valueChanged.connect(self.update_max_optimal_voltage)

        self.button_cancel.clicked.connect(self.discard_changes)
        self.button_load_settings.clicked.connect(self.open_settings)
        self.button_ok.clicked.connect(self.apply_changes)
        self.button_ok.setDefault(True)
        self.button_save_settings.clicked.connect(self.save_settings_to_file)
        self.adjustSize()
        self.layout().setSizeConstraint(QLayout.SetFixedSize)

    def _get_tolerance_value(self) -> float:
        """
        :return: tolerance value.
        """

        return self.spin_box_tolerance.value() / 100.0

    def _send_settings(self, settings: Settings = None) -> None:
        """
        :param settings: settings to be sent.
        """

        self.apply_settings_signal.emit(settings or self._settings)

    def _update_auto_transition(self, auto_transition: bool) -> None:
        """
        :param auto_transition: new value for enabling or disabling auto transition in plan testing mode.
        """

        self.check_box_auto_transition.setChecked(auto_transition)
        self._settings.auto_transition = auto_transition

    def _update_max_optimal_voltage(self, max_optimal_voltage: float) -> None:
        """
        :param max_optimal_voltage: new value for maximum voltage when searching for optimal measurement settings.
        """

        self.spin_box_max_optimal_voltage.setValue(max_optimal_voltage)
        self._settings.max_optimal_voltage = max_optimal_voltage

    def _update_options(self, settings: Settings) -> None:
        """
        :param settings: new settings.
        """

        self._update_auto_transition(settings.auto_transition)
        self._update_max_optimal_voltage(settings.max_optimal_voltage)
        self._update_pin_shift_warning_info(settings.pin_shift_warning_info)
        self._update_tolerance_in_settings_wnd(settings.tolerance)

    def _update_pin_shift_warning_info(self, pin_shift_warning_info: bool) -> None:
        """
        :param pin_shift_warning_info: new value for enabling or disabling auto transition in plan testing mode.
        """

        self.check_box_pin_shift_warning_info.setChecked(pin_shift_warning_info)
        self._settings.pin_shift_warning_info = pin_shift_warning_info

    def _update_tolerance_in_settings_wnd(self, tolerance: float) -> None:
        """
        Method updates tolerance value in settings window.
        :param tolerance: new tolerance value.
        """

        tolerance = min(max(round(100 * tolerance, 1), 0), 100)
        self.spin_box_tolerance.setValue(tolerance)
        self._settings.tolerance = self._get_tolerance_value()

    @pyqtSlot()
    def apply_changes(self) -> None:
        """
        Slot applies all changes in the settings and closes the dialog window.
        """

        self._send_settings()
        self.close()

    @pyqtSlot()
    def decrease_tolerance(self) -> None:
        """
        Slot decreases the tolerance value by a given step.
        """

        self._update_tolerance_in_settings_wnd(self._get_tolerance_value() - SettingsWindow.THRESHOLD_STEP)
        self._send_settings()

    @pyqtSlot()
    def discard_changes(self) -> None:
        """
        Slot refuses changes to the settings, returns the original settings and closes the dialog window.
        """

        self._send_settings(self._init_settings)
        self.close()

    @pyqtSlot()
    def increase_tolerance(self) -> None:
        """
        Slot increases the tolerance value by a given step.
        """

        self._update_tolerance_in_settings_wnd(self._get_tolerance_value() + SettingsWindow.THRESHOLD_STEP)
        self._send_settings()

    @pyqtSlot()
    def open_settings(self) -> None:
        """
        Slot loads settings from the configuration file.
        """

        settings_path = QFileDialog.getOpenFileName(self, qApp.translate("settings", "Открыть файл"),
                                                    self._settings_directory, "Ini file (*.ini);;All Files (*)")[0]
        if settings_path:
            try:
                settings = Settings()
                settings.set_default_values(**self._settings.get_values())
                settings.read(path=settings_path)
            except (InvalidParameterValueError, MissingParameterError) as exc:
                error_message = qApp.translate("settings", "Проверьте конфигурационный файл '{}'.").format(
                    settings_path)
                ut.show_message(qApp.translate("t", "Ошибка"), f"{exc}\n{error_message}")
                return

            self._settings_directory = os.path.dirname(settings_path)
            self._settings = settings
            self._update_options(self._settings)
            self._send_settings()

    @pyqtSlot()
    def save_settings_to_file(self) -> None:
        """
        Slot saves settings to a configuration file.
        """

        settings_path = QFileDialog.getSaveFileName(self, qApp.translate("settings", "Сохранить файл"),
                                                    directory=os.path.join(self._settings_directory, "settings.ini"),
                                                    filter="Ini file (*.ini);;All Files (*)")[0]
        if settings_path:
            self._settings_directory = os.path.dirname(settings_path)
            if not settings_path.endswith(".ini"):
                settings_path += ".ini"
            self._settings.tolerance = self._get_tolerance_value()
            self._settings.export(path=settings_path)

    @pyqtSlot(int)
    def update_auto_transition(self, state: int) -> None:
        """
        :param state: if True, then the auto transition mode is activated when testing according to plan.
        """

        self._update_auto_transition(state == Qt.Checked)
        self._send_settings()

    @pyqtSlot(float)
    def update_max_optimal_voltage(self, new_value: float) -> None:
        """
        :param new_value: new max voltage for optimal search.
        """

        self._update_max_optimal_voltage(new_value)
        self._send_settings()

    @pyqtSlot(int)
    def update_pin_shift_warning_info(self, state: int) -> None:
        """
        :param state: if True, then the auto transition mode is activated when testing according to plan.
        """

        self._update_pin_shift_warning_info(state == Qt.Checked)
        self._send_settings()

    @pyqtSlot(float)
    def update_tolerance(self, new_value: float) -> None:
        """
        :param new_value: new tolerance value.
        """

        self._update_tolerance_in_settings_wnd(new_value / 100)
        self._send_settings()
