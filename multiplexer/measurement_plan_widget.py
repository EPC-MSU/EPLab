"""
File with class for widget to show short information from measurement plan.
"""

import PyQt5.QtWidgets as qt
from epcore.measurementmanager import MeasurementPlan


class MeasurementPlanWidget(qt.QWidget):
    """
    Class to show short information from measurement plan.
    """

    def __init__(self, parent):
        """
        :param parent: parent main window.
        """

        super().__init__()
        self._parent = parent
        self._measurement_plan: MeasurementPlan = parent.measurement_plan
        self._init_ui()

    def _init_ui(self):
        """
        Method initializes widgets on main widget.
        """

        self.table_widget_info = qt.QTableWidget(len(list(self._measurement_plan.all_pins_iterator())), 5)
        v_box_layout = qt.QVBoxLayout()
        self.setLayout(v_box_layout)
