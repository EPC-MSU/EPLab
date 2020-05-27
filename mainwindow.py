from PyQt5.QtWidgets import QMainWindow, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QTimer, QPointF, Qt
from PyQt5 import uic

from warnings import warn
from datetime import datetime

import epcore.filemanager as epfilemanager
from epcore.measurementmanager import MeasurementSystem, MeasurementPlan
from epcore.elements import MeasurementSettings, Board, Pin, Element, IVCurve
from epcore.measurementmanager.ivc_comparator import IVCComparator
from boardwindow import BoardWidget
from ivviewer import Viewer as IVViewer
from score import ScoreWrapper
from ivview_parameters import IVViewerParametersAdjuster
from version import Version
from player import SoundPlayer
from common import WorkMode

from typing import Optional


class EPLabWindow(QMainWindow):
    def __init__(self, msystem: MeasurementSystem):
        super(EPLabWindow, self).__init__()

        uic.loadUi("gui/mainwindow.ui", self)

        self._msystem = msystem
        self._msystem.trigger_measurements()

        self._comparator = IVCComparator()

        self._score_wrapper = ScoreWrapper(self.score_label)

        self._player = SoundPlayer()
        self._player.set_mute(not self.sound_enabled_checkbox.isChecked())

        self.setWindowIcon(QIcon("media/ico.png"))
        self.setWindowTitle(self.windowTitle() + " " + Version.full)

        self._board_window = BoardWidget()
        self._board_window.resize(600, 600)
        self._board_window.setWindowIcon(QIcon("media/ico.png"))
        self._board_window.setWindowTitle("EPLab - Board")

        self._board_window.workspace.point_selected.connect(self._on_board_pin_selected)
        self._board_window.workspace.on_right_click.connect(self._on_board_right_click)
        self._board_window.workspace.point_moved.connect(self._on_board_pin_moved)

        self._iv_window = IVViewer()

        self._iv_window_parameters_adjuster = IVViewerParametersAdjuster(self._iv_window)

        self.setCentralWidget(self._iv_window)

        self._reset_board()
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
            button.toggled.connect(self._on_settings_btn_checked)

        self._voltages = {
            self.voltage_1_2v_radio_button: 1.2,
            self.voltage_3_3v_radio_button: 3.3,
            self.voltage_5v_radio_button: 5.0,
            self.voltage_12v_radio_button: 12.0
        }
        for button, voltage in self._voltages.items():
            button.toggled.connect(self._on_settings_btn_checked)

        self._sensitivities = {
            self.sens_low_radio_button: 47500.0,  # Omh
            self.sens_medium_radio_button: 4750.0,
            self.sens_high_radio_button: 475.0
        }
        for button, resistance in self._sensitivities.items():
            button.toggled.connect(self._on_settings_btn_checked)

        self.zp_push_button_left.clicked.connect(self._on_go_left_pin)
        self.tp_push_button_left.clicked.connect(self._on_go_left_pin)
        self.zp_push_button_right.clicked.connect(self._on_go_right_pin)
        self.tp_push_button_right.clicked.connect(self._on_go_right_pin)
        self.zp_push_button_new_point.clicked.connect(self._on_new_pin)
        self.zp_push_button_save.clicked.connect(self._on_save_pin)
        self.zp_open_file_button.clicked.connect(self._on_load_board)
        self.tp_open_file_button.clicked.connect(self._on_load_board)  # same button on test tab
        self.zp_new_file_button.clicked.connect(self._on_new_board)
        self.zp_save_file_button.clicked.connect(self._on_save_board)
        self.zp_save_file_as_button.clicked.connect(self._on_save_board_as)
        self.zp_add_image_button.clicked.connect(self._on_load_board_image)

        self.sound_enabled_checkbox.stateChanged.connect(self._on_sound_checked)

        self.freeze_curve_a_check_box.stateChanged.connect(self._on_freeze_a)
        self.freeze_curve_b_check_box.stateChanged.connect(self._on_freeze_b)

        if "ref" not in self._msystem.measurers_map:
            self.freeze_curve_a_check_box.setEnabled(False)

        self.save_image_push_button.clicked.connect(self._on_save_image)
        self.tp_push_button_save.clicked.connect(self._on_save_image)

        self.pushButton_score_threshold_minus.clicked.connect(self._on_threshold_dec)
        self.pushButton_score_threshold_plus.clicked.connect(self._on_threshold_inc)

        self.c_push_button_auto_calibration.clicked.connect(self._on_auto_calibration)

        self.test_plan_tab_widget.setCurrentIndex(0)  # first tab - curves comparison
        self.test_plan_tab_widget.currentChanged.connect(self._on_test_plan_tab_switch)

        self._iv_window_parameters_adjuster.adjust_parameters(self._msystem.get_settings())

        self._work_mode = WorkMode.compare  # default mode - compare two curves

        # Update plot settings at next measurement cycle (place settings here or None)
        self._settings_update_next_cycle = None
        # Set to True to skip next measured curves
        self._skip_curve = False

        self._ref_curve = None
        self._test_curve = None

        QTimer.singleShot(0, self._read_curves_periodic_task)

        settings = self._msystem.get_settings()  # set ui settings state to current device
        self._settings_to_ui(settings)

        self._update_current_pin()

        self._update_threshold()

        self._current_file_path = None

    def closeEvent(self, ev):
        self._board_window.close()

    def _change_work_mode(self, mode: WorkMode):
        self._player.set_work_mode(mode)

        if self._work_mode is mode:
            return

        if mode is not WorkMode.compare:
            # "Freeze" is only for compare mode
            self.freeze_curve_a_check_box.setChecked(False)
            self.freeze_curve_b_check_box.setChecked(False)

        # Drag allowed only in write mode
        self._board_window.workspace.allow_drag(mode is WorkMode.write)

        settings_enable = mode is not WorkMode.test  # Disable settings in test mode

        for button in self._voltages:
            button.setEnabled(settings_enable)
        for button in self._frequencies:
            button.setEnabled(settings_enable)
        for button in self._sensitivities:
            button.setEnabled(settings_enable)

        self._work_mode = mode

        self._update_current_pin()

    def _ui_to_settings(self) -> MeasurementSettings:
        """
        Convert UI current RadioButton's states to measurement settings
        :return: Settings
        """
        settings = self._msystem.get_settings()

        for button, value in self._frequencies.items():
            if button.isChecked():
                settings.probe_signal_frequency = value
                settings.sampling_rate = value * 100
        for button, value in self._voltages.items():
            if button.isChecked():
                settings.max_voltage = value
        for button, value in self._sensitivities.items():
            if button.isChecked():
                settings.internal_resistance = value

        return settings

    def _settings_to_ui(self, settings: MeasurementSettings):
        """
        Convert measurement settings to UI RadioButton's states
        :return:
        """
        if settings.probe_signal_frequency not in self._frequencies.values():
            warn(f"No radio button for device frequency {settings.probe_signal_frequency}")
        for button, value in self._frequencies.items():
            if value == settings.probe_signal_frequency:
                button.setChecked(True)

        if settings.internal_resistance not in self._sensitivities.values():
            warn(f"No radio button for device internal resistance {settings.internal_resistance}")
        for button, value in self._sensitivities.items():
            if value == settings.internal_resistance:
                button.setChecked(True)

        if settings.max_voltage not in self._voltages.values():
            warn(f"No radio button for device max voltage {settings.max_voltage}")
        for button, value in self._voltages.items():
            if value == settings.max_voltage:
                button.setChecked(True)

    @pyqtSlot()
    def _on_auto_calibration(self):
        self._msystem.calibrate()

    @pyqtSlot(int)
    def _on_freeze_a(self, state: int):
        if "ref" in self._msystem.measurers_map:
            if state == Qt.Checked:
                self._msystem.measurers_map["ref"].freeze()
            else:
                self._msystem.measurers_map["ref"].unfreeze()

    @pyqtSlot(int)
    def _on_freeze_b(self, state: int):
        if state == Qt.Checked:
            self._msystem.measurers_map["test"].freeze()
        else:
            self._msystem.measurers_map["test"].unfreeze()

    @pyqtSlot(int)
    def _on_sound_checked(self, state: int):
        self._player.set_mute(state != Qt.Checked)

    @pyqtSlot()
    def _on_save_image(self):
        # Freeze image at first
        image = self.grab(self.rect())

        filename = "ivc" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"

        dialog = QFileDialog()
        filename = dialog.getSaveFileName(self, "Save IVC", filter="Image (*.png)", directory=filename)[0]
        if filename:
            if not filename.endswith(".png"):
                filename += ".png"
            image.save(filename)

    @pyqtSlot(int)
    def _on_test_plan_tab_switch(self, index: int):
        tab = self.test_plan_tab_widget.currentWidget().objectName()
        if tab == "test_plan_tab_S":  # compare
            self._change_work_mode(WorkMode.compare)
        elif tab == "test_plan_tab_ZP":  # write
            self._change_work_mode(WorkMode.write)
        elif tab == "test_plan_tab_TP":  # test
            self._change_work_mode(WorkMode.test)
        elif tab == "test_plan_tab_SET":  # settings
            # Settings mode is equal to compare mode, see #39314-9
            self._change_work_mode(WorkMode.compare)

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
        """
        Call this method when current pin index changed
        :return:
        """
        index = self._measurement_plan.get_current_index()
        self.zp_label_num.setText(str(index))
        self.tp_label_num.setText(str(index))
        self._board_window.workspace.select_point(index)

        if self._work_mode in (WorkMode.test, WorkMode.write):
            current_pin = self._measurement_plan.get_current_pin()
            measurement = current_pin.get_reference_measurement()

            if measurement:
                settings = measurement.settings
                self._set_msystem_settings(settings)
                self._settings_to_ui(settings)
                self._update_curves(ref=measurement.ivc)
            else:
                self._remove_ref_curve()
                self._update_curves()

    def _update_threshold(self):
        self.label_score_threshold_value.setText(f"{int(self._score_wrapper.threshold * 100.0)}%")
        self._player.set_threshold(self._score_wrapper.threshold)

    @pyqtSlot()
    def _on_threshold_dec(self):
        self._score_wrapper.decrease_threshold()
        self._update_threshold()

    @pyqtSlot()
    def _on_threshold_inc(self):
        self._score_wrapper.increase_threshold()
        self._update_threshold()

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
            # Place at the center of current viewpoint by default
            width = self._board_window.workspace.width()
            height = self._board_window.workspace.height()
            point = self._board_window.workspace.mapToScene(int(width/2), int(height/2))

            pin = Pin(point.x(),
                      point.y(),
                      measurements=[])
        else:
            pin = Pin(0, 0, measurements=[])

        self._measurement_plan.append_pin(pin)
        self._board_window.add_point(pin.x, pin.y, self._measurement_plan.get_current_index())
        self._update_current_pin()

    @pyqtSlot()
    def _on_save_pin(self):
        """
        Save current pin IVC as reference for current pin
        :return:
        """
        self._measurement_plan.save_last_measurement_as_reference()
        self._update_current_pin()

    def _reset_board(self):
        """
        Set measurement plan to default empty board
        :return:
        """
        # Create default board with 1 pin
        self._measurement_plan = MeasurementPlan(
            Board(elements=[Element(
                pins=[Pin(0, 0, measurements=[])]
            )]
            ),
            measurer=self._msystem.measurers_map["test"]
        )

    @pyqtSlot()
    def _on_new_board(self):
        dialog = QFileDialog()
        filename = dialog.getSaveFileName(self, "Save new board", filter="JSON (*.json)")[0]
        if filename:
            self._current_file_path = filename
            self._reset_board()
            epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            self._board_window.set_board(self._measurement_plan)
            self._update_current_pin()

    @pyqtSlot()
    def _on_save_board_as(self):
        dialog = QFileDialog()
        filename = dialog.getSaveFileName(self, "Save board", filter="JSON (*.json)")[0]
        if filename:
            epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            self._current_file_path = filename

    @pyqtSlot()
    def _on_save_board(self):
        if not self._current_file_path:
            return self._on_save_board_as()
        epfilemanager.save_board_to_ufiv(self._current_file_path, self._measurement_plan)

    @pyqtSlot()
    def _on_load_board(self):
        """
        "Load board" button handler
        :return:
        """
        dialog = QFileDialog()
        filename = dialog.getOpenFileName(self, "Open board", filter="JSON (*.json)")[0]
        if filename:
            self._current_file_path = filename
            board = epfilemanager.load_board_from_ufiv(filename)
            self._measurement_plan = MeasurementPlan(board, measurer=self._msystem.measurers_map["test"])
            self._board_window.set_board(self._measurement_plan)  # New workspace will be created here

            self._update_current_pin()

            if board.image:
                self._board_window.show()

    @pyqtSlot()
    def _on_load_board_image(self):
        """
        "Load board image" button handler
        :return:
        """
        dialog = QFileDialog()
        filename = dialog.getOpenFileName(self, "Open board image", filter="Image Files (*.png *.jpg *.bmp)")[0]
        if filename:
            epfilemanager.add_image_to_ufiv(filename, self._measurement_plan)
            self._board_window.set_board(self._measurement_plan)
            self._update_current_pin()
            self._board_window.show()

    @pyqtSlot()
    def _update_curves(self, test: Optional[IVCurve] = None, ref: Optional[IVCurve] = None):
        # Store last curves
        if test is not None:
            self._test_curve = test
        if ref is not None:
            self._ref_curve = ref

        # Update plots
        self._iv_window.plot.set_test_curve(self._test_curve)
        self._iv_window.plot.set_reference_curve(self._ref_curve)

        # Update score
        if self._ref_curve and self._test_curve:
            score = self._comparator.compare_ivc(self._ref_curve, self._test_curve)
            self._score_wrapper.set_score(score)
            self._player.score_updated(score)

    def _remove_ref_curve(self):
        self._ref_curve = None

    @pyqtSlot()
    def _read_curves_periodic_task(self):
        if self._msystem.measurements_are_ready():
            test = self._msystem.measurers_map["test"].get_last_cached_iv_curve()
            ref = None
            if "ref" in self._msystem.measurers_map:
                ref = self._msystem.measurers_map["ref"].get_last_cached_iv_curve()

            if self._skip_curve:
                self._skip_curve = False
            else:
                if self._work_mode is WorkMode.compare:
                    # Just display two current curves
                    self._update_curves(test, ref)
                else:
                    # Reference curve will be read from measurement plan
                    self._update_curves(test=test)

                if self._settings_update_next_cycle:
                    # New curve with new settings - we must update plot parameters
                    self._iv_window_parameters_adjuster.adjust_parameters(self._settings_update_next_cycle)
                    self._settings_update_next_cycle = None

            self._msystem.trigger_measurements()

        # Add this task to event loop
        QTimer.singleShot(10, self._read_curves_periodic_task)

    def _set_msystem_settings(self, settings: MeasurementSettings):
        self._msystem.set_settings(settings)

        # Skip next measurement because it still have old settings
        self._skip_curve = True

        # When new curve will be received plot parameters will be adjusted
        self._settings_update_next_cycle = settings

    def _on_settings_btn_checked(self, checked: bool) -> None:
        if checked:
            settings = self._ui_to_settings()
            self._set_msystem_settings(settings)

    @pyqtSlot()
    def _on_view_board(self):
        self._board_window.show()

    @pyqtSlot(int)
    def _on_board_pin_selected(self, number: int):
        self._measurement_plan.go_pin(number)
        self._update_current_pin()

    @pyqtSlot(int, QPointF)
    def _on_board_pin_moved(self, number: int, point: QPointF):
        self._measurement_plan.go_pin(number)
        self._measurement_plan.get_current_pin().x = point.x()
        self._measurement_plan.get_current_pin().y = point.y()
