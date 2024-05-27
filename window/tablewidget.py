from typing import Any, Callable, List, Optional
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget
from .pinindextableitem import PinIndexTableItem


class TableWidget(QTableWidget):
    """
    Class for a table.
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
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        horizontal_header = self.horizontalHeader()
        horizontal_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        horizontal_header.setStretchLastSection(True)
        vertical_header = self.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.itemSelectionChanged.connect(self.set_pin_as_current)

    def _remove_row(self, index: int) -> None:
        """
        :param index: index of the row to be deleted.
        """

        self._dont_go_to_selected_pin = True
        self.removeRow(index)

    def _update_indexes(self, start_row: Optional[int] = 0) -> None:
        """
        Method updates row indexes in the table.
        :param start_row: row number in the table, starting from which to update the row indexes.
        """

        if start_row is None:
            start_row = 0
        column = 0
        for row in range(start_row, self.rowCount()):
            item = self.item(row, column)
            if isinstance(item, PinIndexTableItem):
                item.set_index(row)

    def connect_item_selection_changed_signal(self, callback_function: Callable[..., Any] = None) -> None:
        """
        :param callback_function: callback function that should be called when the selected item changes.
        """

        if not callback_function:
            callback_function = self.set_pin_as_current
        self.itemSelectionChanged.connect(callback_function)

    def disconnect_item_selection_changed_signal(self) -> None:
        try:
            self.itemSelectionChanged.disconnect()
        except Exception:
            pass

    def select_row_for_current_pin(self) -> None:
        """
        Method selects row in the table for current pin index.
        """

        index = self._main_window.measurement_plan.get_current_index()
        if index is not None and index != self.currentRow():
            self._dont_go_to_selected_pin = True
            self.selectRow(index)

    @pyqtSlot()
    def set_pin_as_current(self) -> None:
        """
        Slot sets the pin activated on the table as current.
        """

        if not self._dont_go_to_selected_pin:
            pin_index = self.currentRow()
            self._main_window.go_to_selected_pin(pin_index)
        else:
            self._dont_go_to_selected_pin = False
