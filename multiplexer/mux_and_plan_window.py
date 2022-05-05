"""
File with class to show window with information about multiplexer and
measurement plan.
"""

import os
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from multiplexer.measurement_plan_widget import MeasurementPlanWidget
from multiplexer.multiplexer_pinout_widget import MultiplexerPinoutWidget


class MuxAndPlanWindow(qt.QDialog):
    """
    Class for dialog window to show information about multiplexer and measurement plan.
    """

    def __init__(self, parent):
        """
        :param parent: parent main window.
        """

        super().__init__(parent, Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
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
        v_box_layout = qt.QVBoxLayout()
        v_box_layout.addWidget(self.multiplexer_pinout_widget)
        v_box_layout.addWidget(self.measurement_plan_widget)
        v_box_layout.setSpacing(0)
        v_box_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(v_box_layout)
