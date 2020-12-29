from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QDialog, QLineEdit, QLabel, QWidget, QVBoxLayout, \
    QHBoxLayout, QToolBar, QGridLayout, QPushButton, QApplication
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import pyqtSlot, QTimer, QPointF, QCoreApplication
from PyQt5 import uic

from warnings import warn
from datetime import datetime
import numpy as np
from PyQt5.QtCore import Qt as QtC
import epcore.filemanager as epfilemanager
from epcore.measurementmanager import MeasurementSystem, MeasurementPlan
from epcore.measurementmanager.utils import search_optimal_settings
from epcore.elements import MeasurementSettings, Board, Pin, Element, IVCurve
from epcore.measurementmanager.ivc_comparator import IVCComparator
from boardwindow import BoardWidget
from ivviewer import Viewer as IVViewer
from score import ScoreWrapper
from ivview_parameters import IVViewerParametersAdjuster
from version import Version
from player import SoundPlayer
from common import WorkMode, DeviceErrorsHandler
from settings.settings import Settings
from settings.settingswindow import SettingsWindow
import os
from typing import Optional
import traceback

ERROR_CODE = -10000


def _(text: str):
    return QCoreApplication.translate("t", text)


def show_exception(f, msg_title, msg_text):
    """
    This wrapper show message if has error
    :param f:
    :param msg_title:
    :param msg_text:
    :return:
    """
    def func(*args, **kwargs):
        try:
            res = f(*args, **kwargs)
            return res
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(msg_title)
            msg.setText(msg_text)
            msg.setInformativeText(str(e)[0:512] + "\n...")
            msg.exec_()
            return ERROR_CODE
    return func


