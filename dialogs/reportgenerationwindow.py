"""
File with class for dialog window to create report for board.
"""

import queue
import time
from typing import List, Tuple
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt, QThread
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QDialog, QFileDialog, QGroupBox, QHBoxLayout, QLayout, QProgressBar, QTextEdit, QVBoxLayout
from epcore.elements import Board
from report_generator import ConfigAttributes, ObjectsForReport, ReportGenerator, ReportTypes, ScalingTypes
import utils as ut
from common import WorkMode
from dialogs.language import Language


def get_scales_and_noise_amplitudes_for_iv_curves(board: Board, main_window) -> Tuple[List, List]:
    """
    Function returns scales and noise amplitudes for IV-curves in pins of board.
    :param board: board;
    :param main_window: main window of application.
    :return: list with scales and list with noise amplitudes.
    """

    scales = []
    noise_amplitudes = []
    for element in board.elements:
        for pin in element.pins:
            if pin.measurements:
                voltage, current = ut.calculate_scales(pin.measurements[0].settings)
                current /= 1000
                scales.append((voltage, current))
                noise_amplitudes.append(main_window.product.adjust_noise_amplitude(pin.measurements[0].settings))
            else:
                scales.append(None)
                noise_amplitudes.append(None)
    return scales, noise_amplitudes


class ReportGenerationThread(QThread):
    """
    Class for thread to generate reports.
    """

    def __init__(self, parent) -> None:
        """
        :param parent: main window.
        """

        super().__init__(parent=parent)
        self._stop_thread: bool = False
        self._task: queue.Queue = queue.Queue()
        self.report_generator: ReportGenerator = ReportGenerator()
        self.setTerminationEnabled(True)

    def add_task(self, config: dict) -> None:
        """
        :param config: config dictionary to create report.
        """

        self.report_generator.stop = False
        self._task.put(lambda: self.report_generator.run(config))

    def run(self) -> None:
        while not self._stop_thread:
            if not self._task.empty():
                task = self._task.get()
                task()
            else:
                time.sleep(0.1)

    def stop_generation(self) -> None:
        """
        Method stops report generation.
        """

        self.report_generator.stop_process()

    def stop_thread(self) -> None:
        """
        Method stops thread.
        """

        self.stop_generation()
        self._stop_thread = True


class ReportGenerationWindow(QDialog):
    """
    Class for dialog window to create report for board.
    """

    def __init__(self, parent, thread: ReportGenerationThread, board: Board, threshold: float) -> None:
        """
        :param parent: parent window;
        :param thread: thread for report generation;
        :param board:
        :param threshold:
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._parent = parent
        self._board: Board = board
        self._folder_for_report: str = ut.get_dir_name()
        self._number_of_steps_done: int = 0
        self._threshold_score: float = threshold
        self._thread: ReportGenerationThread = thread
        self._total_number: int = None
        self._init_ui()
        self._init_thread()

    def _create_report(self) -> None:
        scales, noise_amplitudes = get_scales_and_noise_amplitudes_for_iv_curves(self._board, self._parent)
        report_to_open = ReportTypes.FULL_REPORT if self._parent.work_mode == WorkMode.WRITE else\
            ReportTypes.SHORT_REPORT
        config = {ConfigAttributes.BOARD: self._board,
                  ConfigAttributes.DIRECTORY: self._folder_for_report,
                  ConfigAttributes.ENGLISH: qApp.instance().property("language") == Language.EN,
                  ConfigAttributes.NOISE_AMPLITUDES: noise_amplitudes,
                  ConfigAttributes.OBJECTS: {ObjectsForReport.BOARD: True},
                  ConfigAttributes.OPEN_REPORT_AT_FINISH: True,
                  ConfigAttributes.PIN_SIZE: 150,
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

    def _init_thread(self) -> None:
        try:
            self._thread.report_generator.total_number_of_steps_calculated.disconnect()
            self._thread.report_generator.step_done.disconnect()
            self._thread.report_generator.step_started.disconnect()
            self._thread.report_generator.generation_finished.disconnect()
            self._thread.report_generator.generation_stopped.disconnect()
            self._thread.report_generator.exception_raised.disconnect()
        except Exception:
            pass
        self._thread.report_generator.total_number_of_steps_calculated.connect(self.set_total_number_of_steps)
        self._thread.report_generator.step_done.connect(self.change_progress)
        self._thread.report_generator.step_started.connect(self.text_edit_info.append)
        self._thread.report_generator.generation_finished.connect(self.finish_generation)
        self._thread.report_generator.generation_stopped.connect(lambda: self.handle_generation_break_or_stop(""))
        self._thread.report_generator.exception_raised.connect(self.handle_generation_break_or_stop)

    def _init_ui(self) -> None:
        self.setWindowTitle(qApp.translate("dialogs", "Генератор отчетов"))
        self.progress_bar: QProgressBar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)

        self.text_edit_info: QTextEdit = QTextEdit()
        self.text_edit_info.setVisible(False)
        self.text_edit_info.setMaximumHeight(100)
        self.text_edit_info.setReadOnly(True)
        self.group_box_info: QGroupBox = QGroupBox(qApp.translate("dialogs", "Шаги генерации отчета"))
        self.group_box_info.setFixedWidth(300)
        self.group_box_info.setCheckable(True)
        self.group_box_info.setChecked(False)
        self.group_box_info.setVisible(False)
        self.group_box_info.toggled.connect(self.text_edit_info.setVisible)
        h_box_layout = QHBoxLayout()
        h_box_layout.addWidget(self.text_edit_info)
        self.group_box_info.setLayout(h_box_layout)

        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self.progress_bar)
        v_box_layout.addWidget(self.group_box_info)
        v_box_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(v_box_layout)
        self.adjustSize()

    @pyqtSlot()
    def change_progress(self) -> None:
        """
        Slot changes progress of report generation.
        """

        self._number_of_steps_done += 1
        self.progress_bar.setValue(int(self._number_of_steps_done / self._total_number * 100))

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        :param event: close event.
        """

        self._thread.stop_generation()
        super().closeEvent(event)

    @pyqtSlot()
    def finish_generation(self, *args) -> None:
        """
        Slot finishes generation of the report.
        """

        self.close()

    @pyqtSlot()
    def handle_generation_break_or_stop(self, *args) -> None:
        """
        Slot handles break of the report generation.
        """

        ut.show_message(qApp.translate("dialogs", "Информация"),
                        qApp.translate("dialogs", "Отчет не был сгенерирован."))
        self.close()

    def show_window(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, qApp.translate("t", "Выбрать папку"), self._folder_for_report)
        if folder:
            self._folder_for_report = folder
            self._create_report()
            self.exec()

    @pyqtSlot(int)
    def set_total_number_of_steps(self, number: int) -> None:
        """
        Slot sets total number of steps of calculation.
        :param number: total number of steps.
        """

        self._total_number = number
