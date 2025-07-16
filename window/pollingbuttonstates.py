from typing import Dict, List
from epcore.ivmeasurer import IVMeasurerBase, IVMeasurerIVM, IVMeasurerVirtual
from PyQt5.QtCore import pyqtSignal, QObject


class PollingButtonStates(QObject):
    """
    Class for polling the states of buttons on probes.
    """

    button_pressed: pyqtSignal = pyqtSignal(str, bool)

    def __init__(self) -> None:
        super().__init__()
        self._buttons_pressed: List[str] = []
        self._buttons_released: List[str] = []
        self._buttons_states: List[Dict[str, int]] = []
        self._measurers: List[IVMeasurerBase] = []

    def delete_measurers(self) -> None:
        self._buttons_pressed.clear()
        self._buttons_released.clear()
        self._buttons_states.clear()
        self._measurers.clear()

    def poll_button_states(self) -> None:
        """
        Method queries the states of the buttons on all probes.
        """

        self._buttons_pressed = []
        self._buttons_released = []

        for i, measurer in enumerate(self._measurers):
            if isinstance(measurer, (IVMeasurerIVM, IVMeasurerVirtual)):
                gen_state, recv_state = measurer.get_button_states()

                if gen_state and not self._buttons_states[i]["gen"]:
                    self._buttons_pressed.append(f"button_{i}_gen")

                if recv_state and not self._buttons_states[i]["recv"]:
                    self._buttons_pressed.append(f"button_{i}_recv")

                if self._buttons_states[i]["gen"] and not gen_state:
                    self._buttons_released.append(f"button_{i}_gen")

                if self._buttons_states[i]["recv"] and not recv_state:
                    self._buttons_released.append(f"button_{i}_recv")

                self._buttons_states[i]["gen"] = gen_state
                self._buttons_states[i]["recv"] = recv_state

    def send_signals(self) -> None:
        """
        Method sends signals with the names of the pressed and released buttons. The method must be called after
        'poll_button_states' method.
        """

        for button_name in self._buttons_pressed:
            self.button_pressed.emit(button_name, True)

        for button_name in self._buttons_released:
            self.button_pressed.emit(button_name, False)

    def set_measurers(self, measurers: List[IVMeasurerBase]) -> None:
        """
        :param measurers: list of probes.
        """

        self._buttons_pressed = []
        self._buttons_released = []
        self._measurers = measurers

        for measurer in self._measurers:
            if isinstance(measurer, (IVMeasurerIVM, IVMeasurerVirtual)):
                gen_state, recv_state = measurer.get_button_states()
            else:
                gen_state, recv_state = 0, 0
            self._buttons_states.append({"gen": gen_state,
                                         "recv": recv_state})
