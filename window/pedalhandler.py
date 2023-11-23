from enum import auto, Enum
from typing import Dict, List
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtGui import QKeyEvent


class PedalHandler(QObject):
    """
    A class for processing signals from a pedal and determining whether the pedal is pressed or released.
    """

    KEYS: List[int] = [Qt.Key_Alt, Qt.Key_Control, Qt.Key_Shift, Qt.Key_P]
    pedal_signal: pyqtSignal = pyqtSignal(bool)

    class Button:

        def __init__(self, key: int, status: bool = False) -> None:
            """
            :param key: button key;
            :param status: if True, then the button is pressed.
            """

            self._key: int = key
            self._status: bool = status

        @property
        def status(self) -> bool:
            """
            :return: if True, then the button is pressed.
            """

            return self._status

        @status.setter
        def status(self, new_state: int) -> None:
            """
            :param new_state: Qt state of button.
            """

            if new_state == QKeyEvent.KeyPress:
                self._status = True
            elif new_state == QKeyEvent.KeyRelease:
                self._status = False

    class Status(Enum):
        """
        Class for listing pedal statuses. If the pedal is pressed for a long time, the P button changes its state
        quickly from Pressed to Released. To catch this behavior, a POSSIBLE_RELEASED status is introduced.
        """

        POSSIBLE_RELEASED = auto()
        PRESSED = auto()
        RELEASED = auto()

    def __init__(self) -> None:
        super().__init__()
        self._buttons: Dict[int, PedalHandler.Button] = {key: PedalHandler.Button(key) for key in PedalHandler.KEYS}
        self._status: PedalHandler.Status = PedalHandler.Status.RELEASED

    def _check_buttons(self) -> None:
        all_pressed = all(button.status for button in self._buttons.values())
        control_buttons_pressed = all(self._buttons[key].status for key in (Qt.Key_Alt, Qt.Key_Control, Qt.Key_Shift))

        if control_buttons_pressed and not all_pressed:
            pass
        else:
            status = PedalHandler.Status.PRESSED if all_pressed else PedalHandler.Status.RELEASED
            if status != self._status:
                self.pedal_signal.emit(all_pressed)
                self._status = status

    def handle_key_event(self, event: QKeyEvent) -> None:
        """
        :param event: key press or release event.
        """

        key = event.key()
        if key in PedalHandler.KEYS:
            button = self._buttons[key]
            button.status = event.type()
        self._check_buttons()
