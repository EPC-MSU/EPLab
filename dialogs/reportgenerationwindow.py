"""
File with class for dialog window to create report for board.
"""

import queue
import time
from typing import Any, Dict, List, Tuple
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt, QThread
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QDialog, QGroupBox, QHBoxLayout, QLayout, QProgressBar, QTextEdit, QVBoxLayout
from epcore.elements import Board
from report_generator import ConfigAttributes, ObjectsForReport, ReportGenerator, ReportTypes, ScalingTypes
import utils as ut
from common import WorkMode
from dialogs.language import Language


def get_scales_and_noise_amplitudes_for_iv_curves(board: Board, main_window
                                                  ) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """
    Function returns scales and noise amplitudes for IV-curves in the pins of the board.
    :param board: board;
    :param main_window: main window.
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
        self._parent = parent
        self._stop_thread: bool = False
        self._task: queue.Queue = queue.Queue()
        self._task_is_running: bool = False
        self.report_generator: ReportGenerator = ReportGenerator()
        self.setTerminationEnabled(True)

    def _create_config(self, board: Board, dir_for_report: str, threshold: float, work_mode: WorkMode
                       ) -> Dict[ConfigAttributes, Any]:
        """
        :param board: board for which to generate a report;
        :param dir_for_report: directory where to save the report;
        :param threshold: score threshold;
        :param work_mode: application work mode.
        :return: configuration dictionary that specifies the operation of the report generator.
        """

        scales, noise_amplitudes = get_scales_and_noise_amplitudes_for_iv_curves(board, self._parent)
        report_to_open = ReportTypes.FULL_REPORT if work_mode == WorkMode.WRITE else ReportTypes.SHORT_REPORT
        return {ConfigAttributes.BOARD: board,
                ConfigAttributes.DIRECTORY: dir_for_report,
                ConfigAttributes.ENGLISH: qApp.instance().property("language") == Language.EN,
                ConfigAttributes.NOISE_AMPLITUDES: noise_amplitudes,
                ConfigAttributes.OBJECTS: {ObjectsForReport.BOARD: True},
                ConfigAttributes.OPEN_REPORT_AT_FINISH: True,
                ConfigAttributes.PIN_SIZE: 150,
                ConfigAttributes.REPORTS_TO_OPEN: [report_to_open],
                ConfigAttributes.SCALING_TYPE: ScalingTypes.USER_DEFINED,
                ConfigAttributes.THRESHOLD_SCORE: threshold,
                ConfigAttributes.USER_DEFINED_SCALES: scales}

    def _run_report_generation(self, board: Board, dir_for_report: str, threshold: float, work_mode: WorkMode) -> None:
        """
        :param board: board for which to generate a report;
        :param dir_for_report: directory where to save the report;
        :param threshold: score threshold;
        :param work_mode: application work mode.
        """

        config = self._create_config(board, dir_for_report, threshold, work_mode)
        self.report_generator.run(config)

    def add_task(self, *args, **kwargs) -> None:
        self.report_generator.stop = False
        self._task.put(lambda: self._run_report_generation(*args, **kwargs))

    def run(self) -> None:
        while not self._stop_thread:
            self._task_is_running = False
            if not self._task.empty():
                self._task_is_running = True
                task = self._task.get()
                task()
                self._task_is_running = False
            else:
                time.sleep(0.1)

    def stop_generation(self) -> None:
        """
        Method stops report generation.
        """

        if self._task_is_running:
            self.report_generator.stop_process()

    def stop_thread(self) -> None:
        """
        Method stops the thread.
        """

        self.stop_generation()
        self._stop_thread = True


class ReportGenerationWindow(QDialog):
    """
    Class for dialog window to create report for board.
    """

    def __init__(self, parent, thread: ReportGenerationThread) -> None:
        """
        :param parent: main window;
        :param thread: thread in which to run report generation.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._number_of_steps_done: int = 0
        self._thread: ReportGenerationThread = thread
        self._total_number: int = None
        self._init_ui()
        self._init_thread()

    def _init_thread(self) -> None:
        for signal_name in ("exception_raised", "generation_finished", "generation_stopped", "step_done",
                            "step_started", "total_number_of_steps_calculated"):
            signal = getattr(self._thread.report_generator, signal_name, None)
            if signal:
                try:
                    signal.disconnect()
                except Exception:
                    pass

        self._thread.report_generator.exception_raised.connect(lambda: self.close())
        self._thread.report_generator.generation_finished.connect(lambda: self.close())
        self._thread.report_generator.generation_stopped.connect(lambda: self.close())
        self._thread.report_generator.step_done.connect(self.change_progress)
        self._thread.report_generator.step_started.connect(self.text_edit_info.append)
        self._thread.report_generator.total_number_of_steps_calculated.connect(self.set_total_number_of_steps)

    def _init_ui(self) -> None:
        self.setWindowTitle(qApp.translate("dialogs", "Генератор отчетов"))
        self.progress_bar: QProgressBar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.text_edit_info: QTextEdit = QTextEdit()
        self.text_edit_info.setMaximumHeight(100)
        self.text_edit_info.setReadOnly(True)
        self.group_box_info: QGroupBox = QGroupBox(qApp.translate("dialogs", "Шаги генерации отчета"))
        self.group_box_info.toggled.connect(self.text_edit_info.setVisible)
        self.group_box_info.setFixedWidth(300)
        self.group_box_info.setCheckable(True)
        self.group_box_info.setChecked(False)
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
        self._number_of_steps_done += 1
        self.progress_bar.setValue(int(self._number_of_steps_done / self._total_number * 100))

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        :param event: close event.
        """

        self._thread.stop_generation()
        super().closeEvent(event)

    @pyqtSlot(int)
    def set_total_number_of_steps(self, number: int) -> None:
        """
        :param number: total number of steps to generate a report.
        """

        self._total_number = number


def show_report_generation_window(parent, thread: ReportGenerationThread, board: Board, dir_for_report: str,
                                  threshold: float, work_mode: WorkMode) -> None:
    """
    :param parent: main window;
    :param thread: thread in which the report will be generated;
    :param board: board for which to generate a report;
    :param dir_for_report: directory where to save the report;
    :param threshold: score threshold;
    :param work_mode: application work mode.
    """

    window = ReportGenerationWindow(parent, thread)
    thread.add_task(board, dir_for_report, threshold, work_mode)
    window.exec()
