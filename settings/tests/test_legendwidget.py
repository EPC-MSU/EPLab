import sys
import unittest
from PyQt5.QtWidgets import QApplication
from settings.legendwidget import LegendWidget


class TestLegendWidget(unittest.TestCase):

    def setUp(self) -> None:
        self.app: QApplication = QApplication(sys.argv[1:])
        self.widget: LegendWidget = LegendWidget("Test", "test_signature", 5)

    def test_clear(self) -> None:
        self.widget.clear()
        self.assertFalse(self.widget.isVisible())

    def test_set_active(self) -> None:
        self.widget.set_active()
        self.assertTrue(self.widget.isVisible())
        self.assertEqual(self.widget.label_status.text(), "☑")

    def test_set_inactive(self) -> None:
        self.widget.set_inactive()
        self.assertTrue(self.widget.isVisible())
        self.assertEqual(self.widget.label_status.text(), "N/A")
