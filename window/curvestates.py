from typing import Dict, List, Set
from PyQt5.QtWidgets import QAction


class CurveStates:
    """
    Class for saving the state of curves (frozen or unfrozen) when working with the pedal or buttons on the probes in
    comparison mode.
    """

    def __init__(self, *actions: QAction) -> None:
        """
        :param actions: menu items that correspond to freezing curves.
        """

        self._actions: List[QAction] = actions
        self._button_or_pedal_pressed: Set[str] = set()
        self._states: List[Dict[str, bool]] = []

    def restore_states(self, source: str) -> None:
        """
        Method restores the state of the curves before pressing the pedal or buttons.
        :param source: the name of the object (pedal or button) that was released.
        """

        self._button_or_pedal_pressed.remove(source)
        if not self._button_or_pedal_pressed:
            for action, state in zip(self._actions, self._states):
                if state["enabled"]:
                    action.setEnabled(True)
                if state["checked"] != action.isChecked():
                    action.trigger()

    def store_states(self, source: str) -> None:
        """
        :param source: the name of the object (pedal or button) that was pressed.
        """

        if not self._button_or_pedal_pressed:
            self._states = [{"checked": action.isChecked(),
                             "enabled": action.isEnabled()} for action in self._actions]

        self._button_or_pedal_pressed.add(source)
