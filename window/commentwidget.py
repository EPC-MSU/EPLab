from typing import Optional
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QEvent, QObject, Qt
from PyQt5.QtGui import QFocusEvent, QKeyEvent
from PyQt5.QtWidgets import QLineEdit, QTableWidgetItem
from window.common import WorkMode
from window.pinindextableitem import PinIndexTableItem
from window.tablewidget import TableWidget


def disconnect_signal(func):
    """
    Decorator disconnects and reconnects the slot to the signal itemChanged.
    :param func: function to be decorated.
    """

    def wrapper(self, *args, **kwargs):
        try:
            self.itemChanged.disconnect()
        except Exception:
            pass
        result = func(self, *args, **kwargs)
        self.itemChanged.connect(self.handle_item_changed)
        return result

    return wrapper


class CommentWidget(TableWidget):
    """
    Widget for working with comments to measurement plan pins.
    """

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__(main_window, ["№", qApp.translate("t", "Комментарий")])
        self._read_only: bool = False

    def _add_comment(self, index: int, comment: Optional[str] = None) -> None:
        """
        Method adds a new comment to the pin.
        :param index: index of the pin for which the comment needs to be added;
        :param comment: new comment.
        """

        self.insertRow(index)
        self.setItem(index, 0, PinIndexTableItem(index))

        item = QTableWidgetItem()
        item.setText(comment)
        self._set_item_read_only(item)
        self.setItem(index, 1, item)

    def _clear_table(self) -> None:
        self.disconnect_item_selection_changed_signal()
        _ = [self.removeRow(row) for row in range(self.rowCount(), -1, -1)]
        self.clearContents()
        self.connect_item_selection_changed_signal()

    @disconnect_signal
    def _fill_table(self) -> None:
        """
        Method fills in a table with comments for measurement plan pins.
        """

        self._clear_table()
        for index, pin in self._main_window.measurement_plan.all_pins_iterator():
            self._add_comment(index, pin.comment)
        self.select_row_for_current_pin()

    def _set_item_read_only(self, item: QTableWidgetItem) -> None:
        if self._read_only:
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        else:
            item.setFlags(item.flags() | Qt.ItemIsEditable)

    def _set_read_only(self) -> None:
        """
        Method switches widgets with comments to read-only state.
        """

        column = 1
        for row in range(self.rowCount()):
            item = self.item(row, column)
            self._set_item_read_only(item)

    def _update_comment(self, index: int, comment: str) -> None:
        """
        Method updates the comment of a pin in the table.
        :param index: index of the pin for which the comment needs to be updated;
        :param comment: new comment.
        """

        self.item(index, 1).setText(comment)

    @disconnect_signal
    def clear_table(self) -> None:
        """
        Method clears all information from table and removes all rows in table.
        """

        self._clear_table()
        self._read_only = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        :param obj: object for which event occurred;
        :param event: event.
        :return: True if event should be filtered out, otherwise - False.
        """

        if isinstance(event, QKeyEvent) and isinstance(obj, QLineEdit):
            key_event = QKeyEvent(event)
            key = key_event.key()
            key_type = key_event.type()
            if key in (Qt.Key_Right, Qt.Key_Left) and key_type == QKeyEvent.ShortcutOverride:
                obj.keyPressEvent(event)
            elif key not in (Qt.Key_Right, Qt.Key_Left) and key_type == QKeyEvent.KeyPress:
                obj.keyPressEvent(event)
            return True

        if isinstance(event, QFocusEvent) and isinstance(obj, QLineEdit):
            filter_event = QFocusEvent(event)
            if filter_event.type() == QFocusEvent.FocusIn:
                setattr(self, "is_focused", True)
            elif filter_event.type() == QFocusEvent.FocusOut:
                setattr(self, "is_focused", False)
        return False

    @pyqtSlot(QTableWidgetItem)
    def handle_item_changed(self, item: QTableWidgetItem) -> None:
        """
        :param item: item whose data changed.
        """

        pin_index = self.row(item)
        self.save_comment(pin_index)

    @pyqtSlot(int)
    def save_comment(self, index: int) -> None:
        """
        Slot saves comment to pin.
        :param index: pin index.
        """

        pin = self._main_window.measurement_plan.get_pin_with_index(index)
        if not pin:
            return

        pin.comment = self.item(index, 1).text()
        self._main_window.update_current_pin()

    def set_new_comment(self, index: int) -> None:
        """
        Method set a new comment for a pin.
        :param index: index of the pin for which a comment needs to be specified.
        """

        comment = self._main_window.measurement_plan.get_pin_with_index(index).comment
        if self.rowCount() <= index:
            self._add_comment(index, comment)
        else:
            self._update_comment(index, comment)

    @pyqtSlot(WorkMode)
    def set_work_mode(self, mode: WorkMode) -> None:
        """
        Slot sets widgets according to new work mode.
        :param mode: new work mode.
        """

        if mode is WorkMode.READ_PLAN:
            if not self._read_only:
                self._read_only = True
                self._set_read_only()
            self.setEnabled(True)
        else:
            if self._read_only:
                self._read_only = False
                self._set_read_only()
            self.setEnabled(mode in (WorkMode.TEST, WorkMode.WRITE))

    def update_info(self) -> None:
        """
        Method updates information in a table with comments.
        """

        self._main_window.measurement_plan.add_callback_func_for_pin_changes(self.set_new_comment)
        self._fill_table()
