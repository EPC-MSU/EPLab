from enum import auto, Enum
from typing import List
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QAbstractItemView, QTableWidget


class LeftRight(Enum):
    """
    Class to denote left and right.
    """

    LEFT = auto()
    RIGHT = auto()


class LeftRightRunnableTable(QTableWidget):

    DEFAULT_WIDTH: int = 20

    def __init__(self, main_window, headers: List[str]) -> None:
        """
        :param main_window: main window of application;
        :param headers:
        """

        super().__init__()
        self._dont_go_to_selected_pin: bool = False
        self._main_window = main_window
        self._standby_mode: bool = False
        self._init_ui(headers)

    def _init_ui(self, headers: List[str]) -> None:
        """
        :param headers:
        """

        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        header = self.horizontalHeader()
        header.setDefaultSectionSize(LeftRightRunnableTable.DEFAULT_WIDTH)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.horizontalHeader().setStretchLastSection(True)
        self.cellClicked.connect(self.set_point_as_current)
        self.itemSelectionChanged.connect(self.set_point_as_current)

    def connect_item_selection_changed_signal(self, callback_function=None) -> None:
        if not callback_function:
            callback_function = self.set_point_as_current
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

        column = self.currentColumn()
        row = self.currentRow()
        if direction == LeftRight.LEFT and column > 0:
            self.setFocus()
            self.setCurrentCell(row, column - 1)
        elif direction == LeftRight.LEFT and column == 0:
            if row > 0:
                row -= 1
                column = self.columnCount() - 1
            self.setFocus()
            self.setCurrentCell(row, column)
        elif direction == LeftRight.RIGHT and column < self.columnCount() - 1:
            self.setFocus()
            self.setCurrentCell(row, column + 1)
        elif direction == LeftRight.RIGHT and column == self.columnCount() - 1:
            if row < self.rowCount() - 1:
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
    def set_point_as_current(self) -> None:
        """
        Slot sets point activated on table as current.
        """

        if not self._dont_go_to_selected_pin or self._standby_mode:
            row_index = self.currentRow()
            self._main_window.go_to_selected_pin(row_index)
        elif self._dont_go_to_selected_pin:
            self._dont_go_to_selected_pin = False
