"""
File with class for dialog window to create report for board.
"""

from functools import partial
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt, QThread
from PyQt5.QtGui import QCloseEvent
from epcore.elements import Board
from report_generator import (ConfigAttributes, create_test_and_ref_boards, ObjectsForReport,
                              ReportGenerator)


class ReportGenerationWindow(qt.QDialog):
    """
    Class for dialog window to create report for board.
    """

    def __init__(self, parent: "EPLabWindow", board: Board, folder_for_report: str = None,
                 threshold_score: float = None):
        """
        :param parent: parent window;
        :param board: board for which report should be generated;
        :param folder_for_report: folder where report should be saved;
        :param threshold_score: threshold score for board report.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._parent = parent
        self._board = board
        if folder_for_report:
            self._folder_for_report: str = folder_for_report
        else:
            self._folder_for_report: str = "."
        self._threshold_score: float = threshold_score
        self._number_of_steps_done: int = 0
        self._total_number: int = None
        self._thread: QThread = None
        self._init_ui()

    def _init_ui(self):
        """
        Method initializes widgets on dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "Генератор отчетов"))
        v_box_layout = qt.QVBoxLayout()
        self.button_select_folder = qt.QPushButton(qApp.translate("t", "Выбрать папку для отчета"))
        self.button_select_folder.clicked.connect(self.select_folder)
        self.button_select_folder.setFixedWidth(300)
        v_box_layout.addWidget(self.button_select_folder)
        self.button_create_report = qt.QPushButton(qApp.translate("t", "Сгенерировать отчет"))
        self.button_create_report.clicked.connect(self.create_report)
        self.button_create_report.setFixedWidth(300)
        v_box_layout.addWidget(self.button_create_report)
        self.progress_bar = qt.QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        v_box_layout.addWidget(self.progress_bar)
        self.text_edit_info = qt.QTextEdit()
        self.text_edit_info.setVisible(False)
        self.text_edit_info.setMaximumHeight(100)
        self.text_edit_info.setReadOnly(True)
        self.group_box_info = qt.QGroupBox(qApp.translate("t", "Шаги генерации отчета"))
        self.group_box_info.setFixedWidth(300)
        self.group_box_info.setCheckable(True)
        self.group_box_info.setChecked(False)
        self.group_box_info.setVisible(False)
        self.group_box_info.toggled.connect(self.text_edit_info.setVisible)
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addWidget(self.text_edit_info)
        self.group_box_info.setLayout(h_box_layout)
        v_box_layout.addWidget(self.group_box_info)
        v_box_layout.setSizeConstraint(qt.QLayout.SetFixedSize)
        self.setLayout(v_box_layout)
        self.adjustSize()

    @pyqtSlot()
    def change_progress(self):
        """
        Slot changes progress of report generation.
        """

        self._number_of_steps_done += 1
        self.progress_bar.setValue(int(self._number_of_steps_done / self._total_number * 100))

    def closeEvent(self, event: QCloseEvent):
        """
        Method handles signal to close dialog window.
        :param event: close event.
        """

        if self._thread:
            self._thread.quit()
        super().closeEvent(event)

    @pyqtSlot()
    def create_report(self):
        """
        Slot creates report.
        """

        if self._thread:
            self._thread.quit()
        self._thread = QThread(parent=self._parent)
        self._thread.setTerminationEnabled(True)
        test_board, ref_board = create_test_and_ref_boards(self._board)
        config = {ConfigAttributes.BOARD_TEST: test_board,
                  ConfigAttributes.BOARD_REF: ref_board,
                  ConfigAttributes.DIRECTORY: self._folder_for_report,
                  ConfigAttributes.OBJECTS: {ObjectsForReport.BOARD: True},
                  ConfigAttributes.THRESHOLD_SCORE: self._threshold_score,
                  ConfigAttributes.OPEN_REPORT_AT_FINISH: True}
        report_generator = ReportGenerator()
        report_generator.moveToThread(self._thread)
        report_generator.total_number_of_steps_calculated.connect(self.set_total_number_of_steps)
        report_generator.step_done.connect(self.change_progress)
        report_generator.exception_raised.connect(self.show_exception)
        report_generator.step_started.connect(self.text_edit_info.append)
        report_generator.generation_finished.connect(self.finish_generation)
        self._thread.started.connect(partial(report_generator.run, config))
        self._number_of_steps_done = 0
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.text_edit_info.clear()
        self.group_box_info.setVisible(True)
        self._thread.start()

    @pyqtSlot(str)
    def finish_generation(self, report_dir_path: str):
        """
        Slot finishes generation of report.
        :param report_dir_path: path to directory with report.
        """

        self.progress_bar.setVisible(False)
        self.group_box_info.setVisible(False)
        self.group_box_info.setChecked(False)
        self.text_edit_info.setVisible(False)
        message = qApp.translate("t", "Отчет сгенерирован и сохранен в файл 'FOLDER'")
        message = message.replace("FOLDER", report_dir_path)
        qt.QMessageBox.information(self._parent, qApp.translate("t", "Информация"), message)

    @pyqtSlot()
    def select_folder(self):
        """
        Slot selects folder where report will be saved.
        """

        folder = qt.QFileDialog.getExistingDirectory(self, qApp.translate("t", "Выбрать папку"),
                                                     self._folder_for_report)
        if folder:
            self._folder_for_report = folder
            self._parent.set_report_directory(folder)

    @pyqtSlot(int)
    def set_total_number_of_steps(self, number: int):
        """
        Slot sets total number of steps of calculation.
        :param number: total number of steps.
        """

        self._total_number = number

    @pyqtSlot(str)
    def show_exception(self, exception_text: str):
        """
        Slot shows message box with exception thrown when generating report.
        :param exception_text: text of exception.
        """

        qt.QMessageBox.warning(self, qApp.translate("t", "Ошибка"), exception_text)
