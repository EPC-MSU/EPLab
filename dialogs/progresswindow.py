import os
from typing import Optional
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtGui import QFontMetrics, QIcon
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLayout, QProgressBar, QPushButton, QVBoxLayout
from window import utils as ut


class ProgressWindow(QDialog):
    """
    A window for displaying information about the progress of a process.
    """

    stopped: pyqtSignal = pyqtSignal()

    def __init__(self, main_window, title: str) -> None:
        """
        :param main_window: main window of application;
        :param title: window title.
        """

        super().__init__(main_window, Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        self._number_of_steps_done: int = 0
        self._total_number: Optional[int] = None
        self._init_ui(title)

    def _create_cancel_button(self) -> QLayout:
        """
        :return: layout with button.
        """

        self._button_cancel: QPushButton = QPushButton()
        self._button_cancel.setText(qApp.translate("t", "Отмена"))
        self._button_cancel.clicked.connect(self.stopped.emit)

        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(self._button_cancel)
        return h_layout

    def _create_progress_bar(self) -> QProgressBar:
        """
        :return: progress bar.
        """

        self._progress_bar: QProgressBar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        return self._progress_bar

    def _init_ui(self, title: str) -> None:
        """
        :param title: window title.
        """

        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        metrics = QFontMetrics(self.font())
        title_width = metrics.horizontalAdvance(title)
        self.setMinimumWidth(title_width + 150)

        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self._create_progress_bar())
        v_box_layout.addLayout(self._create_cancel_button())
        v_box_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.setLayout(v_box_layout)
        self.adjustSize()

    @pyqtSlot()
    def change_progress(self) -> None:
        self._number_of_steps_done += 1
        self._progress_bar.setValue(int(self._number_of_steps_done / self._total_number * 100))

    @pyqtSlot(bool)
    def close_window(self, unused: bool) -> None:
        """
        :param unused: unused parameter.
        """

        self.close()

    @pyqtSlot(int)
    def set_total_number_of_steps(self, number: int) -> None:
        """
        :param number: total number of steps to generate a report.
        """

        self._total_number = number
