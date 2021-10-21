"""
File with class for dialog window to create report for board.
"""

import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt
from epcore.elements import Board
from report_generator import ConfigAttributes, ObjectsForReport, ReportGenerator


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
        self._init_ui()

    def _init_ui(self):
        """
        Method initializes widgets on dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "Генератор отчетов"))
        v_box_layout = qt.QVBoxLayout()
        self.button_select_folder = qt.QPushButton(qApp.translate("t", "Выбрать папку для отчета"))
        self.button_select_folder.clicked.connect(self.select_folder)
        v_box_layout.addWidget(self.button_select_folder)
        self.button_create_report = qt.QPushButton(qApp.translate("t", "Создать отчет"))
        self.button_create_report.clicked.connect(self.create_report)
        v_box_layout.addWidget(self.button_create_report)
        self.progress_bar = qt.QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        v_box_layout.addWidget(self.progress_bar)
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

    @pyqtSlot()
    def create_report(self):
        """
        Slot creates report.
        """

        config = {ConfigAttributes.BOARD_TEST: self._board,
                  ConfigAttributes.DIRECTORY: self._folder_for_report,
                  ConfigAttributes.OBJECTS: {ObjectsForReport.BOARD: True},
                  ConfigAttributes.THRESHOLD_SCORE: self._threshold_score}
        report_generator = ReportGenerator()
        report_generator.total_number_of_steps_calculated.connect(self.set_total_number_of_steps)
        report_generator.step_done.connect(self.change_progress)
        report_generator.generation_finished.connect(self.finish_generation)
        self._number_of_steps_done = 0
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        report_generator.run(config)

    @pyqtSlot()
    def finish_generation(self):
        """
        Slot shows message box with information that report was generated.
        """

        qt.QMessageBox.information(self, qApp.translate("t", "Информация"),
                                   qApp.translate("t", "Отчет создан"))

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
