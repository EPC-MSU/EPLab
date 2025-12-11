import logging
import os
from typing import Optional
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QModelIndex, QPoint, QRect, QSize, Qt
from PyQt5.QtGui import QBrush, QColor, QIcon, QKeySequence, QPainter, QPen
from PyQt5.QtWidgets import (QAction, QMenu, QShortcut, QStyle, QStyledItemDelegate, QStyleOptionViewItem,
                             QTableWidgetItem)
from epcore.elements import Pin
from . import utils as ut
from .common import WorkMode
from .pinindextableitem import PinIndexTableItem
from .tablewidget import change_item_state, disconnect_item_signals, TableWidget


logger = logging.getLogger("eplab")


class CommentTableDelegate(QStyledItemDelegate):
    """
    Class for rendering table cells with comments. Table cells change color depending on the match of the test
    signature with the reference one. In order for the selected table cells to have the same color as was specified
    when comparing signatures, you have to use this class.
    The class eliminates software freezes when working with large tables with comments #118225.
    """

    BORDER_COLOR_OF_SELECTED_CELL: QColor = QColor("#0000CD")
    BORDER_WIDTH_OF_SELECTED_CELL_DISABLED: int = 1
    BORDER_WIDTH_OF_SELECTED_CELL_ENABLED: int = 2
    PEN_COLOR_DISABLED: QColor = QColor(Qt.gray)
    PEN_COLOR_ENABLED: QColor = QColor(Qt.black)
    TEXT_PADDING: int = 2

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """
        :param painter: painter;
        :param option: style option for the item specified by index;
        :param index: index of the item to be drawn.
        """

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        if opt.state & QStyle.State_Selected:
            if opt.state & QStyle.State_Enabled:
                pen_width = self.BORDER_WIDTH_OF_SELECTED_CELL_ENABLED
                final_pen_color = self.PEN_COLOR_ENABLED
            else:
                pen_width = self.BORDER_WIDTH_OF_SELECTED_CELL_DISABLED
                final_pen_color = self.PEN_COLOR_DISABLED

            pen = QPen()
            pen.setColor(self.BORDER_COLOR_OF_SELECTED_CELL)
            pen.setWidth(pen_width)
            painter.setPen(pen)
            painter.setBrush(opt.backgroundBrush)
            x = int(round(opt.rect.x() + pen.width() / 2))
            y = int(round(opt.rect.y() + pen.width() / 2))
            width = int(round(opt.rect.width() - pen.width()))
            height = int(round(opt.rect.height() - pen.width()))
            rect_with_inside_border = QRect(x, y, width, height)
            painter.drawRect(rect_with_inside_border)

            painter.setPen(final_pen_color)
            rect_with_padding = rect_with_inside_border.adjusted(self.TEXT_PADDING, self.TEXT_PADDING,
                                                                 -self.TEXT_PADDING, -self.TEXT_PADDING)
            painter.drawText(rect_with_padding, Qt.AlignLeft | Qt.AlignVCenter, opt.text)
        else:
            super().paint(painter, opt, index)

        painter.restore()


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
        self._read_only: bool = False
        self.adjustSize()
        self._set_f2_hotkey()

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setItemDelegate(CommentTableDelegate())
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def _add_row(self, index: int, comment: Optional[str] = None) -> None:
        """
        Method inserts a new comment to the table.
        :param index: index of the pin for which the comment needs to be added;
        :param comment: comment.
        """

        self.insertRow(index)
        self.setItem(index, 0, PinIndexTableItem(index))

        item = self._create_table_item(self._read_only)
        item.setText(comment or "")
        self.setItem(index, 1, item)

    def _change_row_color(self, index: int, pin: Pin) -> None:
        """
        Method sets the color of the row depending on the difference value. If the pin to which the row corresponds has
        test and reference IV-curves, then the difference is calculated. If difference is not greater than the
        tolerance, then the row is colored light green, otherwise pink.
        :param index: index of the pin;
        :param pin: pin.
        """

        if pin is None:
            return

        reference, test, settings = pin.get_reference_and_test_measurements()
        if None not in (reference, test, settings):
            brush = CommentWidget.GOOD_BRUSH \
                if self._main_window.check_good_difference(reference.ivc, test.ivc, settings) \
                else CommentWidget.BAD_BRUSH
        else:
            brush = CommentWidget.WHITE_BRUSH

        for column in range(self.columnCount()):
            item = self.item(index, column)
            item.setBackground(brush)

    def _check_show_context_menu(self, pos: QPoint) -> bool:
        """
        :param pos: the position of the context menu event that the widget receives.
        :return: True if the context menu should be shown.
        """

        return (self._main_window.new_point_action.isEnabled() and self._main_window.remove_point_action.isEnabled() and
                self.row(self.itemAt(pos)) >= 0)

    @disconnect_item_signals
    def _fill_table(self) -> None:
        """
        Method fills in a table with comments on the measurement plan pins.
        """

        for index, pin in self._main_window.measurement_plan.all_pins_iterator():
            self._add_row(index, pin.comment)
            self._change_row_color(index, pin)

    def _set_f2_hotkey(self) -> None:
        """
        Method sets the F2 hotkey for editing comments.
        """

        self._shortcut: QShortcut = QShortcut(QKeySequence(Qt.Key_F2), self)
        self._shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._shortcut.activated.connect(self._set_focus_on_current_item)

    @pyqtSlot()
    def _set_focus_on_current_item(self) -> None:
        """
        Slot sets the item with the current comment into editable mode.
        """

        item = self.item(self.currentRow(), 1)
        if item and self._main_window.work_mode in (WorkMode.TEST, WorkMode.WRITE):
            self._main_window.activateWindow()
            self.editItem(item)

    def _set_read_only(self, read_only: bool) -> None:
        """
        :param read_only: if True, then set the table to an editable state, otherwise to a non-editable state.
        """

        column = 1
        for row in range(self.rowCount()):
            item = self.item(row, column)
            change_item_state(item, read_only)

    @disconnect_item_signals
    def add_comment(self, index: int, pin: Pin) -> None:
        """
        :param index: index of the pin whose comment to add;
        :param pin: pin whose comment to add.
        """

        self._add_row(index, pin.comment)
        self._change_row_color(index, pin)
        self._update_indexes(index)

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

    @disconnect_item_signals
    def remove_comment(self, index: int) -> None:
        """
        :param index: index of the row to be deleted.
        """

        self._remove_row(index)
        self._update_indexes(index)

    def save_comment(self, index: int) -> None:
        """
        Method saves comment to pin.
        :param index: pin index.
        """

        pin = self._main_window.measurement_plan.get_pin_with_index(index)
        if not pin:
            return

        item = self.item(index, 1)
        if item:
            pin.comment = item.text()

    def set_work_mode(self, mode: WorkMode) -> None:
        """
        Method sets widgets according to new work mode. Comment is only for test and write modes.
        :param mode: new work mode.
        """

        if mode is WorkMode.READ_PLAN:
            if not self._read_only:
                self._read_only = True
                self._set_read_only(self._read_only)
            self.setEnabled(True)
        else:
            if self._read_only:
                self._read_only = False
                self._set_read_only(self._read_only)
            self.setEnabled(mode in (WorkMode.TEST, WorkMode.WRITE))

    @pyqtSlot(QPoint)
    def show_context_menu(self, pos: QPoint) -> None:
        """
        Slot shows a context menu for creating and deleting a point.
        :param pos: the position of the context menu event that the widget receives.
        """

        if self._check_show_context_menu(pos):
            menu = QMenu(self)
            action_add_pin = QAction(QIcon(os.path.join(ut.DIR_MEDIA, "newpoint.png")),
                                     qApp.translate("MainWindow", "Новая точка"), menu)
            action_add_pin.triggered.connect(self._main_window.create_new_pin)
            menu.addAction(action_add_pin)

            action_remove_pin = QAction(QIcon(os.path.join(ut.DIR_MEDIA, "remove_point.png")),
                                        qApp.translate("MainWindow", "Удалить точку"), menu)
            action_remove_pin.triggered.connect(self._main_window.remove_pin)
            menu.addAction(action_remove_pin)
            menu.popup(self.viewport().mapToGlobal(pos))

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

        self._clear_table()
        self._fill_table()

    def update_table_for_new_tolerance(self, *indexes) -> None:
        """
        Method updates the display style of cells in the table. The method must be called when the difference for pins
        or tolerance changes.
        :param indexes: indexes of pins for which you need to update the display style.
        """

        if len(indexes) == 0:
            indexes = range(self.rowCount())

        for index in indexes:
            pin = self._main_window.measurement_plan.get_pin_with_index(index)
            self._change_row_color(index, pin)
