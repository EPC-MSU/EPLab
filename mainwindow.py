from PyQt5.QtWidgets import QMainWindow, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5 import uic

from functools import partial

import epcore.filemanager as epfilemanager
from epcore.measurementmanager import MeasurementSystem
from epcore.elements import IVCurve, MeasurementSettings
from epcore.measurementmanager.ivc_comparator import IVCComparator
from boardwindow import BoardWidget
from boardwindow import GraphicsManualPinItem
from ivviewer import Viewer as IVViewer, Curve as ViewerCurve
from score import ScoreWrapper
from ivview_parameters import IVViewerParametersAdjuster


def _to_viewer_curve(curve: IVCurve) -> ViewerCurve:
    return ViewerCurve(x=curve.voltages, y=curve.currents)


class EPLabWindow(QMainWindow):
    def __init__(self, msystem: MeasurementSystem):
        super(EPLabWindow, self).__init__()

        uic.loadUi("gui/mainwindow.ui", self)

        self._msystem = msystem
        self._msystem.trigger_measurements()

        self._comparator = IVCComparator()

        self._score_wrapper = ScoreWrapper(self.score_label)

        self._board_window = BoardWidget()
        self._board_window.resize(600, 600)
        self._board_window.setWindowIcon(QIcon("media/ico.png"))  # TODO: don't duplicate base configurations
        self._board_window.setWindowTitle("EPLab - Board")        # TODO: don't duplicate base configurations

        self._iv_window = IVViewer()
        self._iv_window.resize(600, 600)
        self._iv_window.setWindowIcon((QIcon("media/ico.png")))   # TODO: don't duplicate base configurations
        self._iv_window.setWindowTitle("EPLab - IVC")             # TODO: don't duplicate base configurations

        self._iv_window_parameters_adjuster = IVViewerParametersAdjuster(self._iv_window)

        self.setCentralWidget(self._iv_window)

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

        self._iv_window_parameters_adjuster.adjust_parameters(self._msystem.get_settings())

        QTimer.singleShot(0, self._update_ivc)

    @pyqtSlot()
    def _update_ivc(self):
        if self._msystem.measurements_are_ready():
            self._msystem.trigger_measurements()

            # Update plot
            # TODO: why [0] measurer is 'ref' and [1] measurer is 'test'? Should be smth like measurers.test
            ref = self._msystem.measurers[0].get_last_iv_curve()
            test = self._msystem.measurers[1].get_last_iv_curve()
            self._iv_window.plot.set_reference_curve(_to_viewer_curve(ref))
            self._iv_window.plot.set_test_curve(_to_viewer_curve(test))

            # Update score
            score = self._comparator.compare_ivc(ref, test)
            self._score_wrapper.set_score(score)

            # Add this task to event loop
            QTimer.singleShot(0, self._update_ivc)

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
    def _on_load_board(self):
        dialog = QFileDialog()
        filename = dialog.getOpenFileName(self, "Open board", filter="JSON (*.json)")[0]
        if filename:
            self._board_window.set_board(epfilemanager.load_board_from_ufiv(filename))
            self._board_window.workspace.on_component_left_click.connect(self._on_component_click)

    @pyqtSlot()
    def _on_view_board(self):
        self._board_window.show()

    @pyqtSlot(GraphicsManualPinItem)
    def _on_component_click(self, component: GraphicsManualPinItem):
        self._point_data_lbl.setText(f"Num: {component.number} x: {component.x()} y: {component.y()}")
