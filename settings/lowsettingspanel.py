from collections import namedtuple
from typing import Dict, Union
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtWidgets import QGridLayout, QLabel, QToolBar
from settings import utils as ut


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

    def __init__(self, window) -> None:
        """
        :param window: main window.
        """

        self._param_dict: Dict[str, QLabel] = {"Напряжение": QLabel(window),
                                               "Ампл. проб. сигнала": QLabel(window),
                                               "Частота": QLabel(window),
                                               "Ток": QLabel(window),
                                               "Чувствительность": QLabel(window),
                                               "Различие": QLabel(window)}
        window.grid_param = QGridLayout()
        positions = [(i, j) for i in range(2) for j in range(3)]
        for position, name in zip(positions, self._param_dict.keys()):
            tool_bar = QToolBar()
            tool_bar.setFixedHeight(30)
            tool_bar.setStyleSheet("background:black; color:white;spacing:10;")
            tool_bar.addWidget(self._param_dict[name])
            window.grid_param.addWidget(tool_bar, *position)

    def _set_current_per_division(self, current: float) -> None:
        self._param_dict["Ток"].setText(qApp.translate("t", "  Ток: ") + str(current) +
                                        qApp.translate("t", " мА / дел."))

    def _set_probe_frequency(self, probe_frequency: int) -> None:
        self._param_dict["Частота"].setText(qApp.translate("t", "Частота: ") + str(probe_frequency) +
                                            qApp.translate("t", " Гц"))

    def _set_score(self, score: Union[float, str]) -> None:
        if isinstance(score, float):
            score = ut.float_to_str(score)
        self._param_dict["Различие"].setText(qApp.translate("t", "Различие: ") + score)

    def _set_sensitivity(self, sensitivity: str) -> None:
        self._param_dict["Чувствительность"].setText(qApp.translate("t", "Чувствительность: ") + sensitivity)

    def _set_voltage_amplitude(self, max_voltage: float) -> None:
        self._param_dict["Ампл. проб. сигнала"].setText(qApp.translate("t", "Ампл. проб. сигнала: ") +
                                                        str(max_voltage) + qApp.translate("t", " B"))

    def _set_voltage_per_division(self, voltage: float) -> None:
        self._param_dict["Напряжение"].setText(qApp.translate("t", "  Напряжение: ") +
                                               str(voltage) + qApp.translate("t", " В / дел."))

    def set_all_parameters(self, **kwargs) -> None:
        """
        Method sets all parameters on the low panel.
        :param kwargs: dictionary of parameters relevant to PanelParameters.
        """

        params = PanelParameters(**kwargs)
        self._set_voltage_per_division(params.voltage)
        self._set_voltage_amplitude(params.max_voltage)
        self._set_probe_frequency(params.probe_signal_frequency)
        self._set_current_per_division(params.current)
        self._set_sensitivity(params.sensity)
        self._set_score(params.score)
