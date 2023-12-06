import sys
import unittest
from PyQt5.QtWidgets import QApplication
from window.pinindexwidget import PinIndexWidget


class TestPinIndexWidget(unittest.TestCase):

    def setUp(self) -> None:
        self._app: QApplication = QApplication(sys.argv[1:])

    def test_set_index(self) -> None:
        """
        Setting the index in programmatic format is tested.
        """

        pin_index_widget = PinIndexWidget()
        pin_index_widget.set_index(5)
        self.assertEqual(pin_index_widget.get_index(), 5)
        self.assertEqual(pin_index_widget.text(), "6")

    def test_set_user_index(self) -> None:
        """
        Setting the index in user format is tested.
        """

        pin_index_widget = PinIndexWidget()
        pin_index_widget.setText("89")
        self.assertEqual(pin_index_widget.get_index(), 88)
        self.assertEqual(pin_index_widget.text(), "89")
