import os
from collections import namedtuple
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QDialog, QFileDialog, QGridLayout, QLabel, QLayout, QToolBar
import utils as ut

PanelParameters = namedtuple(
    "PanelParameters",
    (
        "probe_signal_frequency",
        "max_voltage",
        "current",
        "voltage",
        "sensity",
        "score"
    )
)


class LowSettingsPanel:
    """
    Class for plot parameters on the low panel at GUI.
    """

    def __init__(self, window):
        """
        :param window: main window.
        """

        self._param_dict = {"Напряжение": QLabel(window),
                            "Ампл. проб. сигнала": QLabel(window),
                            "Частота": QLabel(window),
                            "Ток": QLabel(window),
                            "Чувствительность": QLabel(window),
                            "Различие": QLabel(window)}
        window.grid_param = QGridLayout()
        positions = [(i, j) for i in range(2) for j in range(3)]
        for position, name in zip(positions, self._param_dict.keys()):
            tb = QToolBar()
            tb.setFixedHeight(30)
            tb.setStyleSheet("background:black; color:white;spacing:10;")
            tb.addWidget(self._param_dict[name])
            window.grid_param.addWidget(tb, *position)

    def set_all_parameters(self, **kwargs):
        """
        Method sets all parameters on the low panel.
        :param kwargs: dictionary of parameters relevant to PanelParameters.
        """

        params = PanelParameters(**kwargs)
        self.set_voltage_per_division(params.voltage)
        self.set_voltage_amplitude(params.max_voltage)
        self.set_probe_frequency(params.probe_signal_frequency)
        self.set_current_per_division(params.current)
        self.set_sensitivity(params.sensity)
        self.set_score(params.score)

    def set_current_per_division(self, current: float):
        self._param_dict["Ток"].setText(qApp.translate("t", "  Ток: ") + str(current) +
                                        qApp.translate("t", " мА / дел."))

    def set_probe_frequency(self, probe_frequency: int):
        self._param_dict["Частота"].setText(qApp.translate("t", "Частота: ") + str(probe_frequency) +
                                            qApp.translate("t", " Гц"))

    def set_score(self, score: str):
        self._param_dict["Различие"].setText(qApp.translate("t", "Различие: ") + score)

    def set_sensitivity(self, sensitivity: str):
        self._param_dict["Чувствительность"].setText(qApp.translate("t", "Чувствительность: ") + sensitivity)

    def set_voltage_amplitude(self, max_voltage: float):
        self._param_dict["Ампл. проб. сигнала"].setText(
            qApp.translate("t", "Ампл. проб. сигнала: ") + str(max_voltage) + qApp.translate("t", " B"))

    def set_voltage_per_division(self, voltage: float):
        self._param_dict["Напряжение"].setText(qApp.translate("t", "  Напряжение: ") +
                                               str(voltage) + qApp.translate("t", " В / дел."))


class SettingsWindow(QDialog):
    """
    Class for dialog window with measurement settings.
    """

    def __init__(self, parent=None, threshold: float = None, settings_directory: str = None):
        """
        :param parent: parent window;
        :param threshold: score threshold;
        :param settings_directory: directory for settings file.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uic.loadUi(os.path.join(dir_name, "gui", "settings.ui"), self)
        self.parent = parent
        self.settings_directory: str = settings_directory if settings_directory else ut.get_dir_name()
        self.layout().setSizeConstraint(QLayout.SetFixedSize)
        self.score_treshold_button_minus.clicked.connect(self.decrease_threshold)
        self.score_treshold_button_plus.clicked.connect(self.increase_threshold)
        validator = QRegExpValidator(QRegExp(r"^(\d|\d\d|100)%?"), self)
        self.score_treshold_value_line_edit.setValidator(validator)
        if threshold is not None:
            self._update_threshold_in_settings_wnd(threshold)
        self.apply_settings_push_button.clicked.connect(self.apply_settings)
        self.load_settings_push_button.clicked.connect(self.open_settings)
        self.save_settings_push_button.clicked.connect(self.save_settings_to_file)
        self.cancel_push_button.clicked.connect(self.close)

    def _get_threshold_value(self) -> float:
        """
        Method returns value of score threshold from in settings window.
        :return: score threshold value.
        """

        value = self.score_treshold_value_line_edit.text()
        if not value:
            value = 0
        elif value[-1] == "%":
            value = value[:-1]
        return float(int(value) / 100.0)

    def _update_threshold_in_settings_wnd(self, threshold: float):
        """
        Method updates score threshold value in settings window.
        :param threshold: new score threshold value.
        """

        self.score_treshold_value_line_edit.setText(f"{round(threshold * 100.0)}%")

    @pyqtSlot()
    def apply_settings(self):
        """
        Slot is called when you click on 'Apply' button in settings window.
        """

        self.parent.apply_settings(self._get_threshold_value())

    @pyqtSlot()
    def decrease_threshold(self):
        """
        Slot is called when you click on the '-' button in settings window.
        """

        threshold = self._get_threshold_value()
        threshold_step = 0.05
        threshold = max(threshold - threshold_step, 0.0)
        self._update_threshold_in_settings_wnd(threshold)

    @pyqtSlot()
    def increase_threshold(self):
        """
        Slot is called when you click on the '+' button in settings window.
        """

        threshold = self._get_threshold_value()
        threshold_step = 0.05
        threshold = min(threshold + threshold_step, 1.0)
        self._update_threshold_in_settings_wnd(threshold)

    @pyqtSlot()
    def open_settings(self):
        """
        Slot is called when you click on the 'Load settings' button in
        settings window.
        """

        settings_path = QFileDialog.getOpenFileName(self, qApp.translate("t", "Открыть файл"), self.settings_directory,
                                                    "Ini file (*.ini);;All Files (*)")[0]
        if settings_path:
            self.settings_directory = os.path.dirname(settings_path)
            score_threshold = self.parent.open_settings_from_file(settings_path)
            self._update_threshold_in_settings_wnd(score_threshold)

    @pyqtSlot()
    def save_settings_to_file(self):
        """
        Slot is called when you click on the 'Save settings' button in
        settings window.
        """

        settings_path = QFileDialog.getSaveFileName(self, qApp.translate("t", "Сохранить файл"),
                                                    directory=os.path.join(self.settings_directory, "settings.ini"),
                                                    filter="Ini file (*.ini);;All Files (*)")[0]
        if settings_path:
            self.settings_directory = os.path.dirname(settings_path)
            if not settings_path.endswith(".ini"):
                settings_path += ".ini"
            settings = self.parent.get_settings(self._get_threshold_value())
            settings.export(path=settings_path)