class EPLabWindow(QMainWindow):

    default_path = "../EPLab-Files"

    def __init__(self, msystem: MeasurementSystem):
        super(EPLabWindow, self).__init__()

        uic.loadUi("gui/mainwindow.ui", self)

        self._device_errors_handler = DeviceErrorsHandler()

        self._msystem = msystem

        self._comparator = IVCComparator()
        # Little bit hardcode here. See #39320
        # TODO: separate config file
        # Voltage in Volts, current in mA
        self._comparator.set_min_ivc(0.6, 0.002)

        self._score_wrapper = ScoreWrapper(self.score_label)
        self.__settings = Settings()
        self._player = SoundPlayer()
        self._player.set_mute(not self.sound_enabled_action.isChecked())

        self.setWindowIcon(QIcon("media/ico.png"))
        self.setWindowTitle(self.windowTitle() + " " + Version.full)
        self.move(50, 50)

        self._board_window = BoardWidget()
        self._board_window.resize(600, 600)
        self._board_window.setWindowIcon(QIcon("media/ico.png"))
        self._board_window.setWindowTitle("EPLab - Board")

        self._board_window.workspace.point_selected.connect(self._on_board_pin_selected)
        self._board_window.workspace.on_right_click.connect(self._on_board_right_click)
        self._board_window.workspace.point_moved.connect(self._on_board_pin_moved)
        self.add_cursor_action.toggled.connect(self._on_add_cursor)
        self.remove_cursor_action.toggled.connect(self._on_del_cursor)

        self.plot_parameters()
        self.main_widget = QWidget(self)
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)
        vbox = QVBoxLayout()

        self._iv_window = IVViewer(grid_color=QColor(255, 255, 255),
                                   back_color=QColor(0, 0, 0), solid_axis_enabled=False,
                                   axis_sign_enabled=False)
        self.reference_curve_plot = self._iv_window.plot.add_curve()
        self.test_curve_plot = self._iv_window.plot.add_curve()
        self.reference_curve_plot.set_curve_params(QColor(0, 128, 255, 200))
        self.test_curve_plot.set_curve_params(QColor(255, 0, 0, 200))
        self._iv_window.layout().setContentsMargins(0, 0, 0, 0)
        self._iv_window_parameters_adjuster = IVViewerParametersAdjuster(self._iv_window)
        self.__settings_window = SettingsWindow(self)
        vbox.setSpacing(0)
        vbox.addWidget(self._iv_window)
        vbox.addLayout(self.grid_param)
        hbox = QHBoxLayout(self.main_widget)
        hbox.addLayout(vbox)
        self._reset_board()
        self._board_window.set_board(self._measurement_plan)

        self._frequencies = {
            # Frequency and sampling rate here (freq, sampling rate)
            # self.frequency_1hz_radio_button: (1, 100),
            self.frequency_10hz_radio_button: (10, 1000),
            self.frequency_100hz_radio_button: (100, 10000),
            self.frequency_1khz_radio_button: (1000, 100000),
            self.frequency_10khz_radio_button: (10000, 1000000),
            self.frequency_100khz_radio_button: (100000, 2000000)
        }
        for button, frequency in self._frequencies.items():
            button.clicked.connect(self._on_settings_btn_checked)

        self._voltages = {
            self.voltage_1_2v_radio_button: 1.2,
            self.voltage_3_3v_radio_button: 3.3,
            self.voltage_5v_radio_button: 5.0,
            self.voltage_12v_radio_button: 12.0
        }
        for button, voltage in self._voltages.items():
            button.clicked.connect(self._on_settings_btn_checked)

        self._sensitivities = {
            self.sens_low_radio_button: 475.0,  # Omh
            self.sens_medium_radio_button: 4750.0,
            self.sens_high_radio_button: 47500.0
        }
        for button, resistance in self._sensitivities.items():
            button.clicked.connect(self._on_settings_btn_checked)
        self.num_point_line_edit = QLineEdit(self)
        self.num_point_line_edit.setFixedWidth(40)
        self.num_point_line_edit.setEnabled(False)
        self.toolBar_test.insertWidget(self.next_point_action, self.num_point_line_edit)
        self.num_point_line_edit.returnPressed.connect(self._on_go_selected_pin)
        self.last_point_action.triggered.connect(self._on_go_left_pin)
        self.next_point_action.triggered.connect(self._on_go_right_pin)
        self.new_point_action.triggered.connect(self._on_new_pin)
        self.search_optimal_action.triggered.connect(self._on_search_optimal)
        self.save_point_action.triggered.connect(self._on_save_pin)
        self.open_file_action.triggered.connect(self._on_load_board)  # same button on test tab
        self.new_file_action.triggered.connect(self._on_new_board)
        self.save_file_action.triggered.connect(self._on_save_board)
        self.save_as_file_action.triggered.connect(self._on_save_board_as)
        self.add_board_image_action.triggered.connect(self._on_load_board_image)
        self.open_window_board_action.triggered.connect(self._on_open_board_image)
        self.save_comment_push_button.clicked.connect(self._on_save_comment)
        self.line_comment_pin.returnPressed.connect(self._on_save_comment)
        self.about_action.triggered.connect(self._about_product_message)

        self.sound_enabled_action.toggled.connect(self._on_sound_checked)

        self.freeze_curve_a_action.toggled.connect(self._on_freeze_a)
        self.freeze_curve_b_action.toggled.connect(self._on_freeze_b)
        self.hide_curve_a_action.toggled.connect(self._on_hide_a)
        self.hide_curve_b_action.toggled.connect(self._on_hide_b)

        if "ref" not in self._msystem.measurers_map:
            self.freeze_curve_b_action.setEnabled(False)
            self.hide_curve_b_action.setEnabled(False)

        self.save_screen_action.triggered.connect(self._on_save_image)

        self.comparing_mode_action.triggered.connect(lambda: self._on_work_mode_switch(WorkMode.compare))
        self.writing_mode_action.triggered.connect(lambda: self._on_work_mode_switch(WorkMode.write))
        self.testing_mode_action.triggered.connect(lambda: self._on_work_mode_switch(WorkMode.test))
        self.settings_mode_action.triggered.connect(self._show_settings_window)
        with self._device_errors_handler:
            for m in self._msystem.measurers:
                m.open_device()

        with self._device_errors_handler:
            self._iv_window_parameters_adjuster.adjust_parameters(self._msystem.get_settings())

        self._work_mode = None
        self._change_work_mode(WorkMode.compare)  # default mode - compare two curves

        # Update plot settings at next measurement cycle (place settings here or None)
        self._settings_update_next_cycle = None
        # Set to True to skip next measured curves
        self._skip_curve = False
        self._hide_curve_test = False
        self._hide_curve_ref = False
        self._ref_curve = None
        self._test_curve = None

        QTimer.singleShot(0, self._periodic_task)

        with self._device_errors_handler:
            settings = self._msystem.get_settings()  # set ui settings state to current device
            self._settings_to_ui(settings)

        self._update_current_pin()
        self._update_threshold()

        with self._device_errors_handler:
            self._msystem.trigger_measurements()

        self._current_file_path = None

    def _get_min_var(self):
        """
        Retrun "noise" amplitude for
        specified mode.
        """
        s = self._ui_to_settings()

        # Default values
        var_v = s.max_voltage / 20
        var_c = s.max_voltage / (s.internal_resistance * 20)

        # Magic redefinitions for specific modes
        if (np.isclose(s.max_voltage, 12) and np.isclose(s.internal_resistance, 475)):
            var_v = 0.6
            var_c = 0.008
        elif (np.isclose(s.max_voltage, 5) and np.isclose(s.internal_resistance, 475)):
            var_v = 0.6
            var_c = 0.008
        elif (np.isclose(s.max_voltage, 3.3) and np.isclose(s.internal_resistance, 475)):
            var_v = 0.3
            var_c = 0.008
        elif (np.isclose(s.max_voltage, 1.2) and np.isclose(s.internal_resistance, 475)):
            var_v = 0.3
            var_c = 0.008
        elif (np.isclose(s.max_voltage, 12) and np.isclose(s.internal_resistance, 4750)):
            var_v = 0.6
            var_c = 0.0005
        elif (np.isclose(s.max_voltage, 5) and np.isclose(s.internal_resistance, 4750)):
            var_v = 0.3
            var_c = 0.0005
        elif (np.isclose(s.max_voltage, 3.3) and np.isclose(s.internal_resistance, 4750)):
            var_v = 0.3
            var_c = 0.0005
        elif (np.isclose(s.max_voltage, 1.2) and np.isclose(s.internal_resistance, 4750)):
            var_v = 0.3
            var_c = 0.0005
        elif (np.isclose(s.max_voltage, 12) and np.isclose(s.internal_resistance, 47500)):
            var_v = 0.6
            var_c = 0.00005
        elif (np.isclose(s.max_voltage, 5) and np.isclose(s.internal_resistance, 47500)):
            var_v = 0.3
            var_c = 0.00005
        elif (np.isclose(s.max_voltage, 3.3) and np.isclose(s.internal_resistance, 47500)):
            var_v = 0.3
            var_c = 0.00005
        elif (np.isclose(s.max_voltage, 1.2) and np.isclose(s.internal_resistance, 47500)):
            var_v = 0.3
            var_c = 0.00005

        return (var_v, var_c)

    def _calculate_score(self, curve_1: IVCurve, curve_2: IVCurve) -> float:
        var_v, var_c = self._get_min_var()
        self._comparator.set_min_ivc(var_v, var_c)  # It is very important to set relevant noise levels
        score = self._comparator.compare_ivc(self._ref_curve, self._test_curve)
        return score

    def closeEvent(self, ev):
        self._board_window.close()

    def _change_work_mode(self, mode: WorkMode):
        self._player.set_work_mode(mode)

        if self._work_mode is mode:
            return

        # Comment is only for test and write mode
        self.line_comment_pin.setEnabled(mode is not WorkMode.compare)

        if mode is WorkMode.compare:
            # Remove reference curve in case we have only one IVMeasurer
            # in compare mode
            if len(self._msystem.measurers_map) < 2:
                self._remove_ref_curve()

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
        # settings = self._msystem.get_settings() # Cause an error of different settings. #TODO: find out why.
        settings = self._msystem.measurers[0].get_settings()

        for button, (freq, sampling) in self._frequencies.items():
            if button.isChecked():
                settings.probe_signal_frequency = freq
                settings.sampling_rate = sampling
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
        if (settings.probe_signal_frequency, settings.sampling_rate) not in self._frequencies.values():
            warn(f"No radio button for device frequency {settings.probe_signal_frequency} sampling rate "
                 f"{settings.sampling_rate}")
        for button, (freq, sampling) in self._frequencies.items():
            if np.isclose(freq, settings.probe_signal_frequency, atol=0.01):
                button.setChecked(True)

        if settings.internal_resistance not in self._sensitivities.values():
            warn(f"No radio button for device internal resistance {settings.internal_resistance}")
        for button, value in self._sensitivities.items():
            if np.isclose(value, settings.internal_resistance, atol=0.01):
                button.setChecked(True)

        if settings.max_voltage not in self._voltages.values():
            warn(f"No radio button for device max voltage {settings.max_voltage}")
        for button, value in self._voltages.items():
            if np.isclose(value, settings.max_voltage, atol=0.01):
                button.setChecked(True)

    def _open_board_window_if_needed(self):
        if self._measurement_plan.image:
            self._board_window.show()

    @pyqtSlot(bool)
    def _on_add_cursor(self, state):
        if state:
            self.remove_cursor_action.setChecked(False)
        self._iv_window.plot.set_state_adding_cursor(state)

    @pyqtSlot(bool)
    def _on_del_cursor(self, state):
        if state:
            self.add_cursor_action.setChecked(False)
        self._iv_window.plot.set_state_removing_cursor(state)

    @pyqtSlot()
    def _on_open_board_image(self):
        self._open_board_window_if_needed()
        if not self._measurement_plan.image:
            msg = QMessageBox()
            msg.setWindowTitle(_("Открытие изображения платы"))
            msg.setText("Для данной платы изображение не задано!")
            msg.exec_()

    @pyqtSlot()
    def _on_auto_calibration(self):
        with self._device_errors_handler:
            self._msystem.calibrate()

    @pyqtSlot(bool)
    def _on_hide_b(self, state: bool):
        self._hide_curve_ref = state

    @pyqtSlot(bool)
    def _on_hide_a(self, state: bool):
        self._hide_curve_test = state

    @pyqtSlot(bool)
    def _on_freeze_b(self, state: bool):
        if "ref" in self._msystem.measurers_map:
            if state:
                self._msystem.measurers_map["ref"].freeze()
            else:
                self._msystem.measurers_map["ref"].unfreeze()

    @pyqtSlot()
    def _on_search_optimal(self):
        with self._device_errors_handler:
            optimal_settings = search_optimal_settings(self._msystem.measurers[0])
            self._set_msystem_settings(optimal_settings)
            self._settings_to_ui(optimal_settings)

    @pyqtSlot(bool)
    def _on_freeze_a(self, state: bool):
        if state:
            self._msystem.measurers_map["test"].freeze()
        else:
            self._msystem.measurers_map["test"].unfreeze()

    @pyqtSlot(bool)
    def _on_sound_checked(self, state: bool):
        self._player.set_mute(not state)

    @pyqtSlot(bool)
    def _about_product_message(self):
        def msgbtn(i):
            if i.text() == "Перейти" or i.text() == "Go":
                import webbrowser
                webbrowser.open_new_tab("http://eyepoint.physlab.ru")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(_("Справка"))
        msg.setText(self.windowTitle())
        msg.setInformativeText(_("Программное обеспечение для работы с устройствами линейки EyePoint, предназначенными "
                                 "для поиска неисправностей на печатных платах в ручном режиме (при помощи ручных "
                                 "щупов). Для более подробной информации об Eyepoint, перейдите по ссылке "
                                 "http://eyepoint.physlab.ru."))
        msg.addButton(_("Перейти"), QMessageBox.YesRole)
        msg.addButton(_("ОК"), QMessageBox.NoRole)
        msg.buttonClicked.connect(msgbtn)
        msg.exec_()

    @pyqtSlot()
    def _on_save_comment(self):
        comment = self.line_comment_pin.text()
        self._measurement_plan.get_current_pin().comment = comment

    def _update_threshold(self):
        self.__settings_window.score_treshold_value_lineEdit.setText(f"{round(self._score_wrapper.threshold * 100.0)}%")
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
    def _on_threshold_set_value(self):
        value = float(int(self.__settings_window.score_treshold_value_lineEdit.text()[:-1]) / 100.0)
        self._score_wrapper.set_threshold(value)
        self._update_threshold()

    @pyqtSlot()
    def _show_settings_window(self):
        self.__settings_window.open()

    @pyqtSlot()
    def _on_save_image(self):
        # Freeze image at first
        image = self.grab(self.rect())

        filename = "eplab_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"

        if not os.path.isdir(self.default_path):
            os.mkdir(self.default_path)
        if not os.path.isdir(os.path.join(self.default_path, "Screenshot")):
            os.mkdir(os.path.join(self.default_path, "Screenshot"))

        dialog = QFileDialog()
        filename = dialog.getSaveFileName(self, _("Сохранить ВАХ"), filter="Image (*.png)",
                                          directory=os.path.join(self.default_path, "Screenshot", filename))[0]
        if filename:
            if not filename.endswith(".png"):
                filename += ".png"
            image.save(filename)

    @pyqtSlot()
    def _on_open_settings(self):
        settings_path = QFileDialog(self).getOpenFileName(self, "Open file", ".", "Ini file (*.ini);;All Files (*)")[0]
        if len(settings_path) == 0:
            return

        self.__settings.import_(path=settings_path)
        self._load_settings()

    def _load_settings(self):
        self._on_work_mode_switch(self.__settings.work_mode)
        for button, voltage in self._voltages.items():
            if voltage == self.__settings.max_voltage:
                button.setChecked(True)
        for button, frequency in self._frequencies.items():
            if frequency == self.__settings.frequency:
                button.setChecked(True)
        for button, sensitivity in self._sensitivities.items():
            if sensitivity == self.__settings.internal_resistance:
                button.setChecked(True)
        self.__settings_window.score_treshold_value_lineEdit.setText(f"{round(self.__settings.score_threshold * 100.0)}"
                                                                     f"%")
        self.hide_curve_a_action.setChecked(self.__settings.hide_curve_a)
        self.hide_curve_b_action.setChecked(self.__settings.hide_curve_b)
        self.sound_enabled_action.setChecked(self.__settings.sound_enabled)

    def _store_settings(self, settings=None):
        if settings is None:
            settings = self.__settings
        for button, voltage in self._voltages.items():
            if button.isChecked():
                settings.max_voltage = voltage
        for button, frequency in self._frequencies.items():
            if button.isChecked():
                settings.frequency = frequency
        for button, sensitivity in self._sensitivities.items():
            if button.isChecked():
                settings.internal_resistance = sensitivity
        if self.testing_mode_action.isChecked():
            settings.work_mode = WorkMode.test
        elif self.writing_mode_action.isChecked():
            settings.work_mode = WorkMode.write
        else:
            settings.work_mode = WorkMode.compare
        settings.score_threshold = float(int(self.__settings_window.score_treshold_value_lineEdit.text()[:-1]) / 100.0)
        settings.hide_curve_a = bool(self.hide_curve_a_action.isChecked())
        settings.hide_curve_b = bool(self.hide_curve_b_action.isChecked())
        settings.sound_enabled = bool(self.sound_enabled_action.isChecked())

    @pyqtSlot()
    def _save_settings_to_file(self):
        settings_path = QFileDialog(self).getSaveFileName(self, "Save file", ".", "Ini file (*.ini);;All Files (*)")[0]
        if len(settings_path) == 0:
            return

        if not settings_path.endswith(".ini"):
            settings_path += ".ini"

        settings = Settings()
        self._store_settings(settings)
        settings.export(path=settings_path)

    @pyqtSlot(bool)
    def _on_work_mode_switch(self, mode: WorkMode):
        self.comparing_mode_action.setChecked(mode is WorkMode.compare)
        self.writing_mode_action.setChecked(mode is WorkMode.write)
        self.testing_mode_action.setChecked(mode is WorkMode.test)
        self.next_point_action.setEnabled(mode is not WorkMode.compare)
        self.last_point_action.setEnabled(mode is not WorkMode.compare)
        self.num_point_line_edit.setEnabled(mode is not WorkMode.compare)
        self.new_point_action.setEnabled(mode is WorkMode.write)
        self.save_point_action.setEnabled(mode is WorkMode.write)
        self.add_board_image_action.setEnabled(mode is WorkMode.write)
        self._change_work_mode(mode)

    @pyqtSlot(QPointF)
    def _on_board_right_click(self, point: QPointF):
        if self._work_mode is WorkMode.write:
            # Create new pin
            pin = Pin(x=point.x(), y=point.y(), measurements=[])
            self._measurement_plan.append_pin(pin)
            self._board_window.add_point(pin.x, pin.y, self._measurement_plan.get_current_index())
            self._update_current_pin()

    def _set_comment(self):
        comment = self.line_comment_pin.text()
        self._measurement_plan.get_current_pin().comment = comment
        self.line_comment_pin.setText(self._measurement_plan.get_current_pin().comment or "")

    @pyqtSlot()
    def _update_current_pin(self):
        """
        Call this method when current pin index changed
        :return:
        """
        index = self._measurement_plan.get_current_index()
        self.num_point_line_edit.setText(str(index))
        self._board_window.workspace.select_point(index)

        if self._work_mode in (WorkMode.test, WorkMode.write):
            current_pin = self._measurement_plan.get_current_pin()
            measurement = current_pin.get_reference_measurement()
            self.line_comment_pin.returnPressed.connect(self._set_comment)
            self.line_comment_pin.setText(current_pin.comment or "")

            if measurement:
                with self._device_errors_handler:
                    settings = measurement.settings
                    self._set_msystem_settings(settings)
                    self._settings_to_ui(settings)
                    self._update_curves(ref=measurement.ivc, settings=self._msystem.measurers[0].get_settings())
            else:
                self._remove_ref_curve()
                self._update_curves(settings=self._msystem.measurers[0].get_settings())

    @pyqtSlot()
    def _on_go_selected_pin(self):
        str_to_int = show_exception(int, _("Ошибка открытия точки"), _("Неверный формат номера точки. Номер точки может"
                                                                       " принимать только целочисленное значение!"))
        num_point = str_to_int(self.num_point_line_edit.text())
        if num_point == ERROR_CODE:
            return
        go_pin = show_exception(self._measurement_plan.go_pin, _("Ошибка открытия точки"),
                                _("Точка с таким номером не найдена на данной плате."))
        status = go_pin(num_point)
        if status == ERROR_CODE:
            return
        self._update_current_pin()
        self._open_board_window_if_needed()

    @pyqtSlot()
    def _on_go_left_pin(self):
        self._measurement_plan.go_prev_pin()
        self._update_current_pin()
        self._open_board_window_if_needed()

    @pyqtSlot()
    def _on_go_right_pin(self):
        self._measurement_plan.go_next_pin()
        self._update_current_pin()
        self._open_board_window_if_needed()

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
        self.line_comment_pin.setText(pin.comment or "")

        # It is important to initialize pin with real measurement.
        # Otherwise user can create several empty points and they will not be unique.
        # This will cause some errors during ufiv validation.
        self._on_save_pin()
        self._update_current_pin()

    @pyqtSlot()
    def _on_save_pin(self):
        """
        Save current pin IVC as reference for current pin
        :return:
        """
        with self._device_errors_handler:
            self._measurement_plan.save_last_measurement_as_reference()
        self._set_comment()
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
        if self._current_file_path is not None:
            d = QDialog()
            label = QLabel("Сохранить изменеия в файл?")
            btn_yes = QPushButton("Да")
            btn_no = QPushButton("Нет")
            btn_cancel = QPushButton("Отмена")
            layout = QVBoxLayout(d)
            hl = QHBoxLayout(d)
            layout.addWidget(label)
            hl.addWidget(btn_yes)
            hl.addWidget(btn_no)
            hl.addWidget(btn_cancel)
            layout.addLayout(hl)
            btn_yes.clicked.connect(d.accept)
            btn_no.clicked.connect(lambda: d.done(1))
            btn_cancel.clicked.connect(d.reject)
            d.setWindowTitle("Внимание")
            d.setWindowModality(QtC.ApplicationModal)
            resp = d.exec()
            if resp == QDialog.Accepted:
                self._on_save_board()
            elif resp == QDialog.Rejected:
                return
        if not os.path.isdir(self.default_path):
            os.mkdir(self.default_path)
        if not os.path.isdir(os.path.join(self.default_path, "Reference")):
            os.mkdir(os.path.join(self.default_path, "Reference"))
        dialog = QFileDialog()
        filename = dialog.getSaveFileName(self, _("Создать новую плату"), filter="UFIV Archived File (*.uzf)",
                                          directory=os.path.join(self.default_path, "Reference", "board.uzf"))[0]
        if filename:
            self._current_file_path = filename
            self._reset_board()
            epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            self._board_window.set_board(self._measurement_plan)
            self._update_current_pin()

    @pyqtSlot()
    def _on_save_board_as(self):
        if not os.path.isdir(self.default_path):
            os.mkdir(self.default_path)
        if not os.path.isdir(os.path.join(self.default_path, "Reference")):
            os.mkdir(os.path.join(self.default_path, "Reference"))
        dialog = QFileDialog()
        filename = dialog.getSaveFileName(self, _("Сохранить плату"), filter="UFIV Archived File (*.uzf)",
                                          directory=os.path.join(self.default_path, "Reference", "board.uzf"))[0]
        if filename:
            epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            self._current_file_path = filename
        elif self._current_file_path is None:
            self._current_file_path = os.path.join(self.default_path, "Reference", "board.uzf")
            epfilemanager.save_board_to_ufiv(self._current_file_path, self._measurement_plan)
        load_file = show_exception(epfilemanager.load_board_from_ufiv, _("Ошибка"),
                                   _("Неверный формат сохраняемого файла"))
        load_file(self._current_file_path)

    @pyqtSlot()
    def _on_save_board(self):
        if not self._current_file_path:
            return self._on_save_board_as()
        epfilemanager.save_board_to_ufiv(self._current_file_path, self._measurement_plan)
        load_file = show_exception(epfilemanager.load_board_from_ufiv, _("Ошибка"),
                                   _("Неверный формат сохраняемого файла"))
        load_file(self._current_file_path)

    @pyqtSlot()
    def _on_load_board(self):
        """
        "Load board" button handler
        :return:
        """
        dialog = QFileDialog()
        filename = dialog.getOpenFileName(self, _("Открыть плату"),
                                          filter="Board Files (*.json *.uzf)")[0]
        if filename:
            self._current_file_path = filename
            load_file = show_exception(epfilemanager.load_board_from_ufiv, _("Ошибка"), _("Формат файла не подходит"))
            board = load_file(filename, auto_convert_p10=True)
            if board == ERROR_CODE:
                return

            self._measurement_plan = MeasurementPlan(board, measurer=self._msystem.measurers_map["test"])
            self._board_window.set_board(self._measurement_plan)  # New workspace will be created here

            self._update_current_pin()
            self._open_board_window_if_needed()

    @pyqtSlot()
    def _on_load_board_image(self):
        """
        "Load board image" button handler
        :return:
        """
        dialog = QFileDialog()
        filename = dialog.getOpenFileName(self, _("Открыть изображение платы"),
                                          filter="Image Files (*.png *.jpg *.bmp)")[0]
        if filename:
            epfilemanager.add_image_to_ufiv(filename, self._measurement_plan)
            self._board_window.set_board(self._measurement_plan)
            self._update_current_pin()
            self._open_board_window_if_needed()

    @pyqtSlot()
    def _update_curves(self, test: Optional[IVCurve] = None, ref: Optional[IVCurve] = None, settings=None):
        # Store last curves
        if test is not None:
            self._test_curve = test
        if ref is not None:
            self._ref_curve = ref
        # Update plots
        if not self._hide_curve_test:
            self.test_curve_plot.set_curve(self._test_curve)
        else:
            self.test_curve_plot.set_curve(None)
        if not self._hide_curve_ref:
            self.reference_curve_plot.set_curve(self._ref_curve)
        else:
            self.reference_curve_plot.set_curve(None)

        # Update score
        if self._ref_curve and self._test_curve:
            score = self._calculate_score(self._ref_curve, self._test_curve)
            self._score_wrapper.set_score(score)
            self._player.score_updated(score)
            score = str(round(score * 100.0)) + "%"
        else:
            score = "-"
            self._score_wrapper.set_dummy_score()
        _v, _c = self._iv_window.plot.get_minor_axis_step()
        if settings is not None:
            sensity = [button.text() for button in self._sensitivities.keys() if self._sensitivities[button] ==
                       settings.internal_resistance]
            sensity = sensity[0]
            max_v = np.round(settings.max_voltage, 1)
            probe_freq = np.round(settings.probe_signal_frequency, 1)
        else:
            sensity = "-"
            max_v = "-"
            probe_freq = "-"
        self._param_dict["Напряжение"].setText(_("  Напряжение: ") + str(_v) +
                                               _(" В / дел."))
        self._param_dict["Ампл. проб. сигнала"].setText(_("Ампл. проб. сигнала: ") +
                                                        str(max_v) +
                                                        _(" B"))
        self._param_dict["Частота"].setText(_("Частота: ") +
                                            str(probe_freq) +
                                            _(" Гц"))
        self._param_dict["Ток"].setText(_("  Ток: ") + str(_c) +
                                        _(" мА / дел."))
        self._param_dict["Чувствительность"].setText(_("Чувствительность: ") +
                                                     str(sensity))
        self._param_dict["Различие"].setText(_("Различие: ") + score)

    def plot_parameters(self):
        self._param_dict = {"Напряжение": QLabel(self), "Ампл. проб. сигнала": QLabel(self), "Частота": QLabel(self),
                            "Ток": QLabel(self), "Чувствительность": QLabel(self), "Различие": QLabel(self)}
        self.grid_param = QGridLayout()
        positions = [(i, j) for i in range(2) for j in range(3)]
        for position, name in zip(positions, self._param_dict.keys()):
            tb = QToolBar()
            tb.setFixedHeight(30)
            tb.setStyleSheet("background:black; color:white;spacing:10;")
            tb.addWidget(self._param_dict[name])
            self.grid_param.addWidget(tb, *position)

    def _remove_ref_curve(self):
        self._ref_curve = None

    def _reconnect_periodic_task(self):
        # Draw empty curves
        self._test_curve = None
        if self._work_mode is WorkMode.compare:
            self._ref_curve = None
        self._update_curves()
        self.reference_curve_plot.set_curve(None)
        self.test_curve_plot.set_curve(None)
        # Draw text
        self._iv_window.plot.set_center_text(_("НЕТ ПОДКЛЮЧЕНИЯ"))

        if self._msystem.reconnect():
            # Reconnection success!
            self._device_errors_handler.reset_error()
            self._iv_window.plot.clear_center_text()
            with self._device_errors_handler:
                # Update current settings to reconnected device
                settings = self._ui_to_settings()
                self._set_msystem_settings(settings)
                self._msystem.trigger_measurements()

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
                    self._update_curves(test, ref, settings=self._msystem.measurers[0].get_settings())
                else:
                    # Reference curve will be read from measurement plan
                    self._update_curves(test=test, settings=self._msystem.measurers[0].get_settings())

                if self._settings_update_next_cycle:
                    # New curve with new settings - we must update plot parameters
                    self._iv_window_parameters_adjuster.adjust_parameters(self._settings_update_next_cycle)
                    self._settings_update_next_cycle = None

            self._msystem.trigger_measurements()

    @pyqtSlot()
    def _periodic_task(self):
        if self._device_errors_handler.all_ok:
            with self._device_errors_handler:
                self._read_curves_periodic_task()
        else:
            self._reconnect_periodic_task()
        # Add this task to event loop
        QTimer.singleShot(10, self._periodic_task)

    def _set_msystem_settings(self, settings: MeasurementSettings):
        self._msystem.set_settings(settings)

        # Skip next measurement because it still have old settings
        self._skip_curve = True

        # When new curve will be received plot parameters will be adjusted
        self._settings_update_next_cycle = settings

    def _on_settings_btn_checked(self, checked: bool) -> None:
        if checked:
            with self._device_errors_handler:
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


tb = None


def excepthook(exc_type, exc_value, exc_tb):
    global tb
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("error catched!:")
    print("error message:\n", tb)
    QApplication.quit()
