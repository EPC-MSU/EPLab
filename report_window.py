"""
File with class for dialog window to create report for board.
"""

import queue
import time
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt, QThread
from PyQt5.QtGui import QCloseEvent
from epcore.elements import Board
from report_generator import ConfigAttributes, create_test_and_ref_boards, ObjectsForReport, ReportGenerator
from language import Language


class ReportGenerationThread(QThread):
    """
    Class for thread to generate reports.
    """

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._task: queue.Queue = queue.Queue()
        self.report_generator: ReportGenerator = ReportGenerator()

    def add_task(self, config: dict):
        """
        Method adds task.
        :param config: config dictionary to create report.
        """

        self.report_generator.stop = False
        self._task.put(lambda: self.report_generator.run(config))

    def run(self):
        while True:
            if not self._task.empty():
                task = self._task.get()
                task()
            else:
                time.sleep(0.1)

    def stop_generation(self):
        """
        Method stops report generation.
        """

        self.report_generator.stop_process()


class ReportGenerationWindow(qt.QDialog):
    """
    Class for dialog window to create report for board.
    """

    def __init__(self, parent: "EPLabWindow", thread: ReportGenerationThread, board: Board,
                 folder_for_report: str = None, threshold_score: float = None):
        """
        :param parent: parent window;
        :param thread: thread for report generation;
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
        self._number_of_steps_done: int = 0
        self._software_change_of_button_state: bool = False
        self._threshold_score: float = threshold_score
        self._total_number: int = None
        self._init_ui()
        self._thread: ReportGenerationThread = thread
        self._thread.report_generator.total_number_of_steps_calculated.connect(self.set_total_number_of_steps)
        self._thread.report_generator.step_done.connect(self.change_progress)
        self._thread.report_generator.step_started.connect(self.text_edit_info.append)
        self._thread.report_generator.generation_finished.connect(self.finish_generation)
        self._thread.report_generator.exception_raised.connect(self.handle_generation_break)

    def _create_report(self):
        """
        Method creates report.
        """

        test_board, ref_board = create_test_and_ref_boards(self._board)
        config = {ConfigAttributes.BOARD_REF: ref_board,
                  ConfigAttributes.BOARD_TEST: test_board,
                  ConfigAttributes.DIRECTORY: self._folder_for_report,
                  ConfigAttributes.ENGLISH: qApp.instance().property("language") == Language.EN,
                  ConfigAttributes.OBJECTS: {ObjectsForReport.BOARD: True},
                  ConfigAttributes.OPEN_REPORT_AT_FINISH: True,
                  ConfigAttributes.PIN_SIZE: 200,
                  ConfigAttributes.THRESHOLD_SCORE: self._threshold_score}
        self._number_of_steps_done = 0
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.text_edit_info.clear()
        self.group_box_info.setVisible(True)
        self._thread.add_task(config)

    def _finish_generation(self, report_dir_path: str = "", report_was_generated: bool = True):
        """
        Method finishes generation of report.
        :param report_dir_path: path to directory with report;
        :param report_was_generated: if True then report was generated.
        """

        self.progress_bar.setVisible(False)
        self.group_box_info.setVisible(False)
        self.group_box_info.setChecked(False)
        self.text_edit_info.setVisible(False)
        if report_was_generated:
            message = qApp.translate("t", "Отчет сгенерирован и сохранен в файл 'FOLDER'")
            message = message.replace("FOLDER", report_dir_path)
        else:
            message = qApp.translate("t", "Отчет не был сгенерирован")
        qt.QMessageBox.information(self._parent, qApp.translate("t", "Информация"), message)

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
        self.button_create_report.setCheckable(True)
        self.button_create_report.toggled.connect(self.start_or_stop)
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

    def _set_state_to_buttons(self, state: bool):
        """
        Method sets properties for buttons.
        :param state: if True then buttons need to be passed properties when generating
        report.
        """

        self.button_select_folder.setEnabled(not state)
        if state:
            self.button_create_report.setText(qApp.translate("t", "Завершить генерацию отчетов"))
        else:
            self.button_create_report.setText(qApp.translate("t", "Сгенерировать отчет"))
            self.button_create_report.setChecked(False)

    @pyqtSlot()
    def change_progress(self):
        """
        Slot changes progress of report generation.
        """

        self._number_of_steps_done += 1
        self.progress_bar.setValue(int(self._number_of_steps_done / self._total_number * 100))

    def closeEvent(self, event: QCloseEvent):
        """
        Method handles close event.
        :param event: close event.
        """

        self._thread.stop_generation()

    @pyqtSlot(str)
    def finish_generation(self, report_dir_path: str):
        """
        Slot finishes generation of report.
        :param report_dir_path: path to directory with report.
        """

        self._finish_generation(report_dir_path)
        self._software_change_of_button_state = True
        self._set_state_to_buttons(False)

    @pyqtSlot(str)
    def handle_generation_break(self, _: str):
        """
        Slot handles break of report generation.
        :param _: message of exception.
        """

        self._finish_generation(report_was_generated=False)
        self.button_create_report.setEnabled(True)

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

    @pyqtSlot(bool)
    def start_or_stop(self, status: bool):
        """
        Slot starts or stops report generation.
        :param status: if True then report generation should be started.
        """

        if self._software_change_of_button_state:
            self._software_change_of_button_state = False
            return
        if status:
            self._create_report()
        else:
            self._thread.stop_generation()
            self.button_create_report.setEnabled(False)
        self._set_state_to_buttons(status)