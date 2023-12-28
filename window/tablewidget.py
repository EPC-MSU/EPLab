from typing import Any, Callable, List
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget


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
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
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

    def select_row_for_current_pin(self) -> None:
        """
        Method selects row in table for current pin index.
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
