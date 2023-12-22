from typing import List, Optional
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from multiplexer.leftrightrunnabletable import LeftRightRunnableTable
from multiplexer.measurementplanwidget import LeftRight, ModifiedLineEdit
from multiplexer.pinindextableitem import PinIndexTableItem
from window.common import WorkMode


class CommentWidget(QWidget):
    """
    Widget for working with comments to measurement plan points.
    """

    HEADERS: List[str] = ["№", qApp.translate("comment", "Комментарий")]

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self._parent = main_window
        self._read_only: bool = False
        self._init_ui()

    def _init_ui(self) -> None:
        self.table_widget: LeftRightRunnableTable = LeftRightRunnableTable(self._parent, CommentWidget.HEADERS)
        self.v_layout: QVBoxLayout = QVBoxLayout()
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addWidget(self.table_widget)
        self.setLayout(self.v_layout)

    def _add_comment(self, index: int, comment: Optional[str] = None) -> None:
        """
        Method adds a new comment to the point.
        :param index: index of the point for which the comment needs to be added;
        :param comment: new comment.
        """

        self.table_widget.insertRow(index)
        self.table_widget.setItem(index, 0, PinIndexTableItem(index))

        line_edit = ModifiedLineEdit()
        line_edit.setReadOnly(self._read_only)
        line_edit.editingFinished.connect(lambda: self.save_comment(index))
        line_edit.left_pressed.connect(lambda: self.table_widget.move_left_or_right(LeftRight.LEFT))
        line_edit.right_pressed.connect(lambda: self.table_widget.move_left_or_right(LeftRight.RIGHT))
        line_edit.setText(comment)
        self.table_widget.setCellWidget(index, 1, line_edit)

    def _clear_table(self) -> None:
        self.table_widget.disconnect_item_selection_changed_signal()
        _ = [self.table_widget.removeRow(row) for row in range(self.table_widget.rowCount(), -1, -1)]
        self.table_widget.clearContents()
        self.table_widget.connect_item_selection_changed_signal()

    def _fill_table(self) -> None:
        """
        Method fills in a table with comments for measurement plan points.
        """

        self._clear_table()
        for index, point in self._parent.measurement_plan.all_pins_iterator():
            self._add_comment(index, point.comment)
        self.table_widget.select_row_for_current_point()

    def _set_read_only(self) -> None:
        """
        Method switches widgets with comments to read-only state.
        """

        column = 1
        for row in range(self.table_widget.rowCount()):
            widget = self.table_widget.cellWidget(row, column)
            widget.setReadOnly(self._read_only)

    def _update_comment(self, index: int, comment: str) -> None:
        """
        Method updates the comment of a point in the table.
        :param index: index of the point for which the comment needs to be updated;
        :param comment: new comment.
        """

        self.table_widget.cellWidget(index, 1).setText(comment)

    def clear_table(self) -> None:
        """
        Method clears all information from table and removes all rows in table.
        """

        self._clear_table()
        self._read_only = False

    @pyqtSlot(int)
    def save_comment(self, index: int) -> None:
        """
        Slot saves comment to point.
        :param index: point index.
        """

        point = self._parent.measurement_plan.get_pin_with_index(index)
        if not point:
            return

        point.comment = self.table_widget.cellWidget(index, 1).text()
        self._parent.update_current_pin()

    def select_current_point(self) -> None:
        """
        Method selects row in table for current point index.
        """

        self.table_widget.select_row_for_current_point()

    def set_new_comment(self, point_index: int) -> None:
        """
        Method set a new comment for a point.
        :param point_index: index of the point for which a comment needs to be specified.
        """

        comment = self._parent.measurement_plan.get_pin_with_index(point_index).comment
        if self.table_widget.rowCount() <= point_index:
            self._add_comment(point_index, comment)
        else:
            self._update_comment(point_index, comment)

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

        self._parent.measurement_plan.add_callback_func_for_pin_changes(self.set_new_comment)
        self._fill_table()
