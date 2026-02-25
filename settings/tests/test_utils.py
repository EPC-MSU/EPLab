import os
import unittest
from PyQt5.QtCore import QSettings
from settings import utils as ut


class TestUtils(unittest.TestCase):

    def setUp(self) -> None:
        path = os.path.join(os.curdir, "settings", "tests", "test_data", "settings.ini")
        self.settings: QSettings = QSettings(path, QSettings.IniFormat)

    def test_float_to_str(self) -> None:
        self.assertEqual(ut.float_to_str(67.3244), "67.324")
        self.assertEqual(ut.float_to_str(-23), "-23")
        self.assertEqual(ut.float_to_str(0.0023), "0.002")

    def test_get_parameter(self) -> None:
        self.settings.setValue("parameter_1", 56)
        self.assertEqual(ut.get_parameter(self.settings, "parameter_1", int), 56)

        self.settings.setValue("parameter_2", "wefkwj")
        self.assertEqual(ut.get_parameter(self.settings, "parameter_2", int, default=78), 78)

        self.assertEqual(ut.get_parameter(self.settings, "parameter_4", default=69), 69)

    def test_set_parameter(self) -> None:
        ut.set_parameter(self.settings, "parameter_5", 67)
        self.assertEqual(self.settings.value("parameter_5"), 67)

    def test_to_bool(self) -> None:
        self.assertTrue(ut.to_bool(True))
        self.assertFalse(ut.to_bool("false"))
        self.assertTrue(ut.to_bool(78))
