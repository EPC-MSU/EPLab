import copy
import os
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QDialog, QLayout, QSizePolicy
from .autosettings import AutoSettings


class SettingsWindow(QDialog):
    """
    Class for dialog window with measurement settings.
    """

    THRESHOLD_STEP: float = 0.05
    apply_settings_signal: pyqtSignal = pyqtSignal(AutoSettings)

    def __init__(self, main_window, init_settings: AutoSettings) -> None:
        """
        :param main_window: main window of application;
        :param init_settings: initial settings of the application.
        """

        super().__init__(main_window, Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        self._init_settings: AutoSettings = init_settings
        self._settings: AutoSettings = copy.copy(init_settings)
        self._init_ui()
        self._set_settings(self._init_settings)

    def _connect_signals(self) -> None:
        self.button_cancel.clicked.connect(self.discard_changes)
        self.button_ok.clicked.connect(self.apply_changes)
        self.button_tolerance_minus.clicked.connect(self.decrease_tolerance)
        self.button_tolerance_plus.clicked.connect(self.increase_tolerance)
        self.check_box_auto_transition.stateChanged.connect(self.update_auto_transition)
        self.check_box_pin_shift_warning_info.stateChanged.connect(self.update_pin_shift_warning_info)
        self.check_box_warning_about_untested_pins_in_report.stateChanged.connect(
            self.update_warning_about_untested_pins_in_report)
        self.spin_box_max_optimal_voltage.valueChanged.connect(self.update_max_optimal_voltage)
        self.spin_box_tolerance.valueChanged.connect(self.update_tolerance)

    def _init_ui(self) -> None:
        dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uic.loadUi(os.path.join(dir_name, "gui", "settings.ui"), self)
        if self.parent().measurement_plan and self.parent().measurement_plan.multiplexer:
            self.label_auto_transition.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            self.check_box_auto_transition.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            self.label_auto_transition.hide()
            self.check_box_auto_transition.hide()
            self.grid_layout.setRowMinimumHeight(1, 0)

        self._connect_signals()
        self.button_ok.setDefault(True)
        self.adjustSize()
        self.layout().setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

    def _get_tolerance_value(self) -> float:
        """
        :return: tolerance value.
        """

        return self.spin_box_tolerance.value() / 100.0

    def _send_settings(self, settings: AutoSettings = None) -> None:
        """
        :param settings: settings to be sent.
        """

        self.apply_settings_signal.emit(settings or self._settings)

    def _set_settings(self, settings: AutoSettings) -> None:
        """
        :param settings: new settings.
        """

        self._update_auto_transition(settings.auto_transition)
        self._update_max_optimal_voltage(settings.max_optimal_voltage)
        self._update_pin_shift_warning_info(settings.pin_shift_warning_info)
        self._update_tolerance_in_settings_wnd(settings.tolerance)
        self._update_warning_about_untested_pins_in_report(settings.warning_about_untested_pins_in_report)

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

    def _update_warning_about_untested_pins_in_report(self, warning_about_untested_pins_in_report: bool) -> None:
        """
        :param warning_about_untested_pins_in_report: if True, then warn about untested points when generating a report.
        """

        self.check_box_warning_about_untested_pins_in_report.setChecked(warning_about_untested_pins_in_report)
        self._settings.warning_about_untested_pins_in_report = warning_about_untested_pins_in_report

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

        self._update_tolerance_in_settings_wnd(self._get_tolerance_value() - self.THRESHOLD_STEP)
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

        self._update_tolerance_in_settings_wnd(self._get_tolerance_value() + self.THRESHOLD_STEP)
        self._send_settings()

    @pyqtSlot(int)
    def update_auto_transition(self, state: int) -> None:
        """
        :param state: if True, then the auto transition mode is activated when testing according to plan.
        """

        self._update_auto_transition(state == Qt.CheckState.Checked)
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

        self._update_pin_shift_warning_info(state == Qt.CheckState.Checked)
        self._send_settings()

    @pyqtSlot(float)
    def update_tolerance(self, new_value: float) -> None:
        """
        :param new_value: new tolerance value.
        """

        self._update_tolerance_in_settings_wnd(new_value / 100)
        self._send_settings()

    @pyqtSlot(int)
    def update_warning_about_untested_pins_in_report(self, state: int) -> None:
        """
        :param state: if True, then warn about untested points when generating a report.
        """

        self._update_warning_about_untested_pins_in_report(state == Qt.CheckState.Checked)
        self._send_settings()
