from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QDialog, QLineEdit, QLabel, QWidget, QVBoxLayout, \
    QHBoxLayout, QPushButton, QRadioButton
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import pyqtSlot, QTimer, QPointF, QCoreApplication as qApp
from PyQt5 import uic

from datetime import datetime
import numpy as np
from PyQt5.QtCore import Qt as QtC
import epcore.filemanager as epfilemanager
from epcore.measurementmanager import MeasurementSystem, MeasurementPlan
from epcore.measurementmanager.utils import Searcher
from epcore.elements import MeasurementSettings, Board, Pin, Element, IVCurve
from epcore.measurementmanager.ivc_comparator import IVCComparator
from epcore.product import EPLab
from boardwindow import BoardWidget
from ivviewer import Viewer as IVViewer
from score import ScoreWrapper
from version import Version
from player import SoundPlayer
from common import WorkMode, DeviceErrorsHandler
from language import Language
from settings.settings import Settings
from settings.settingswindow import SettingsWindow, LowSettingsPanel
import os
from typing import Dict

# TODO: is that C-style error code? Refactor!
ERROR_CODE = -10000


def show_exception(f, msg_title, msg_text):
    """
    Wrapper show message box if wrapped function terminates with error.
    :param f: wrapped function;
    :param msg_title: title of message box;
    :param msg_text: message text.
    """

    def func(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(msg_title)
            msg.setText(msg_text)
            # TODO: remove hardcoded constant parameter
            msg.setInformativeText(str(e)[0:512] + "\n...")
            msg.exec_()
            return ERROR_CODE

    return func


class EPLabWindow(QMainWindow):
    default_path = "../EPLab-Files"

    def __init__(self, msystem: MeasurementSystem, product: EPLab):
        super(EPLabWindow, self).__init__()

        uic.loadUi("gui/mainwindow.ui", self)

        self._device_errors_handler = DeviceErrorsHandler()

        self._msystem = msystem

        self._product = product

        self._comparator = IVCComparator()
        # Little bit hardcode here. See #39320
        # TODO: separate config file
        # Voltage in Volts, current in mA
        self._comparator.set_min_ivc(0.6, 0.002)

        self._score_wrapper = ScoreWrapper(self.score_label)
        self.__settings: Settings = None
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

        self.low_panel_settings = LowSettingsPanel(self)
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
        self.__settings_window = SettingsWindow(self)
        vbox.setSpacing(0)
        vbox.addWidget(self._iv_window)
        vbox.addLayout(self.grid_param)
        hbox = QHBoxLayout(self.main_widget)
        hbox.addLayout(vbox)
        self._reset_board()
        self._board_window.set_board(self._measurement_plan)

        self._option_buttons = {
            EPLab.Parameter.frequency: dict(),
            EPLab.Parameter.voltage: dict(),
            EPLab.Parameter.sensitive: dict()
        }

        lang = qApp.instance().property("language")

        for option in self._product.mparams[EPLab.Parameter.frequency].options:
            button = QRadioButton()
            self.freqLayout.layout().addWidget(button)
            button.setText(option.label_ru if lang == Language.ru else option.label_en)
            button.clicked.connect(self._on_settings_btn_checked)
            self._option_buttons[EPLab.Parameter.frequency][option.name] = button

        for option in self._product.mparams[EPLab.Parameter.voltage].options:
            button = QRadioButton()
            self.voltageLayout.layout().addWidget(button)
            button.setText(option.label_ru if lang == Language.ru else option.label_en)
            button.clicked.connect(self._on_settings_btn_checked)
            self._option_buttons[EPLab.Parameter.voltage][option.name] = button

        for option in self._product.mparams[EPLab.Parameter.sensitive].options:
            button = QRadioButton()
            self.currentLayout.layout().addWidget(button)
            button.setText(option.label_ru if lang == Language.ru else option.label_en)
            button.clicked.connect(self._on_settings_btn_checked)
            self._option_buttons[EPLab.Parameter.sensitive][option.name] = button

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

        if len(self._msystem.measurers) < 2:
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
            self._adjust_plot_params(self._msystem.get_settings())

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
            options = self._product.settings_to_options(settings)
            self._options_to_ui(options)

        self._update_current_pin()
        self._init_threshold()

        with self._device_errors_handler:
            self._msystem.trigger_measurements()

        self._current_file_path = None

    def _ui_to_options(self) -> Dict:
        """
        Get current options state from ui.
        """

        def _get_checked_button(buttons: Dict) -> str:
            for name, button in buttons.items():
                if button.isChecked():
                    return name

        return {
            param: _get_checked_button(self._option_buttons[param]) for param in self._option_buttons
        }

    def _options_to_ui(self, options: Dict[EPLab.Parameter, str]):
        """
        Convert options to us state.
        """
        for group in options.keys():
            self._option_buttons[group][options[group]].setChecked(True)

    def _get_min_var(self, settings: MeasurementSettings):
        """
        Return "noise" amplitude for specified mode.
        """
        return self._product.adjust_noise_amplitude(settings)

    def _calculate_score(self, curve_1: IVCurve, curve_2: IVCurve, settings: MeasurementSettings) -> float:
        var_v, var_c = self._get_min_var(settings)
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
            if len(self._msystem.measurers) < 2:
                self._remove_ref_curve()

        # Drag allowed only in write mode
        self._board_window.workspace.allow_drag(mode is WorkMode.write)

        settings_enable = mode is not WorkMode.test  # Disable settings in test mode

        for group in self._option_buttons.values():
            for button in group.values():
                button.setEnabled(settings_enable)

        self._work_mode = mode

        self._update_current_pin()

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
            msg.setWindowTitle(qApp.translate("t", "Открытие изображения платы"))
            msg.setText(qApp.translate("t", "Для данной платы изображение не задано!"))
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

    @pyqtSlot()
    def _on_search_optimal(self):
        with self._device_errors_handler:
            searcher = Searcher(self._msystem.measurers[0], self._product.mparams)
            optimal_settings = searcher.search_optimal_settings()
            self._set_msystem_settings(optimal_settings)
            options = self._product.settings_to_options(optimal_settings)
            self._options_to_ui(options)

    def _freeze_measurer(self, measurer_id: int, state: bool):
        if measurer_id < len(self._msystem.measurers):
            if state:
                self._msystem.measurers[measurer_id].freeze()
            else:
                self._msystem.measurers[measurer_id].unfreeze()

    @pyqtSlot(bool)
    def _on_freeze_a(self, state: bool):
        self._freeze_measurer(0, state)

    @pyqtSlot(bool)
    def _on_freeze_b(self, state: bool):
        self._freeze_measurer(1, state)

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
        msg.setWindowTitle(qApp.translate("t", "Справка"))
        msg.setText(self.windowTitle())
        msg.setInformativeText(qApp.translate("t", "Программное обеспечение для работы с устройствами линейки EyePoint,"
                                                   " предназначенными для поиска неисправностей на печатных платах в "
                                                   "ручном режиме (при помощи ручных щупов). Для более подробной "
                                                   "информации об Eyepoint, перейдите по ссылке "
                                                   "http://eyepoint.physlab.ru."))
        msg.addButton(qApp.translate("t", "Перейти"), QMessageBox.YesRole)
        msg.addButton(qApp.translate("t", "ОК"), QMessageBox.NoRole)
        msg.buttonClicked.connect(msgbtn)
        msg.exec_()

    @pyqtSlot()
    def _on_save_comment(self):
        comment = self.line_comment_pin.text()
        self._measurement_plan.get_current_pin().comment = comment

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
        filename = dialog.getSaveFileName(self, qApp.translate("t", "Сохранить ВАХ"), filter="Image (*.png)",
                                          directory=os.path.join(self.default_path, "Screenshot", filename))[0]
        if filename:
            if not filename.endswith(".png"):
                filename += ".png"
            image.save(filename)

    @pyqtSlot()
    def _show_settings_window(self):
        """
        The method is called when you click on 'Settings' button, it shows
        settings window.
        """

        self._update_threshold_in_settings_wnd(self._score_wrapper.threshold)
        self.__settings_window.open()
        self.__settings = None

    def _get_threshold_value(self) -> float:
        """
        The method returns value of score threshold from
        score_threshold_value_lineEdit in settings window.
        :return: score threshold value.
        """

        value = self.__settings_window.score_treshold_value_lineEdit.text()
        if not value:
            value = 0
        elif value[-1] == "%":
            value = value[:-1]
        return float(int(value) / 100.0)

    def _init_threshold(self):
        """
        The method initializes initial value (50%) of score threshold.
        """

        threshold = self._score_wrapper.threshold
        self._update_threshold_in_settings_wnd(threshold)
        self._update_threshold(threshold)

    @pyqtSlot()
    def _load_settings(self):
        """
        The method is called when you click on the 'Apply' button in the
        settings window.
        """

        threshold = self._get_threshold_value()
        if (self.__settings is None or
                (self.__settings and self.__settings.score_threshold != threshold)):
            # Settings were not loaded from file
            self._update_threshold(threshold)
            return
        # Settings were loaded from file
        self._on_work_mode_switch(self.__settings.work_mode)
        settings = self.__settings.measurement_settings()
        options = self._product.settings_to_options(settings)
        self._options_to_ui(options)
        self._set_msystem_settings(settings)
        self.hide_curve_a_action.setChecked(self.__settings.hide_curve_a)
        self.hide_curve_b_action.setChecked(self.__settings.hide_curve_b)
        self.sound_enabled_action.setChecked(self.__settings.sound_enabled)
        self._update_threshold(self.__settings.score_threshold)

    @pyqtSlot()
    def _on_open_settings(self):
        """
        The method is called when you click on the 'Load settings' button in
        the settings window.
        """

        settings_path = QFileDialog(self).getOpenFileName(
            self, qApp.translate("t", "Открыть файл"), ".",
            "Ini file (*.ini);;All Files (*)")[0]
        if len(settings_path) == 0:
            return
        self.__settings = Settings()
        self.__settings.import_(path=settings_path)
        self.__settings_window.score_treshold_value_lineEdit.setText(
            f"{round(self.__settings.score_threshold * 100.0)}%")

    @pyqtSlot()
    def _on_threshold_dec(self):
        """
        The method is called when you click on the '-' button in the settings
        window.
        """

        threshold = self._get_threshold_value()
        threshold_step = 0.05
        threshold = max(threshold - threshold_step, 0.0)
        self._update_threshold_in_settings_wnd(threshold)

    @pyqtSlot()
    def _on_threshold_inc(self):
        """
        The method is called when you click on the '+' button in the settings
        window.
        """

        threshold = self._get_threshold_value()
        threshold_step = 0.05
        threshold = min(threshold + threshold_step, 1.0)
        self._update_threshold_in_settings_wnd(threshold)

    @pyqtSlot()
    def _save_settings_to_file(self):
        """
        The method is called when you click on the 'Save settings' button in
        the settings window.
        """

        settings_path = QFileDialog(self).getSaveFileName(
            self, qApp.translate("t", "Сохранить файл"), filter="Ini file (*.ini);;All Files (*)",
            directory="settings.ini")[0]
        if len(settings_path) == 0:
            return
        if not settings_path.endswith(".ini"):
            settings_path += ".ini"
        settings = Settings()
        self._store_settings(settings)
        settings.export(path=settings_path)

    def _store_settings(self, settings: Settings):
        """
        The method stores current applied settings in object.
        :param settings: object to store current settings.
        """

        settings.set_measurement_settings(self._msystem.get_settings())
        if self.testing_mode_action.isChecked():
            settings.work_mode = WorkMode.test
        elif self.writing_mode_action.isChecked():
            settings.work_mode = WorkMode.write
        else:
            settings.work_mode = WorkMode.compare
        settings.score_threshold = self._get_threshold_value()
        settings.hide_curve_a = bool(self.hide_curve_a_action.isChecked())
        settings.hide_curve_b = bool(self.hide_curve_b_action.isChecked())
        settings.sound_enabled = bool(self.sound_enabled_action.isChecked())

    def _update_threshold(self, threshold: float):
        """
        The method updates score threshold value in _score_wrapper and _player.
        :param threshold: score threshold value.
        """

        self._score_wrapper.set_threshold(threshold)
        self._player.set_threshold(threshold)

    def _update_threshold_in_settings_wnd(self, threshold: float):
        """
        The method updates score threshold value in settings window.
        :param threshold: new score threshold value.
        """

        self.__settings_window.score_treshold_value_lineEdit.setText(
            f"{round(threshold * 100.0)}%")

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
        Call this method when current pin index changed.
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
                    options = self._product.settings_to_options(settings)
                    self._options_to_ui(options)
                    self._update_curves({"ref": measurement.ivc}, settings=self._msystem.measurers[0].get_settings())
            else:
                self._remove_ref_curve()
                self._update_curves({}, settings=self._msystem.measurers[0].get_settings())

    @pyqtSlot()
    def _on_go_selected_pin(self):
        str_to_int = show_exception(int, qApp.translate("t", "Ошибка открытия точки"),
                                    qApp.translate("t", "Неверный формат номера точки. Номер точки может"
                                                        " принимать только целочисленное значение!"))
        num_point = str_to_int(self.num_point_line_edit.text())
        if num_point == ERROR_CODE:
            return
        go_pin = show_exception(self._measurement_plan.go_pin, qApp.translate("t", "Ошибка открытия точки"),
                                qApp.translate("t", "Точка с таким номером не найдена на данной плате."))
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
            point = self._board_window.workspace.mapToScene(int(width / 2), int(height / 2))
            pin = Pin(point.x(), point.y(), measurements=[])
        else:
            pin = Pin(0, 0, measurements=[])

        self._measurement_plan.append_pin(pin)
        self._board_window.add_point(pin.x, pin.y, self._measurement_plan.get_current_index())
        self.line_comment_pin.setText(pin.comment or "")

        # It is important to initialize pin with real measurement.
        # Otherwise user can create several empty points and they will not be unique.
        # This will cause some errors during ufiv validation.
        # self._on_save_pin()
        self._update_current_pin()

    @pyqtSlot()
    def _on_save_pin(self):
        """
        Save current pin IVC as reference for current pin.
        """
        with self._device_errors_handler:
            self._measurement_plan.save_last_measurement_as_reference()
        self._set_comment()
        self._update_current_pin()

    def _reset_board(self):
        """
        Set measurement plan to default empty board.
        """
        # Create default board with 1 pin
        self._measurement_plan = MeasurementPlan(
            Board(elements=[Element(
                pins=[Pin(0, 0, measurements=[])]
            )]
            ),
            measurer=self._msystem.measurers[0]
        )

    @pyqtSlot()
    def _on_new_board(self):
        if self._current_file_path is not None:
            d = QDialog()
            d.setWindowTitle(qApp.translate("t", "Внимание"))
            d.setWindowModality(QtC.ApplicationModal)
            label = QLabel(qApp.translate("t", "Сохранить изменения в файл?"))
            btn_yes = QPushButton(qApp.translate("t", "Да"))
            btn_yes.clicked.connect(d.accept)
            btn_no = QPushButton(qApp.translate("t", "Нет"))
            btn_no.clicked.connect(lambda: d.done(10))
            btn_cancel = QPushButton(qApp.translate("t", "Отмена"))
            btn_cancel.clicked.connect(d.reject)
            hl = QHBoxLayout()
            hl.addWidget(btn_yes)
            hl.addWidget(btn_no)
            hl.addWidget(btn_cancel)
            layout = QVBoxLayout()
            layout.addWidget(label)
            layout.addLayout(hl)
            d.setLayout(layout)
            resp = d.exec()
            if resp == QDialog.Accepted:
                self._on_save_board()
            elif resp == 10:
                pass
            elif resp == QDialog.Rejected:
                return
        if not os.path.isdir(self.default_path):
            os.mkdir(self.default_path)
        if not os.path.isdir(os.path.join(self.default_path, "Reference")):
            os.mkdir(os.path.join(self.default_path, "Reference"))
        dialog = QFileDialog()
        filename = dialog.getSaveFileName(self, qApp.translate("t", "Создать новую плату"),
                                          filter="UFIV Archived File (*.uzf)",
                                          directory=os.path.join(self.default_path, "Reference", "board.uzf"))[0]
        if filename:
            self._current_file_path = filename
            self._reset_board()
            epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            self._board_window.set_board(self._measurement_plan)
            self._update_current_pin()

    def _check_measurement_plan(self) -> bool:
        """
        Method checks if there are pins without measurements.
        :return: True if there are pins without measurements.
        """

        empty_pins = ""
        for pin_index, pin in self._measurement_plan.all_pins_iterator():
            if not pin.measurements:
                if empty_pins:
                    empty_pins += ", "
                empty_pins += str(pin_index)
        if empty_pins:
            def func():
                raise ValueError("")
            if "," in empty_pins:
                text = qApp.translate("t", "Точки POINTS_PARAM не содержат сохраненных измерений. "
                                           "Для сохранения плана тестирования все точки должны "
                                           "содержать сохраненные измерения")
            else:
                text = qApp.translate("t", "Точка POINTS_PARAM не содержит сохраненных измерений. "
                                           "Для сохранения плана тестирования все точки должны "
                                           "содержать сохраненные измерения")
            text = text.replace("POINTS_PARAM", empty_pins)
            exec_msgbox = show_exception(func, qApp.translate("t", "Ошибка"), text)
            exec_msgbox()
            return True
        return False

    @pyqtSlot()
    def _on_save_board_as(self):
        """
        Method saves board in new file.
        """

        if self._check_measurement_plan():
            return
        if not os.path.isdir(self.default_path):
            os.mkdir(self.default_path)
        if not os.path.isdir(os.path.join(self.default_path, "Reference")):
            os.mkdir(os.path.join(self.default_path, "Reference"))
        dialog = QFileDialog()
        filename = dialog.getSaveFileName(self, qApp.translate("t", "Сохранить плату"),
                                          filter="UFIV Archived File (*.uzf)",
                                          directory=os.path.join(self.default_path, "Reference", "board.uzf"))[0]
        if filename:
            save_file = show_exception(epfilemanager.save_board_to_ufiv, qApp.translate("t", "Ошибка"),
                                       qApp.translate("t", "Неверный формат сохраняемого файла"))
            self._current_file_path = save_file(filename, self._measurement_plan)

    @pyqtSlot()
    def _on_save_board(self):
        """
        Method saves board in file.
        """

        if self._check_measurement_plan():
            return
        if not self._current_file_path:
            return self._on_save_board_as()
        save_file = show_exception(epfilemanager.save_board_to_ufiv, qApp.translate("t", "Ошибка"),
                                   qApp.translate("t", "Неверный формат сохраняемого файла"))
        self._current_file_path = save_file(self._current_file_path, self._measurement_plan)

    @pyqtSlot()
    def _on_load_board(self):
        """
        "Load board" button handler.
        """
        dialog = QFileDialog()
        filename = dialog.getOpenFileName(self, qApp.translate("t", "Открыть плату"),
                                          filter="Board Files (*.json *.uzf)")[0]
        if filename:
            self._current_file_path = filename
            load_file = show_exception(epfilemanager.load_board_from_ufiv, qApp.translate("t", "Ошибка"),
                                       qApp.translate("t", "Формат файла не подходит"))
            board = load_file(filename, auto_convert_p10=True)
            if board == ERROR_CODE:
                return

            self._measurement_plan = MeasurementPlan(board, measurer=self._msystem.measurers[0])
            self._board_window.set_board(self._measurement_plan)  # New workspace will be created here

            self._update_current_pin()
            self._open_board_window_if_needed()

    @pyqtSlot()
    def _on_load_board_image(self):
        """
        "Load board image" button handler.
        """
        dialog = QFileDialog()
        filename = dialog.getOpenFileName(self, qApp.translate("t", "Открыть изображение платы"),
                                          filter="Image Files (*.png *.jpg *.bmp)")[0]
        if filename:
            epfilemanager.add_image_to_ufiv(filename, self._measurement_plan)
            self._board_window.set_board(self._measurement_plan)
            self._update_current_pin()
            self._open_board_window_if_needed()

    @pyqtSlot()
    def _update_curves(self, curves: Dict[str, IVCurve], settings=None):
        # TODO: let the function work with larger lists
        # Store last curves
        if "test" in curves.keys():
            self._test_curve = curves["test"]

        if "ref" in curves.keys():
            self._ref_curve = curves["ref"]

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
            assert settings is not None
            score = self._calculate_score(self._ref_curve, self._test_curve, settings)
            self._score_wrapper.set_score(score)
            self._player.score_updated(score)
        else:
            self._score_wrapper.set_dummy_score()
        self.plot_parameters(settings)

    def plot_parameters(self, settings: MeasurementSettings):
        # TODO: refactor!
        param_dict = {"sensity": "-", "max_voltage": "-", "probe_signal_frequency": "-"}
        param_dict["voltage"], param_dict["current"] = self._iv_window.plot.get_minor_axis_step()
        param_dict["score"] = self._score_wrapper.get_score()

        buttons = self._option_buttons[EPLab.Parameter.sensitive]
        sensitive = buttons[self._product.settings_to_options(settings)[EPLab.Parameter.sensitive]].text()
        param_dict["sensity"] = sensitive
        param_dict["max_voltage"] = np.round(settings.max_voltage, 1)
        param_dict["probe_signal_frequency"] = np.round(settings.probe_signal_frequency, 1)
        self.low_panel_settings.set_all_parameters(**param_dict)

    def _remove_ref_curve(self):
        self._ref_curve = None

    def _adjust_plot_params(self, settings: MeasurementSettings):
        """
        Adjust plot parameters
        """
        borders = self._product.adjust_plot_borders(settings)
        scale = self._product.adjust_plot_scale(settings)
        self._iv_window.plot.set_scale(*scale)
        self._iv_window.plot.set_min_borders(*borders)

    def _reconnect_periodic_task(self):
        # Draw empty curves
        self._test_curve = None
        if self._work_mode is WorkMode.compare:
            self._ref_curve = None
        self._update_curves()
        self.reference_curve_plot.set_curve(None)
        self.test_curve_plot.set_curve(None)
        # Draw text
        self._iv_window.plot.set_center_text(qApp.translate("t", "НЕТ ПОДКЛЮЧЕНИЯ"))

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
            # Get curves from devices
            curves = dict()
            curves["test"] = self._msystem.measurers[0].get_last_cached_iv_curve()

            if self._work_mode is WorkMode.compare and len(self._msystem.measurers) > 1:
                # Display two current curves
                curves["ref"] = self._msystem.measurers[1].get_last_cached_iv_curve()
            else:
                # Reference curve will be read from measurement plan
                pass

            if self._skip_curve:
                self._skip_curve = False
            else:
                self._update_curves(curves, settings=self._msystem.measurers[0].get_settings())

                if self._settings_update_next_cycle:
                    # New curve with new settings - we must update plot parameters
                    self._adjust_plot_params(self._settings_update_next_cycle)
                    self._settings_update_next_cycle = None
                    # You need to redraw markers with new plot parameters
                    # (the scale of the plot has changed)
                    self._iv_window.plot.redraw_cursors()

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
                # settings = self._msystem.get_settings() # Cause an error of different settings. #TODO: find out why.
                settings = self._msystem.measurers[0].get_settings()
                options = self._ui_to_options()
                settings = self._product.options_to_settings(options, settings)
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
