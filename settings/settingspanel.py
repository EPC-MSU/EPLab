from typing import Dict, List, Tuple
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtWidgets import QLabel, QToolBar, QVBoxLayout, QWidget
from .legendwidget import LegendWidget


class SettingsPanel(QWidget):
    """
    Widget for displaying current settings.
    """

    LEFT_MARGIN: int = 4

    def __init__(self, parent=None) -> None:
        """
        :param parent: parent widget.
        """

        super().__init__(parent)
        self._legends: Dict[str, LegendWidget] = dict()
        self._param_dict: Dict[str, QLabel] = dict()
        self._init_ui()

    def _init_legends(self) -> None:
        names = "reference", "test", "current"
        texts = (qApp.translate("settings", "Эталон"), qApp.translate("settings", "Тест"),
                 qApp.translate("settings", "Текущая"))
        colors = "reference_signature.png", "test_signature.png", "current_signature.png"
        for name, text, color in zip(names, texts, colors):
            legend = LegendWidget(text, color, SettingsPanel.LEFT_MARGIN)
            self._legends[name] = legend
            self._layout.addWidget(legend)

    def _init_param_dict(self) -> None:
        for param_name in ("voltage_per_div", "current_per_div", "max_voltage", "sensitivity", "frequency", "score"):
            label = QLabel()
            label.setContentsMargins(SettingsPanel.LEFT_MARGIN, 0, 0, 0)
            self._param_dict[param_name] = label

            tool_bar = QToolBar()
            tool_bar.setStyleSheet("background-color: black; color: white;")
            tool_bar.addWidget(label)
            tool_bar.setContentsMargins(0, 0, 0, 0)
            self._layout.addWidget(tool_bar)

    def _init_ui(self) -> None:
        self._layout: QVBoxLayout = QVBoxLayout()
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)
        self.setStyleSheet("background-color: red;")

        self._init_param_dict()
        self._init_legends()

    def _set_current_per_div(self, current_per_division: float) -> None:
        """
        :param current_per_division: current value per division.
        """

        current_per_division *= 1e-3
        current_per_division, unit = convert_value_by_order(current_per_division)
        self._param_dict["current_per_div"].setText(qApp.translate("settings", "Ток: ") +
                                                    f"{current_per_division} {unit}" +
                                                    qApp.translate("settings", "А / дел."))

    def _set_legend(self, **kwargs) -> None:
        """
        :param kwargs:
        """

        for name, legend_widget in self._legends.items():
            value = kwargs.get(name, None)
            if value:
                legend_widget.set_active()
            else:
                legend_widget.set_inactive()

    def _set_max_voltage(self, max_voltage: float) -> None:
        """
        :param max_voltage: voltage amplitude.
        """

        self._param_dict["max_voltage"].setText(qApp.translate("settings", "Ампл. проб. сигнала: ") +
                                                str(round(max_voltage, 1)) + qApp.translate("settings", " В"))

    def _set_frequency(self, probe_frequency: float) -> None:
        """
        :param probe_frequency: probe signal frequency value.
        """

        frequency, unit = convert_value_by_order(probe_frequency)
        self._param_dict["frequency"].setText(qApp.translate("settings", "Частота: ") + f"{frequency} {unit}" +
                                              qApp.translate("settings", "Гц"))

    def _set_score(self, score: str) -> None:
        """
        :param score: score value.
        """

        self._param_dict["score"].setText(qApp.translate("settings", "Различие: ") + score)

    def _set_sensitivity(self, sensitivity: str) -> None:
        """
        :param sensitivity: current sensitivity value.
        """

        self._param_dict["sensitivity"].setText(qApp.translate("settings", "Чувствительность: ") + sensitivity)

    def _set_voltage_per_div(self, voltage_per_division: float) -> None:
        """
        :param voltage_per_division: voltage value per division.
        """

        voltage_per_division, unit = convert_value_by_order(voltage_per_division)
        self._param_dict["voltage_per_div"].setText(qApp.translate("settings", "Напряжение: ") +
                                                    f"{voltage_per_division} {unit}" +
                                                    qApp.translate("settings", "В / дел."))

    def clear_panel(self) -> None:
        _ = [label.clear() for label in self._param_dict.values()]
        _ = [legend.clear() for legend in self._legends.values()]

    def get_labels(self) -> List[QLabel]:
        for label in self._param_dict.values():
            yield label

    def set_all_parameters(self, **kwargs) -> None:
        """
        Method sets all parameters on the low panel.
        :param kwargs: dictionary with all parameters that are displayed on the low panel.
        """

        for key, value in kwargs.items():
            method = getattr(self, f"_set_{key}", None)
            if method:
                method(value)

        self._set_legend(**kwargs)


def convert_value_by_order(value: float) -> Tuple[float, str]:
    """
    :param value: number to be converted in order.
    :return: converted number and unit prefix.
    """

    value = abs(value)
    if value >= 10**3:
        value = round(value / 10**3, 2)
        unit = qApp.translate("settings", "к")
    elif 1 <= value < 10**3:
        value = round(value, 2)
        unit = ""
    elif 1e-3 <= value < 1:
        value = round(10**3 * value, 2)
        unit = qApp.translate("settings", "м")
    elif 1e-6 <= value < 1e-3:
        value = round(10**6 * value, 2)
        unit = qApp.translate("settings", "мк")
    elif 1e-9 <= value < 1e-6:
        value = round(10**9 * value, 2)
        unit = qApp.translate("settings", "н")
    else:
        value = round(10**12 * value, 2)
        unit = qApp.translate("settings", "п")
    return value, unit
