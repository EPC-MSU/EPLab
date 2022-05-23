"""
File with class for dialog window to create report for board.
"""

import queue
import time
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt, QThread
from PyQt5.QtGui import QCloseEvent
from epcore.elements import Board
from epcore.product import EyePointProduct
from report_generator import (ConfigAttributes, create_test_and_ref_boards, ObjectsForReport, ReportGenerator,
                              ReportTypes, ScalingTypes)
import utils as ut
from common import WorkMode
from language import Language


def get_scales_for_iv_curves(board: Board, product: EyePointProduct) -> list:
    """
    Function returns scales for IV-curves in pins of board.
    :param board: board;
    :param product: product.
    :return: list with scales.
    """

    scales = []
    for element in board.elements:
        for pin in element.pins:
            if pin.measurements:
                voltage, current = product.adjust_plot_scale(pin.measurements[0].settings)
                current /= 1000
                scales.append((voltage, current))
            else:
                scales.append(None)
    return scales


class ReportGenerationThread(QThread):
    """
    Class for thread to generate reports.
    """

    def __init__(self, parent):
        super().__init__(parent=parent)
        self._stop_thread: bool = False
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
        while not self._stop_thread:
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

    def stop_thread(self):
        """
        Method stops thread.
        """

        self._stop_thread = True


class ReportGenerationWindow(qt.QDialog):
    """
    Class for dialog window to create report for board.
    """

    def __init__(self, parent, thread: ReportGenerationThread):
        """
        :param parent: parent window;
        :param thread: thread for report generation.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._parent = parent
        self._board: Board = None
        self._folder_for_report: str = ut.get_dir_name()
        self._number_of_steps_done: int = 0
        self._software_change_of_button_state: bool = False
        self._threshold_score: float = None
        self._total_number: int = None
        self._init_ui()
        self._thread: ReportGenerationThread = thread
        try:
            self._thread.report_generator.total_number_of_steps_calculated.disconnect()
            self._thread.report_generator.step_done.disconnect()
            self._thread.report_generator.step_started.disconnect()
            self._thread.report_generator.generation_finished.disconnect()
            self._thread.report_generator.exception_raised.disconnect()
        except Exception:
            pass
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
        scales = get_scales_for_iv_curves(self._board, self._parent.product)
        report_to_open = ReportTypes.FULL_REPORT if self._parent.work_mode == WorkMode.WRITE else\
            ReportTypes.SHORT_REPORT
        config = {ConfigAttributes.BOARD_REF: ref_board,
                  ConfigAttributes.BOARD_TEST: test_board,
                  ConfigAttributes.DIRECTORY: self._folder_for_report,
                  ConfigAttributes.ENGLISH: qApp.instance().property("language") == Language.EN,
                  ConfigAttributes.OBJECTS: {ObjectsForReport.BOARD: True},
                  ConfigAttributes.OPEN_REPORT_AT_FINISH: True,
                  ConfigAttributes.PIN_SIZE: 200,
                  ConfigAttributes.REPORTS_TO_OPEN: [report_to_open],
                  ConfigAttributes.SCALING_TYPE: ScalingTypes.USER_DEFINED,
                  ConfigAttributes.THRESHOLD_SCORE: self._threshold_score,
                  ConfigAttributes.USER_DEFINED_SCALES: scales}
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
            message = qApp.translate("t", "Отчет сгенерирован и сохранен в директорию 'FOLDER'")
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
        super().closeEvent(event)

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

    @pyqtSlot(int)
    def set_total_number_of_steps(self, number: int):
        """
        Slot sets total number of steps of calculation.
        :param number: total number of steps.
        """

        self._total_number = number

    def start_generation(self):
        """
        Method starts report generation.
        """

        self.button_create_report.setChecked(True)

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

    def update_info(self, board: Board, threshold_score: float = None):
        """
        Method updates info for report generator.
        :param board: board for which report should be generated;
        :param threshold_score: threshold score for board report.
        """

        self._board = board
        self._threshold_score = threshold_score
