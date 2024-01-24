import os
from typing import Optional
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QLayout, QProgressBar, QTextEdit, QVBoxLayout
from window import utils as ut
from window.scaler import update_scale_of_class


@update_scale_of_class
class ProgressWindow(QDialog):
    """
    A window for displaying information about the progress of a process.
    """

    def __init__(self, title: str) -> None:
        """
        :param title: window title.
        """

        super().__init__(None, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._number_of_steps_done: int = 0
        self._total_number: int = None
        self._init_ui(title)

    def _init_ui(self, title: str) -> None:
        """
        :param title: window title.
        """

        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
        self.progress_bar: QProgressBar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.text_edit_info: QTextEdit = QTextEdit()
        self.text_edit_info.setMaximumHeight(100)
        self.text_edit_info.setReadOnly(True)

        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self.progress_bar)
        v_box_layout.addWidget(self.text_edit_info)
        v_box_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(v_box_layout)
        self.adjustSize()

    @pyqtSlot()
    def change_progress(self, step_info: Optional[str] = None) -> None:
        """
        :param step_info: information about the completed step.
        """

        self._number_of_steps_done += 1
        self.progress_bar.setValue(int(self._number_of_steps_done / self._total_number * 100))
        if step_info:
            self.text_edit_info.append(step_info)

    @pyqtSlot(int)
    def set_total_number_of_steps(self, number: int) -> None:
        """
        :param number: total number of steps to generate a report.
        """

        self._total_number = number
