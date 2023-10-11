import sys
import unittest
from PyQt5.QtWidgets import QApplication
from settings import LowSettingsPanel


class TestLowSettingsPanel(unittest.TestCase):

    def setUp(self) -> None:
        self.app = QApplication(sys.argv[1:])

    def test_set_all_parameters(self) -> None:
        data = {"current_per_division": 2.32,
                "max_voltage": 34.234,
                "probe_signal_frequency": 78342.37,
                "score": "67%",
                "sensitivity": "Middle",
                "voltage_per_division": 1.23}
        correct_result = {"Ток": "  Ток: 2.32 мА / дел.",
                          "Ампл. проб. сигнала": "Ампл. проб. сигнала: 34.2 В",
                          "Частота": "Частота: 78342.4 Гц",
                          "Различие": "Различие: 67%",
                          "Чувствительность": "Чувствительность: Middle",
                          "Напряжение": "  Напряжение: 1.23 В / дел."}
        panel = LowSettingsPanel()
        panel.set_all_parameters(**data)
        for label_name, value in correct_result.items():
            label = panel._param_dict[label_name]
            self.assertEqual(label.text(), value)
