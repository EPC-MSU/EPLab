"""
File with class to show window with information about multiplexer and
measurement plan.
"""

import os
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from common import WorkMode
from multiplexer.measurement_plan_widget import MeasurementPlanWidget
from multiplexer.multiplexer_pinout_widget import MultiplexerPinoutWidget


class MuxAndPlanWindow(qt.QWidget):
    """
    Class for dialog window to show information about multiplexer and measurement plan.
    """

    def __init__(self, parent):
        """
        :param parent: parent main window.
        """

        super().__init__(None, Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self.measurement_plan_widget: MeasurementPlanWidget = None
        self.multiplexer_pinout_widget: MultiplexerPinoutWidget = None
        self._dir_name: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
        self._parent = parent
        self._init_ui()

    def _init_ui(self):
        """
        Method initializes widgets on dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "Мультиплексор и план измерения"))
        self.setWindowIcon(QIcon(os.path.join(self._dir_name, "ico.png")))
        self.measurement_plan_widget = MeasurementPlanWidget(self._parent)
        self.multiplexer_pinout_widget = MultiplexerPinoutWidget(self._parent)
        self.multiplexer_pinout_widget.channel_added.connect(
            self.measurement_plan_widget.add_pin_with_mux_output_to_plan)
        self.multiplexer_pinout_widget.process_finished.connect(self.measurement_plan_widget.turn_off_standby_mode)
        self.multiplexer_pinout_widget.process_started.connect(self.measurement_plan_widget.turn_on_standby_mode)
        splitter = qt.QSplitter(Qt.Vertical)
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(self.multiplexer_pinout_widget)
        splitter.addWidget(self.measurement_plan_widget)
        layout = qt.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        self.setLayout(layout)
        self.change_work_mode(self._parent.work_mode)

    @pyqtSlot(WorkMode)
    def change_work_mode(self, new_work_mode: WorkMode):
        """
        Slot changes widgets according to new work mode.
        :param new_work_mode: new work mode.
        """

        self.measurement_plan_widget.set_work_mode(new_work_mode)
        self.multiplexer_pinout_widget.set_work_mode(new_work_mode)

    def select_current_pin(self):
        self.measurement_plan_widget.select_row_for_current_pin()

    def update_info(self):
        """
        Method updates information about measurement plan and multiplexer.
        """

        self.measurement_plan_widget.update_info()
        self.multiplexer_pinout_widget.update_info()
