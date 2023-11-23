from typing import Dict, List
from PyQt5.QtWidgets import QAction


class CurveStates:
    """
    Class for saving the state of curves (frozen or unfrozen) when working with the pedal in comparison mode.
    """

    def __init__(self, *actions: QAction) -> None:
        """
        :param actions: menu items that correspond to freezing curves.
        """

        self._actions: List[QAction] = actions
        self._states: List[Dict[str, bool]] = []

    def restore_states(self) -> None:
        """
        Method restores the state of the curves before pressing the pedal.
        """

        for action, state in zip(self._actions, self._states):
            if state["enabled"]:
                action.setEnabled(True)
            if state["checked"] != action.isChecked():
                action.trigger()

    def store_states(self) -> None:
        self._states = [{"checked": action.isChecked(),
                         "enabled": action.isEnabled()} for action in self._actions]
