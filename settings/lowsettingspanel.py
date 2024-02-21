from typing import Dict, List
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtWidgets import QGridLayout, QLabel, QToolBar, QWidget
from settings.legendwidget import LegendWidget


class LowSettingsPanel(QWidget):
    """
    Class for plot parameters on the low panel at GUI.
    """

    HEIGHT: int = 30
    LEFT_MARGIN: int = 4

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._legends: Dict[str, LegendWidget] = dict()
        self._param_dict: Dict[str, QLabel] = dict()
        self._init_ui()

    def _init_legends(self) -> None:
        names = ["reference", "test", "current"]
        texts = [qApp.translate("settings", "Эталон"), qApp.translate("settings", "Тест"),
                 qApp.translate("settings", "Текущая")]
        colors = ["reference_signature.png", "test_signature.png", "current_signature.png"]
        row = 2
        for column, (name, text, color) in enumerate(zip(names, texts, colors)):
            legend = LegendWidget(text, color, LowSettingsPanel.LEFT_MARGIN)
            self._legends[name] = legend
            self.grid_layout.addWidget(legend, row, column)

    def _init_param_dict(self) -> None:
        labels = [["voltage_per_div", "max_voltage", "frequency"],
                  ["current_per_div", "sensitivity", "score"]]
        for row, row_labels in enumerate(labels):
            for column, name in enumerate(row_labels):
                label = QLabel()
                label.setContentsMargins(LowSettingsPanel.LEFT_MARGIN, 0, 0, 0)
                self._param_dict[name] = label

                tool_bar = QToolBar()
                tool_bar.setFixedHeight(LowSettingsPanel.HEIGHT)
                tool_bar.setStyleSheet("background-color: black; color: white; spacing: 10;")
                tool_bar.addWidget(label)
                tool_bar.setContentsMargins(0, 0, 0, 0)
                self.grid_layout.addWidget(tool_bar, row, column)

    def _init_ui(self) -> None:
        self.grid_layout: QGridLayout = QGridLayout()
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.grid_layout)
        self.setStyleSheet("background-color: red;")

        self._init_param_dict()
        self._init_legends()

    def _set_current_per_div(self, current_per_division: float) -> None:
        """
        :param current_per_division: current value per division.
        """

        self._param_dict["current_per_div"].setText(qApp.translate("settings", "Ток: ") + str(current_per_division) +
                                                    qApp.translate("settings", " мА / дел."))

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

        self._param_dict["frequency"].setText(qApp.translate("settings", "Частота: ") + str(round(probe_frequency, 1)) +
                                              qApp.translate("settings", " Гц"))

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

        self._param_dict["voltage_per_div"].setText(qApp.translate("settings", "Напряжение: ") +
                                                    str(voltage_per_division) + qApp.translate("settings", " В / дел."))

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
