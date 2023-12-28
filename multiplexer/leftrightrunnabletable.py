from enum import auto, Enum
from typing import Any, Callable, List
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget


class LeftRight(Enum):
    """
    Class to denote left and right.
    """

    LEFT = auto()
    RIGHT = auto()


class LeftRightRunnableTable(QTableWidget):
    """
    Class for a table in which you can continuously move between cells using the Left and Right keys.
    """

    def __init__(self, main_window, headers: List[str]) -> None:
        """
        :param main_window: main window of application;
        :param headers: list with headers for table.
        """

        super().__init__()
        self._dont_go_to_selected_pin: bool = False
        self._main_window = main_window
        self._init_ui(headers)

    def _init_ui(self, headers: List[str]) -> None:
        """
        :param headers: list with headers for table.
        """

        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)

        self.cellClicked.connect(self.set_pin_as_current)
        self.itemSelectionChanged.connect(self.set_pin_as_current)

    def connect_item_selection_changed_signal(self, callback_function: Callable[..., Any] = None) -> None:
        """
        :param callback_function:
        """

        if not callback_function:
            callback_function = self.set_pin_as_current
        self.itemSelectionChanged.connect(callback_function)

    def disconnect_item_selection_changed_signal(self) -> None:
        try:
            self.itemSelectionChanged.disconnect()
        except Exception:
            pass

    def keyPressEvent(self, key_press_event: QKeyEvent) -> None:
        """
        Method performs additional processing of pressing left key on keyboard.
        :param key_press_event: key press event.
        """

        super().keyPressEvent(key_press_event)
        if key_press_event.key() == Qt.Key_Left and self.currentColumn() == 0:
            self.move_left_or_right(LeftRight.LEFT)

    @pyqtSlot(LeftRight)
    def move_left_or_right(self, direction: LeftRight) -> None:
        """
        Slot moves focus in table between columns.
        :param direction: left or right direction in which to move focus.
        """

        print(direction)
        column = self.currentColumn()
        row = self.currentRow()
        if direction == LeftRight.LEFT:
            if column > 0:
                column -= 1
            elif column == 0 and row > 0:
                row -= 1
                column = self.columnCount() - 1
        elif direction == LeftRight.RIGHT:
            if column < self.columnCount() - 1:
                column += 1
            elif column == self.columnCount() - 1 and row < self.rowCount() - 1:
                row += 1
                column = 0
        self.setFocus()
        self.setCurrentCell(row, column)

    def select_row_for_current_point(self) -> None:
        """
        Method selects row in table for current point index.
        """

        index = self._main_window.measurement_plan.get_current_index()
        if index != self.currentRow():
            self._dont_go_to_selected_pin = True
            self.selectRow(index)

    @pyqtSlot()
    def set_pin_as_current(self) -> None:
        """
        Slot sets pin activated on table as current.
        """

        if not self._dont_go_to_selected_pin:
            pin_index = self.currentRow()
            self._main_window.go_to_selected_pin(pin_index)
        else:
            self._dont_go_to_selected_pin = False
