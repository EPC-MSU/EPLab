import copy
import os
import unittest
from typing import Any, Dict
from settings import Settings
from window.common import WorkMode


class TestSettings(unittest.TestCase):

    def setUp(self) -> None:
        self.dir_test: str = os.path.join(os.curdir, "settings", "tests", "test_data")
        self.correct_result: Dict[str, Any] = {"frequency": (100, 10000),
                                               "hide_curve_a": True,
                                               "hide_curve_b": False,
                                               "internal_resistance": 47500,
                                               "max_voltage": 3.3,
                                               "score_threshold": 0.69,
                                               "sound_enabled": True,
                                               "work_mode": WorkMode.TEST}
        self.settings: Settings = Settings()
        _ = [setattr(self.settings, key, value) for key, value in self.correct_result.items()]

    def test_copy(self) -> None:
        other_settings = copy.copy(self.settings)
        other_settings.score_threshold = 0.96
        self.assertNotEqual(other_settings.score_threshold, self.settings.score_threshold)
        for attr_name in Settings.ATTRIBUTE_NAMES:
            if attr_name != "score_threshold":
                self.assertEqual(getattr(other_settings, attr_name), getattr(self.settings, attr_name))

    def test_read(self) -> None:
        settings = Settings()
        settings.read(path=os.path.join(self.dir_test, "test_settings.ini"))
        result = settings.get_values()
        for key, value in self.correct_result.items():
            self.assertEqual(value, result[key])

    def test_set_default_values(self) -> None:
        init_settings = Settings()
        init_settings.frequency = 56, 239
        init_settings.hide_curve_a = False
        init_settings.hide_curve_b = True
        init_settings.internal_resistance = 672.4
        init_settings.max_voltage = 32.43
        init_settings.score_threshold = 0.23
        init_settings.sound_enabled = False
        init_settings.work_mode = WorkMode.WRITE

        settings = Settings()
        settings.set_default_values(**self.correct_result)
        default_values = settings.get_default_values()
        for key, value in self.correct_result.items():
            self.assertEqual(value, default_values[key])

    def test_write(self) -> None:
        config_path = os.path.join(self.dir_test, "settings.ini")
        self.settings.write(path=config_path)
        self.assertTrue(os.path.exists(config_path))

        settings = Settings()
        settings.read(path=config_path)
        result = settings.get_values()
        for key, value in self.correct_result.items():
            self.assertEqual(value, result[key])
