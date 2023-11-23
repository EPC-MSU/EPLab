import unittest
from typing import List
from PyQt5.QtWidgets import QAction
from window.curvestates import CurveStates


class TestCurveStates(unittest.TestCase):

    def setUp(self) -> None:
        action_number = 10
        self._actions: List[QAction] = []
        for index in range(action_number):
            action = QAction(f"action_{index}")
            action.setCheckable(True)
            action.setChecked(bool(index % 2))
            self._actions.append(action)

    def test_restore_states(self) -> None:
        curve_states = CurveStates(*self._actions)
        curve_states.store_states()
        for action in self._actions:
            action.setChecked(True)
        curve_states.restore_states()

        for index, action in enumerate(self._actions):
            self.assertEqual(action.isChecked(), bool(index % 2))
