from typing import Dict, Generator
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget
from window import utils as ut
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
            legend = LegendWidget(text, color, self.LEFT_MARGIN)
            self._legends[name] = legend
            self._layout.addWidget(legend)

    def _init_param_dict(self) -> None:
        for param_name in ("voltage_per_div", "current_per_div", "max_voltage", "sensitivity", "frequency", "score"):
            label = QLabel()
            label.setContentsMargins(self.LEFT_MARGIN, 0, 0, 0)
            label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 128);")
            self._param_dict[param_name] = label
            self._layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft)

    def _init_ui(self) -> None:
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._layout: QVBoxLayout = QVBoxLayout()
        self._layout.setSpacing(2)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        self._init_param_dict()
        self._init_legends()

    def _set_current_per_div(self, current_per_division: float) -> None:
        """
        :param current_per_division: current value per division.
        """

        current_per_division *= 1e-3
        text = ut.get_str_representation_of_physical_quantity(qApp.translate("settings", "Ток"), current_per_division,
                                                              qApp.translate("settings", "А / дел."))
        self._param_dict["current_per_div"].setText(text)

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

        text = ut.get_str_representation_of_physical_quantity(qApp.translate("mux", "Частота"), probe_frequency,
                                                              qApp.translate("settings", "Гц"))
        self._param_dict["frequency"].setText(text)

    def _set_score(self, score: str) -> None:
        """
        :param score: score value.
        """

        score_text = "{}: {}".format(qApp.translate("MainWindow", "Различие"), score)
        self._param_dict["score"].setText(score_text)

    def _set_sensitivity(self, sensitivity: str) -> None:
        """
        :param sensitivity: current sensitivity value.
        """

        sens_text = "{}: {}".format(qApp.translate("mux", "Чувствительность"), sensitivity)
        self._param_dict["sensitivity"].setText(sens_text)

    def _set_voltage_per_div(self, voltage_per_division: float) -> None:
        """
        :param voltage_per_division: voltage value per division.
        """

        text = ut.get_str_representation_of_physical_quantity(qApp.translate("mux", "Напряжение"), voltage_per_division,
                                                              qApp.translate("settings", "В / дел."))
        self._param_dict["voltage_per_div"].setText(text)

    def clear_panel(self) -> None:
        _ = [label.clear() for label in self._param_dict.values()]
        _ = [legend.clear() for legend in self._legends.values()]

    def get_labels(self) -> Generator[QLabel, None, None]:
        """
        :yield: QLabel widgets with parameters.
        """

        for label in self._param_dict.values():
            yield label

    def set_all_parameters(self, **kwargs) -> None:
        """
        Method sets all parameters on the low panel.
        :param kwargs: keyword arguments with all parameters that are displayed on the settings panel.
        """

        for key, value in kwargs.items():
            method = getattr(self, f"_set_{key}", None)
            if method:
                method(value)

        self._set_legend(**kwargs)
