import os
from collections import namedtuple
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QDialog, QFileDialog, QGridLayout, QLabel, QLayout, QToolBar

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


class SettingsWindow(QDialog):
    """
    Class for dialog window with measurement settings.
    """

    def __init__(self, parent=None, threshold: float = None):
        """
        :param parent: parent window;
        :param threshold: score threshold.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uic.loadUi(os.path.join(dir_name, "gui", "settings.ui"), self)
        self.parent = parent
        self.layout().setSizeConstraint(QLayout.SetFixedSize)
        self.score_treshold_button_minus.clicked.connect(self._decrease_threshold)
        self.score_treshold_button_plus.clicked.connect(self._increase_threshold)
        validator = QRegExpValidator(QRegExp(r"^(\d|\d\d|100)%?"), self)
        self.score_treshold_value_lineEdit.setValidator(validator)
        if threshold is not None:
            self._update_threshold_in_settings_wnd(threshold)
        self.load_settings_push_button.clicked.connect(self._open_settings)
        self.save_settings_push_button.clicked.connect(self._save_settings_to_file)
        self.apply_settings_push_button.clicked.connect(self._apply_settings)
        self.cancel_push_button.clicked.connect(self.close)

    @pyqtSlot()
    def _apply_settings(self):
        """
        Slot is called when you click on 'Apply' button in settings window.
        """

        self.parent.apply_settings(self._get_threshold_value())

    @pyqtSlot()
    def _decrease_threshold(self):
        """
        Slot is called when you click on the '-' button in settings window.
        """

        threshold = self._get_threshold_value()
        threshold_step = 0.05
        threshold = max(threshold - threshold_step, 0.0)
        self._update_threshold_in_settings_wnd(threshold)

    def _get_threshold_value(self) -> float:
        """
        Method returns value of score threshold from in settings window.
        :return: score threshold value.
        """

        value = self.score_treshold_value_lineEdit.text()
        if not value:
            value = 0
        elif value[-1] == "%":
            value = value[:-1]
        return float(int(value) / 100.0)

    @pyqtSlot()
    def _increase_threshold(self):
        """
        Slot is called when you click on the '+' button in settings window.
        """

        threshold = self._get_threshold_value()
        threshold_step = 0.05
        threshold = min(threshold + threshold_step, 1.0)
        self._update_threshold_in_settings_wnd(threshold)

    @pyqtSlot()
    def _open_settings(self):
        """
        Slot is called when you click on the 'Load settings' button in
        settings window.
        """

        settings_path = QFileDialog.getOpenFileName(self, qApp.translate("t", "Открыть файл"), ".",
                                                    "Ini file (*.ini);;All Files (*)")[0]
        if settings_path:
            score_threshold = self.parent.open_settings_from_file(settings_path)
            self._update_threshold_in_settings_wnd(score_threshold)

    @pyqtSlot()
    def _save_settings_to_file(self):
        """
        Slot is called when you click on the 'Save settings' button in
        settings window.
        """

        settings_path = QFileDialog.getSaveFileName(
            self, qApp.translate("t", "Сохранить файл"), filter="Ini file (*.ini);;All Files (*)",
            directory="settings.ini")[0]
        if settings_path:
            if not settings_path.endswith(".ini"):
                settings_path += ".ini"
            settings = self.parent.get_settings(self._get_threshold_value())
            settings.export(path=settings_path)

    def _update_threshold_in_settings_wnd(self, threshold: float):
        """
        Method updates score threshold value in settings window.
        :param threshold: new score threshold value.
        """

        self.score_treshold_value_lineEdit.setText(f"{round(threshold * 100.0)}%")


class LowSettingsPanel:
    """
    Class for plot parameters on the low panel at GUI.
    """

    def __init__(self, window):
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

    def set_volt(self, voltage: float):
        self._param_dict["Напряжение"].setText(qApp.translate("t", "  Напряжение: ") +
                                               str(voltage) + qApp.translate("t", " В / дел."))

    def set_v_ampl(self, max_v: float):
        self._param_dict["Ампл. проб. сигнала"].setText(
            qApp.translate("t", "Ампл. проб. сигнала: ") + str(max_v) + qApp.translate("t", " B"))

    def set_probe_freq(self, probe_freq: int):
        self._param_dict["Частота"].setText(qApp.translate("t", "Частота: ") + str(probe_freq) +
                                            qApp.translate("t", " Гц"))

    def set_cur(self, current: float):
        self._param_dict["Ток"].setText(qApp.translate("t", "  Ток: ") + str(current) +
                                        qApp.translate("t", " мА / дел."))

    def set_sensity(self, sensity: str):
        self._param_dict["Чувствительность"].setText(qApp.translate("t", "Чувствительность: ") +
                                                     sensity)

    def set_score(self, score: str):
        self._param_dict["Различие"].setText(qApp.translate("t", "Различие: ") + score)

    def set_all_parameters(self, **kwargs):
        """
        Set all parameters on the low panel.
        :param kwargs: dict of parameters, correspond PanelParameters.
        """

        params = PanelParameters(**kwargs)
        self.set_volt(params.voltage)
        self.set_v_ampl(params.max_voltage)
        self.set_probe_freq(params.probe_signal_frequency)
        self.set_cur(params.current)
        self.set_sensity(params.sensity)
        self.set_score(params.score)
