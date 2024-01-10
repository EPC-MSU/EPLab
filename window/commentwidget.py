from typing import Any, Callable, Optional
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QSize, Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QTableWidgetItem
from epcore.elements import Pin
from window.common import WorkMode
from window.pinindextableitem import PinIndexTableItem
from window.tablewidget import TableWidget


def disconnect_signal(func: Callable[..., Any]):
    """
    Decorator disconnects and reconnects the slot to the signal itemChanged.
    :param func: function to be decorated.
    """

    def wrapper(self, *args, **kwargs) -> Any:
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

    BAD_BRUSH: QBrush = QBrush(QColor(255, 129, 129))
    DEFAULT_WIDTH: int = 150
    GOOD_BRUSH: QBrush = QBrush(QColor(152, 251, 152))
    WHITE_BRUSH: QBrush = QBrush(QColor(255, 255, 255))

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__(main_window, ["№", qApp.translate("t", "Комментарий")])
        self._default_style_sheet: str = self.styleSheet()
        self._read_only: bool = False
        self.adjustSize()

    @property
    def read_only(self) -> bool:
        """
        :return:
        """

        return self._read_only

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

    def _change_row_color(self, index: int, pin: Pin) -> None:
        """
        Method sets the color of the row depending on the score value. If the pin to which the row corresponds has
        test and reference IV-curves, then the score is calculated. If score is not greater than the threshold, then
        the row is colored light green, otherwise pink.
        :param index: index of the pin;
        :param pin: pin.
        """

        reference, test, settings = pin.get_reference_and_test_measurements()
        if None not in (reference, test, settings):
            brush = CommentWidget.GOOD_BRUSH if self._main_window.check_good_score(reference.ivc, test.ivc, settings) \
                else CommentWidget.BAD_BRUSH
        else:
            brush = CommentWidget.WHITE_BRUSH
        for column in range(self.columnCount()):
            item = self.item(index, column)
            item.setBackground(brush)

    def _change_style_for_selected_row(self, index: Optional[int] = None) -> None:
        """
        :param index: index of selected row.
        """

        index = self.currentRow() if index is None else index
        item = self.item(index, 1)
        color = item.background().color().name()
        selected_style = ("QTableView::item:selected {"
                          f"background-color: {color};"
                          "border: 2px solid #0000CD;"
                          "color: black;}")
        selected_and_disabled_style = ("QTableView::item:selected:disabled {"
                                       f"background-color: {color};"
                                       "border: 1px solid #0000CD;"
                                       "color: gray;}")
        self.setStyleSheet(self._default_style_sheet + selected_style + selected_and_disabled_style)

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
            self._change_row_color(index, pin)
        self.select_row_for_current_pin()

    def _set_item_read_only(self, item: QTableWidgetItem) -> None:
        """
        :param item: set table widget item as editable or not editable.
        """

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

        item = self.item(index, 1)
        if item:
            pin.comment = item.text()

    def set_new_comment(self, index: int) -> None:
        """
        Method sets a new comment for a pin.
        :param index: index of the pin for which a comment needs to be specified.
        """

        pin = self._main_window.measurement_plan.get_pin_with_index(index)
        if self.rowCount() <= index:
            self._add_comment(index, pin.comment)
        else:
            self._update_comment(index, pin.comment)
        self._change_row_color(index, pin)

    def set_pin_as_current(self) -> None:
        super().set_pin_as_current()
        for model_index in self.selectedIndexes():
            self._change_style_for_selected_row(model_index.row())
            break

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

    def sizeHint(self) -> QSize:
        """
        :return: recommended size for the widget.
        """

        height = super().sizeHint().height()
        return QSize(CommentWidget.DEFAULT_WIDTH, height)

    def update_info(self) -> None:
        """
        Method updates information in a table with comments.
        """

        self._main_window.measurement_plan.add_callback_func_for_pin_changes(self.set_new_comment)
        self._fill_table()
