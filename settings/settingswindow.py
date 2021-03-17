from PyQt5.QtWidgets import QDialog, QLabel, QGridLayout, QToolBar
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
import os
from PyQt5 import uic
from collections import namedtuple

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
    Qdialog window, load settings.ui
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        uic.loadUi(os.path.join("gui", "settings.ui"), self)

        self.score_treshold_button_minus.clicked.connect(parent._on_threshold_dec)
        self.score_treshold_button_plus.clicked.connect(parent._on_threshold_inc)
        self.auto_calibration_push_button.clicked.connect(parent._on_auto_calibration)
        validator = QRegExpValidator(QRegExp(r"^(\d|\d\d)%?"), self)
        self.score_treshold_value_lineEdit.setValidator(validator)
        self.score_treshold_value_lineEdit.returnPressed.connect(parent._on_threshold_set_value)
        self.load_settings_push_button.clicked.connect(parent._on_open_settings)
        self.save_settings_push_button.clicked.connect(parent._save_settings_to_file)


class LowSettingsPanel:
    """
    Class plot parameters on the low panel at gui
    """
    def __init__(self, window):
        self._param_dict = {"Напряжение": QLabel(window), "Ампл. проб. сигнала": QLabel(window),
                            "Частота": QLabel(window),
                            "Ток": QLabel(window), "Чувствительность": QLabel(window), "Различие": QLabel(window)}
        window.grid_param = QGridLayout()
        positions = [(i, j) for i in range(2) for j in range(3)]
        for position, name in zip(positions, self._param_dict.keys()):
            tb = QToolBar()
            tb.setFixedHeight(30)
            tb.setStyleSheet("background:black; color:white;spacing:10;")
            tb.addWidget(self._param_dict[name])
            window.grid_param.addWidget(tb, *position)

    def set_volt(self, voltage: float):
        self._param_dict["Напряжение"].setText(qApp.translate("t", "  Напряжение: ") + str(voltage) +
                                               qApp.translate("t", " В / дел."))

    def set_v_ampl(self, max_v: float):
        self._param_dict["Ампл. проб. сигнала"].setText(qApp.translate("t", "Ампл. проб. сигнала: ") +
                                                        str(max_v) + qApp.translate("t", " B"))

    def set_probe_freq(self, probe_freq: int):
        self._param_dict["Частота"].setText(qApp.translate("t", "Частота: ") + str(probe_freq) +
                                            qApp.translate("t", " Гц"))

    def set_cur(self, current: float):
        self._param_dict["Ток"].setText(qApp.translate("t", "  Ток: ") + str(current) +
                                        qApp.translate("t", " мА / дел."))

    def set_sensity(self, sensity: str):
        self._param_dict["Чувствительность"].setText(qApp.translate("t", "Чувствительность: ") + sensity)

    def set_score(self, score: str):
        self._param_dict["Различие"].setText(qApp.translate("t", "Различие: ") + score)

    def set_all_parameters(self, **kwargs):
        """
        set all parameters on the low panel
        :param kwargs: dict of parameters, correspond PanelParameters
        :return:
        """
        s = PanelParameters(**kwargs)
        self.set_volt(s.voltage)
        self.set_v_ampl(s.max_voltage)
        self.set_probe_freq(s.probe_signal_frequency)
        self.set_cur(s.current)
        self.set_sensity(s.sensity)
        self.set_score(s.score)
