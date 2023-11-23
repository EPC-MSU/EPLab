import sys
import unittest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication
from window.pedalhandler import PedalHandler


class TestPedalHandler(unittest.TestCase):

    def _handle_pedal(self, pressed: bool) -> None:
        """
        :param pressed: if True, then the pedal is pressed.
        """

        if pressed:
            self._pressed_number += 1
        else:
            self._released_number += 1

    def setUp(self) -> None:
        self._app: QApplication = QApplication(sys.argv[1:])
        self._pressed_number: int = 0
        self._released_number: int = 0

    def tearDown(self) -> None:
        pass

    def test_pedal_handler(self) -> None:
        """
        Test tests that the handler correctly determines the number of pedal presses.
        """

        press_and_release_events = []
        for status in (QKeyEvent.KeyPress, QKeyEvent.KeyRelease):
            for key in (Qt.Key_Alt, Qt.Key_Control, Qt.Key_Shift, Qt.Key_P):
                press_and_release_events.append(QKeyEvent(status, key, Qt.NoModifier))

        number_of_presses = 6
        events = press_and_release_events * number_of_presses

        pedal_handler = PedalHandler()
        pedal_handler.pedal_signal.connect(self._handle_pedal)
        for event in events:
            pedal_handler.handle_key_event(event)

        self.assertEqual(self._pressed_number, number_of_presses)
        self.assertEqual(self._released_number, number_of_presses)
