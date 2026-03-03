import sys
import unittest
from PyQt5.QtWidgets import QApplication
from settings import LowSettingsPanel


class TestLowSettingsPanel(unittest.TestCase):

    def setUp(self) -> None:
        self.app: QApplication = QApplication(sys.argv[1:])

    def test_set_all_parameters(self) -> None:
        data = {"current_per_div": 2.32,
                "frequency": 78342.37,
                "max_voltage": 34.234,
                "score": "67%",
                "sensitivity": "Middle",
                "voltage_per_div": 1.23}
        correct_result = {"current_per_div": "Ток: 2.32 мА / дел.",
                          "frequency": "Частота: 78342.4 Гц",
                          "max_voltage": "Ампл. проб. сигнала: 34.2 В",
                          "score": "Различие: 67%",
                          "sensitivity": "Чувствительность: Middle",
                          "voltage_per_div": "Напряжение: 1.23 В / дел."}
        panel = LowSettingsPanel()
        panel.set_all_parameters(**data)
        for label_name, value in correct_result.items():
            label = panel._param_dict[label_name]
            self.assertEqual(label.text(), value)

    def test_set_legend(self) -> None:
        data = {"current": False,
                "reference": True,
                "test": True}
        panel = LowSettingsPanel()
        panel.set_all_parameters(**data)
        for curve_name, value in data.items():
            legend_widget = panel._legends[curve_name]
            self.assertEqual(legend_widget.label_status.text() == "☑", value)
