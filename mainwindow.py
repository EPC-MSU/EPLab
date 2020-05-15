from PyQt5.QtWidgets import QMainWindow, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QTimer, QPointF
from PyQt5 import uic

from functools import partial

import epcore.filemanager as epfilemanager
from epcore.measurementmanager import MeasurementSystem, MeasurementPlan
from epcore.elements import MeasurementSettings, Board, Pin, Element
from epcore.measurementmanager.ivc_comparator import IVCComparator
from boardwindow import BoardWidget
from ivviewer import Viewer as IVViewer
from score import ScoreWrapper
from ivview_parameters import IVViewerParametersAdjuster

from enum import Enum, auto


class WorkMode(Enum):
    compare = auto()
    write = auto()
    test = auto()


class EPLabWindow(QMainWindow):

    def __init__(self, msystem: MeasurementSystem):
        super(EPLabWindow, self).__init__()

        uic.loadUi("gui/mainwindow.ui", self)

        self._msystem = msystem
        self._msystem.trigger_measurements()

        self._comparator = IVCComparator()

        self._score_wrapper = ScoreWrapper(self.score_label)

        self.setWindowIcon(QIcon("media/ico.png"))

        self._board_window = BoardWidget()
        self._board_window.resize(600, 600)
        self._board_window.setWindowIcon(QIcon("media/ico.png"))  # TODO: don't duplicate base configurations
        self._board_window.setWindowTitle("EPLab - Board")  # TODO: don't duplicate base configurations

        self._iv_window = IVViewer()
        self._iv_window.resize(600, 600)
        self._iv_window.setWindowIcon((QIcon("media/ico.png")))  # TODO: don't duplicate base configurations
        self._iv_window.setWindowTitle("EPLab - IVC")  # TODO: don't duplicate base configurations

        self._iv_window_parameters_adjuster = IVViewerParametersAdjuster(self._iv_window)

        self.setCentralWidget(self._iv_window)

        # Create default board with 1 pin
        # TODO: why measurers[1]? Must be smth like 'measurers.reference'
        self._measurement_plan = MeasurementPlan(
            Board(elements=[Element(
                pins=[Pin(0, 0, measurements=[])]
            )]
            ),
            measurer=self._msystem.measurers[1]
        )
        self._board_window.set_board(self._measurement_plan)

        self._frequencies = {
            self.frequency_1hz_radio_button: 1,
            self.frequency_10hz_radio_button: 10,
            self.frequency_100hz_radio_button: 100,
            self.frequency_1khz_radio_button: 1000,
            self.frequency_10khz_radio_button: 10000,
            self.frequency_100khz_radio_button: 100000
        }
        for button, frequency in self._frequencies.items():
            button.toggled.connect(partial(self._on_frequency_radio_button_toggled, frequency))

        self._voltages = {
            self.voltage_1_2v_radio_button: 1.2,
            self.voltage_3_3v_radio_button: 3.3,
            self.voltage_5v_radio_button: 5.0,
            self.voltage_12v_radio_button: 12.0
        }
        for button, voltage in self._voltages.items():
            button.toggled.connect(partial(self._on_voltage_radio_button_toggled, voltage))

        self._sensitivities = {
            self.sens_low_radio_button: 47500.0,  # Omh
            self.sens_medium_radio_button: 4750.0,
            self.sens_high_radio_button: 475.0
        }
        for button, resistance in self._sensitivities.items():
            button.toggled.connect(partial(self._on_sensitivity_radio_button_toggled, resistance))

        self.zp_push_button_left.clicked.connect(self._on_go_left_pin)
        self.tp_push_button_left.clicked.connect(self._on_go_left_pin)
        self.zp_push_button_right.clicked.connect(self._on_go_right_pin)
        self.tp_push_button_right.clicked.connect(self._on_go_right_pin)
        self.zp_push_button_new_point.clicked.connect(self._on_new_pin)
        self.zp_push_button_save.clicked.connect(self._on_save_pin)
        self.zp_open_file_button.clicked.connect(self._on_load_board)
        self.zp_save_new_file_button.clicked.connect(self._on_save_board)

        self.test_plan_tab_widget.setCurrentIndex(0)
        self.test_plan_tab_widget.currentChanged.connect(self._on_test_plan_tab_switch)

        self._iv_window_parameters_adjuster.adjust_parameters(self._msystem.get_settings())

        self._work_mode = WorkMode.compare  # compare two current IVC's

        QTimer.singleShot(0, self._update_ivc)

        self._update_current_pin()

    def _change_work_mode(self, mode: WorkMode):
        if self._work_mode is mode:
            return
        self._work_mode = mode

    @pyqtSlot(int)
    def _on_test_plan_tab_switch(self, index: int):
        tab = self.test_plan_tab_widget.currentWidget().objectName()
        if tab == "test_plan_tab_S":  # compare
            self._change_work_mode(WorkMode.compare)
        elif tab == "test_plan_tab_ZP":  # write
            self._change_work_mode(WorkMode.write)
        elif tab == "test_plan_tab_TP":  # test
            self._change_work_mode(WorkMode.test)

    @pyqtSlot(QPointF)
    def _on_board_right_click(self, point: QPointF):
        if self._work_mode is WorkMode.write:
            # Create new pin
            pin = Pin(x=point.x(), y=point.y(), measurements=[])
            self._measurement_plan.append_pin(pin)
            self._board_window.add_point(pin.x, pin.y, self._measurement_plan.get_current_index())
            self._update_current_pin()

    @pyqtSlot()
    def _update_current_pin(self):
        index = self._measurement_plan.get_current_index()
        self.zp_label_num.setText(str(index))
        self.tp_label_num.setText(str(index))
        self._board_window.workspace.select_point(index)

        if self._work_mode is WorkMode.test:  # In test mode we must display saved IVC
            current_pin = self._measurement_plan.get_current_pin()
            measurement = current_pin.get_reference_measurement()
            if measurement:
                self._iv_window.plot.set_reference_curve(measurement.ivc)
            else:
                self._iv_window.plot.set_reference_curve(None)

    @pyqtSlot()
    def _on_go_left_pin(self):
        self._measurement_plan.go_prev_pin()
        self._update_current_pin()

    @pyqtSlot()
    def _on_go_right_pin(self):
        self._measurement_plan.go_next_pin()
        self._update_current_pin()

    @pyqtSlot()
    def _on_new_pin(self):
        if self._measurement_plan.image:
            pin = Pin(self._measurement_plan.image.width() / 2,
                      self._measurement_plan.image.height() / 2,
                      measurements=[])
        else:
            pin = Pin(0, 0, measurements=[])

        self._measurement_plan.append_pin(pin)
        self._board_window.add_point(pin.x, pin.y, self._measurement_plan.get_current_index())
        self._update_current_pin()

    @pyqtSlot()
    def _on_save_pin(self):
        self._measurement_plan.save_last_measurement_as_reference()

    @pyqtSlot()
    def _on_save_board(self):
        dialog = QFileDialog()
        filename = dialog.getSaveFileName(self, "Save board", filter="JSON (*.json)")[0]
        if filename:
            epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)

    @pyqtSlot()
    def _on_load_board(self):
        dialog = QFileDialog()
        filename = dialog.getOpenFileName(self, "Open board", filter="JSON (*.json)")[0]
        if filename:
            board = epfilemanager.load_board_from_ufiv(filename)
            self._measurement_plan = MeasurementPlan(board, measurer=self._msystem.measurers[0])
            self._board_window.set_board(self._measurement_plan)  # New workspace will be created here
            self._board_window.workspace.point_selected.connect(self._on_board_pin_selected)
            self._board_window.workspace.on_right_click.connect(self._on_board_right_click)

            self._update_current_pin()

            if board.image:
                self._board_window.show()

    @pyqtSlot()
    def _update_ivc(self):
        if self._msystem.measurements_are_ready():
            # TODO: why [0] measurer is 'ref' and [1] measurer is 'test'? Should be smth like measurers.test
            test = self._msystem.measurers[0].get_last_iv_curve()
            self._iv_window.plot.set_test_curve(test)

            ref = None
            if self._work_mode is WorkMode.compare:  # We need reference curve only in compare mode
                ref = self._msystem.measurers[1].get_last_iv_curve()
                self._iv_window.plot.set_reference_curve(ref)

            # Update score (only if here are two curves)
            if ref and test:
                score = self._comparator.compare_ivc(ref, test)
                self._score_wrapper.set_score(score)

            self._msystem.trigger_measurements()

        # Add this task to event loop
        QTimer.singleShot(10, self._update_ivc)

    def _set_msystem_settings(self, settings: MeasurementSettings):
        self._msystem.set_settings(settings)
        self._iv_window_parameters_adjuster.adjust_parameters(settings)

    def _on_frequency_radio_button_toggled(self, frequency: float, checked: bool) -> None:
        if checked:
            settings = self._msystem.get_settings()
            settings.probe_signal_frequency = frequency
            settings.sampling_rate = frequency * 100
            self._set_msystem_settings(settings)

    def _on_voltage_radio_button_toggled(self, voltage: float, checked: bool) -> None:
        if checked:
            settings = self._msystem.get_settings()
            settings.max_voltage = voltage
            self._set_msystem_settings(settings)

    def _on_sensitivity_radio_button_toggled(self, resistance: float, checked: bool) -> None:
        if checked:
            settings = self._msystem.get_settings()
            settings.internal_resistance = resistance
            self._set_msystem_settings(settings)

    @pyqtSlot()
    def _on_view_board(self):
        self._board_window.show()

    @pyqtSlot(int)
    def _on_board_pin_selected(self, number: int):
        self._measurement_plan.go_pin(number)
        self._update_current_pin()
