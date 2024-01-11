import os
import sys
import unittest
from typing import Tuple
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from window.commentwidget import CommentWidget
from window.common import WorkMode
from .simplemainwindow import SimpleMainWindow


def prepare_data(board_name: str) -> Tuple[SimpleMainWindow, CommentWidget]:
    """
    :param board_name: file name with board.
    :return: an object that models a simple application window, and a widget with a table of pin comments.
    """

    dir_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
    window: SimpleMainWindow = SimpleMainWindow(os.path.join(dir_name, board_name))
    comment_widget: CommentWidget = CommentWidget(window)
    return window, comment_widget


class TestCommentWidget(unittest.TestCase):

    def setUp(self) -> None:
        self._app: QApplication = QApplication(sys.argv[1:])

    def test_clear_table(self) -> None:
        window, comment_widget = prepare_data("simple_board.json")
        comment_widget.update_info()
        comment_widget.clear_table()
        self.assertEqual(comment_widget.rowCount(), 0)

    def test_set_work_mode(self) -> None:
        _, comment_widget = prepare_data("simple_board.json")
        comment_widget.update_info()
        self.assertFalse(comment_widget.read_only)

        comment_widget.set_work_mode(WorkMode.READ_PLAN)
        self.assertTrue(comment_widget.read_only)
        for row in range(comment_widget.rowCount()):
            item = comment_widget.item(row, 1)
            self.assertFalse(bool(int(item.flags()) & Qt.ItemIsEditable))

        comment_widget.set_work_mode(WorkMode.WRITE)
        self.assertFalse(comment_widget.read_only)
        for row in range(comment_widget.rowCount()):
            item = comment_widget.item(row, 1)
            self.assertTrue(bool(int(item.flags()) & Qt.ItemIsEditable))

    def test_size_hint(self) -> None:
        _, comment_widget = prepare_data("simple_board.json")
        self.assertEqual(comment_widget.sizeHint().width(), 150)

    def test_update_info(self) -> None:
        _, comment_widget = prepare_data("simple_board.json")
        comment_widget.update_info()
        self.assertEqual(comment_widget.rowCount(), 3)
        for row in range(comment_widget.rowCount()):
            item = comment_widget.item(row, 1)
            self.assertEqual(item.text(), f"comment for pin {row + 1}")
