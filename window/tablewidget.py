from typing import Any, Callable, List, Optional
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem
from .pinindextableitem import PinIndexTableItem


def change_item_state(item: QTableWidgetItem, read_only: bool) -> None:
    """
    :param item: table widget item as editable or not editable;
    :param read_only: if True, then change the table widget item to an editable state, otherwise to a non-editable
    state.
    """

    item.setFlags(item.flags() ^ Qt.ItemIsEditable if read_only else item.flags() | Qt.ItemIsEditable)


def disconnect_item_signals(func: Callable[..., Any]):
    """
    The decorator disconnects and reconnects the itemChanged and itemSelectionChanged signals to the slots after
    executing the decorated function.
    :param func: function to be decorated.
    """

    def wrapper(self, *args, **kwargs) -> Any:
        try:
            self.itemChanged.disconnect()
        except Exception:
            pass

        try:
            self.itemSelectionChanged.disconnect()
        except Exception:
            pass

        result = func(self, *args, **kwargs)
        self.itemChanged.connect(self.handle_item_changed)
        self.itemSelectionChanged.connect(self.send_current_row_index)
        return result

    return wrapper


class TableWidget(QTableWidget):
    """
    Class for a table.
    """

    current_row_signal: pyqtSignal = pyqtSignal(int, bool)

    def __init__(self, main_window, headers: List[str]) -> None:
        """
        :param main_window: main window of application;
        :param headers: list with headers for table.
        """

        super().__init__()
        self._main_window = main_window
        self._init_ui(headers)

    @disconnect_item_signals
    def _clear_table(self) -> None:
        _ = [self.removeRow(row) for row in range(self.rowCount(), -1, -1)]
        self.clearContents()

    @staticmethod
    def _create_table_item(read_only: bool = True) -> QTableWidgetItem:
        """
        :param read_only: if True, then item will be non-editable.
        :return: new table item.
        """

        item = QTableWidgetItem()
        change_item_state(item, read_only)
        return item

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
        self.itemSelectionChanged.connect(self.send_current_row_index)

    @disconnect_item_signals
    def _remove_row(self, index: int) -> None:
        """
        :param index: index of the row to be deleted.
        """

        self.removeRow(index)

    @disconnect_item_signals
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

    @pyqtSlot(QTableWidgetItem)
    def handle_item_changed(self, item: QTableWidgetItem) -> None:
        """
        :param item: item whose data changed.
        """

    @disconnect_item_signals
    def select_row(self) -> None:
        """
        Method selects row in the table for current pin index.
        """

        index = self._main_window.measurement_plan.get_current_index()
        if index is not None:
            self.selectRow(index)

    @pyqtSlot()
    def send_current_row_index(self) -> None:
        """
        Slot sends a signal with the number of the table row that is activated.
        """

        pin_index = self.currentRow()
        self.current_row_signal.emit(pin_index, True)
