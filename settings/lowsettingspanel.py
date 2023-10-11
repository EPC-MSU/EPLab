from typing import Dict, List
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtWidgets import QGridLayout, QLabel, QToolBar


class LowSettingsPanel(QGridLayout):
    """
    Class for plot parameters on the low panel at GUI.
    """

    LABELS: List[str] = ["Напряжение", "Ампл. проб. сигнала", "Частота", "Ток", "Чувствительность", "Различие"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._param_dict: Dict[str, QLabel] = dict()
        positions = [(i, j) for i in range(2) for j in range(3)]
        for position, name in zip(positions, LowSettingsPanel.LABELS):
            label = QLabel(parent)
            self._param_dict[name] = label
            tool_bar = QToolBar()
            tool_bar.setFixedHeight(30)
            tool_bar.setStyleSheet("background:black; color:white;spacing:10;")
            tool_bar.addWidget(label)
            self.addWidget(tool_bar, *position)

    def _set_current_per_division(self, current_per_division: float) -> None:
        """
        :param current_per_division: current value per division.
        """

        self._param_dict["Ток"].setText(qApp.translate("t", "  Ток: ") + str(current_per_division) +
                                        qApp.translate("t", " мА / дел."))

    def _set_max_voltage(self, max_voltage: float) -> None:
        """
        :param max_voltage: voltage amplitude.
        """

        self._param_dict["Ампл. проб. сигнала"].setText(qApp.translate("t", "Ампл. проб. сигнала: ") +
                                                        str(round(max_voltage, 1)) + qApp.translate("t", " В"))

    def _set_probe_signal_frequency(self, probe_frequency: float) -> None:
        """
        :param probe_frequency: probe signal frequency value.
        """

        self._param_dict["Частота"].setText(qApp.translate("t", "Частота: ") + str(round(probe_frequency, 1)) +
                                            qApp.translate("t", " Гц"))

    def _set_score(self, score: str) -> None:
        """
        :param score: score value.
        """

        self._param_dict["Различие"].setText(qApp.translate("t", "Различие: ") + score)

    def _set_sensitivity(self, sensitivity: str) -> None:
        """
        :param sensitivity: current sensitivity value.
        """

        self._param_dict["Чувствительность"].setText(qApp.translate("t", "Чувствительность: ") + sensitivity)

    def _set_voltage_per_division(self, voltage_per_division: float) -> None:
        """
        :param voltage_per_division: voltage value per division.
        """
        self._param_dict["Напряжение"].setText(qApp.translate("t", "  Напряжение: ") +
                                               str(voltage_per_division) + qApp.translate("t", " В / дел."))

    def set_all_parameters(self, **kwargs) -> None:
        """
        Method sets all parameters on the low panel.
        :param kwargs: dictionary with all parameters that are displayed on the low panel.
        """

        for key, value in kwargs.items():
            method = getattr(self, f"_set_{key}", None)
            if method:
                method(value)
