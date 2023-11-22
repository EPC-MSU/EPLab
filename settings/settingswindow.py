import copy
import os
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QLayout
from settings.settings import Settings
from settings.utils import InvalidParameterValueError, MissingParameterError
from window import utils as ut
from window.scaler import update_scale_of_class


@update_scale_of_class
class SettingsWindow(QDialog):
    """
    Class for dialog window with measurement settings.
    """

    THRESHOLD_STEP: float = 0.05
    apply_settings_signal: pyqtSignal = pyqtSignal(Settings)

    def __init__(self, parent, init_settings: Settings, settings_directory: str = None) -> None:
        """
        :param parent: main window;
        :param init_settings: initial settings of application;
        :param settings_directory: directory for settings file.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._init_settings: Settings = init_settings
        self._settings: Settings = copy.copy(init_settings)
        self._settings_directory: str = settings_directory or ut.get_dir_name()
        self._init_ui()
        self._update_threshold_in_settings_wnd(self._init_settings.score_threshold)

    @property
    def settings_directory(self) -> str:
        """
        :return: the directory in which the configuration file with settings was last saved or opened from.
        """

        return self._settings_directory

    def _init_ui(self) -> None:
        dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uic.loadUi(os.path.join(dir_name, "gui", "settings.ui"), self)
        self.layout().setSizeConstraint(QLayout.SetFixedSize)
        self.button_score_threshold_minus.clicked.connect(self.decrease_threshold)
        self.button_score_threshold_plus.clicked.connect(self.increase_threshold)
        self.spin_box_score_threshold.valueChanged.connect(self.update_threshold)
        self.button_cancel.clicked.connect(self.discard_changes)
        self.button_load_settings.clicked.connect(self.open_settings)
        self.button_ok.clicked.connect(self.apply_changes)
        self.button_save_settings.clicked.connect(self.save_settings_to_file)

    def _get_threshold_value(self) -> float:
        """
        :return: score threshold value.
        """

        value = self.spin_box_score_threshold.value()
        return float(value / 100.0)

    def _send_settings(self, settings: Settings = None) -> None:
        """
        :param settings: settings to be sent.
        """

        self.apply_settings_signal.emit(settings or self._settings)

    def _update_threshold_in_settings_wnd(self, threshold: float) -> None:
        """
        Method updates score threshold value in settings window.
        :param threshold: new score threshold value.
        """

        threshold = min(max(round(100 * threshold), 0), 100)
        self.spin_box_score_threshold.setValue(threshold)
        self._settings.score_threshold = self._get_threshold_value()

    @pyqtSlot()
    def apply_changes(self) -> None:
        """
        Slot applies all changes in the settings and closes the dialog window.
        """

        self._send_settings()
        self.close()

    @pyqtSlot()
    def decrease_threshold(self) -> None:
        """
        Slot decreases the threshold value by a given step.
        """

        self._update_threshold_in_settings_wnd(self._get_threshold_value() - SettingsWindow.THRESHOLD_STEP)
        self._send_settings()

    @pyqtSlot()
    def discard_changes(self) -> None:
        """
        Slot refuses changes to the settings, returns the original settings and closes the dialog window.
        """

        self._send_settings(self._init_settings)
        self.close()

    @pyqtSlot()
    def increase_threshold(self) -> None:
        """
        Slot increases the threshold value by a given step.
        """

        self._update_threshold_in_settings_wnd(self._get_threshold_value() + SettingsWindow.THRESHOLD_STEP)
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
                ut.show_message(qApp.translate("settings", "Ошибка"), f"{exc}\n{error_message}")
                return

            self._settings_directory = os.path.dirname(settings_path)
            self._settings = settings
            self._update_threshold_in_settings_wnd(self._settings.score_threshold)
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
            self._settings.score_threshold = self._get_threshold_value()
            self._settings.export(path=settings_path)

    @pyqtSlot(int)
    def update_threshold(self, new_value: int) -> None:
        """
        :param new_value: new threshold value.
        """

        self._update_threshold_in_settings_wnd(new_value / 100)
        self._send_settings()
