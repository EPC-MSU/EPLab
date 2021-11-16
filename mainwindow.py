"""
File with class for main window of application.
"""

import copy
import os
import webbrowser
from datetime import datetime
from functools import partial
from platform import system
from typing import Dict, List, Optional, Tuple
import numpy as np
from PyQt5.QtCore import (pyqtSlot, QCoreApplication as qApp, QEvent, QPoint, QPointF, QSize,
                          Qt as QtC, QTimer, QTranslator)
from PyQt5.QtGui import QCloseEvent, QColor, QIcon, QResizeEvent
from PyQt5.QtWidgets import (QAction, QFileDialog, QHBoxLayout, QLayout, QLineEdit, QMainWindow,
                             QMenu, QMessageBox, QPushButton, QRadioButton, QScrollArea,
                             QVBoxLayout, QWidget)
from PyQt5.uic import loadUi
import epcore.filemanager as epfilemanager
from epcore.elements import Board, Element, IVCurve, MeasurementSettings, Pin
from epcore.ivmeasurer import (IVMeasurerASA, IVMeasurerBase, IVMeasurerIVM10, IVMeasurerVirtual,
                               IVMeasurerVirtualASA)
from epcore.measurementmanager import MeasurementPlan
from epcore.measurementmanager.ivc_comparator import IVCComparator
from epcore.measurementmanager.utils import Searcher
from epcore.product import EyePointProduct
from ivviewer import Viewer as IVViewer
import utils as ut
from boardwindow import BoardWidget
from common import DeviceErrorsHandler, WorkMode
from connection_window import ConnectionWindow
from language import Language, LanguageSelectionWindow
from measurer_settings_window import MeasurerSettingsWindow
from player import SoundPlayer
from report_window import ReportGenerationWindow
from score import ScoreWrapper
from settings.settings import Settings
from settings.settingswindow import LowSettingsPanel, SettingsWindow
from version import Version


def show_exception(msg_title: str, msg_text: str, exc: str = ""):
    """
    Function shows message box with error.
    :param msg_title: title of message box;
    :param msg_text: message text;
    :param exc: text of exception.
    """

    max_message_length = 500
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(msg_title)
    dir_name = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(dir_name, "media", "ico.png")
    msg.setWindowIcon(QIcon(icon_path))
    msg.setText(msg_text)
    if exc:
        msg.setInformativeText(str(exc)[-max_message_length:])
    msg.exec_()


class EPLabWindow(QMainWindow):
    """
    Class for main window of application.
    """

    default_path = "../EPLab-Files"

    def __init__(self, product: EyePointProduct, port_1: Optional[str] = None,
                 port_2: Optional[str] = None, english: Optional[bool] = None):
        """
        :param product: product;
        :param port_1: port for first measurer;
        :param port_2: port for second measurer;
        :param english: if True then interface language will be English.
        """

        super().__init__()
        self._init_ui(product, english)
        if port_1 is None and port_2 is None:
            self.disconnect_devices()
        else:
            self.connect_devices(port_1, port_2)

    def _adjust_plot_params(self, settings: MeasurementSettings):
        """
        Adjust plot parameters.
        :param settings: measurement settings.
        """

        borders = self._product.adjust_plot_borders(settings)
        scale = self._product.adjust_plot_scale(settings)
        self._iv_window.plot.set_scale(*scale)
        self._iv_window.plot.set_min_borders(*borders)

    def _calculate_score(self, curve_1: IVCurve, curve_2: IVCurve,
                         settings: MeasurementSettings) -> float:
        """
        Method calculates score for given IV-curves and measurement settings.
        :param curve_1: first curve;
        :param curve_2: second curve;
        :param settings: measurement settings.
        :return: score.
        """

        var_v, var_c = self._get_noise_amplitude(settings)
        # It is very important to set relevant noise levels
        self._comparator.set_min_ivc(var_v, var_c)
        score = self._comparator.compare_ivc(curve_1, curve_2)
        return score

    def _change_work_mode(self, mode: WorkMode):
        """
        Method sets window settings for given work mode.
        :param mode: work mode.
        """

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
        # Disable settings in test mode
        settings_enable = mode is not WorkMode.test
        for group in self._option_buttons.values():
            for button in group.values():
                button.setEnabled(settings_enable)
        self._work_mode = mode
        self._update_current_pin()

    def _check_measurement_plan(self, for_saving: bool = True) -> bool:
        """
        Method checks if there are pins without measurements.
        :param for_saving: if True then message box with warning will be shown
        for saving measurement plan.
        :return: True if there are pins without measurements.
        """

        empty_pins = ""
        for pin_index, pin in self._measurement_plan.all_pins_iterator():
            if not pin.measurements:
                if empty_pins:
                    empty_pins += ", "
                empty_pins += str(pin_index)
        if empty_pins:
            if for_saving:
                process_name = qApp.translate("t", "сохранения плана тестирования")
            else:
                process_name = qApp.translate("t", "создания отчета")
            if "," in empty_pins:
                text = qApp.translate("t", "Точки POINTS_PARAM не содержат сохраненных измерений. "
                                           "Для PROCESS_NAME все точки должны содержать сохраненные"
                                           " измерения")
            else:
                text = qApp.translate("t", "Точка POINTS_PARAM не содержит сохраненных измерений. "
                                           "Для PROCESS_NAME все точки должны содержать сохраненные"
                                           " измерения")
            text = text.replace("POINTS_PARAM", empty_pins)
            text = text.replace("PROCESS_NAME", process_name)
            show_exception(qApp.translate("t", "Ошибка"), text, "")
            return True
        return False

    @staticmethod
    def _clear_layout(layout: QLayout):
        """
        Method removes all widgets from layout.
        :param layout: layout.
        """

        for i_item in range(layout.count()):
            item = layout.itemAt(i_item)
            layout.removeItem(item)

    def _clear_widgets(self):
        """
        Method clears widgets on main window.
        """

        # Little bit hardcode here. See #39320
        # TODO: separate config file
        # Voltage in Volts, current in mA
        self._comparator.set_min_ivc(0.6, 0.002)
        self.__settings: Settings = None
        self._option_buttons = {EyePointProduct.Parameter.frequency: dict(),
                                EyePointProduct.Parameter.voltage: dict(),
                                EyePointProduct.Parameter.sensitive: dict()}
        for dock_widget in (self.freqLayout, self.currentLayout, self.voltageLayout):
            layout = dock_widget.layout()
            self._clear_layout(layout)
            layout.addWidget(QScrollArea())
        self.measurers_menu.clear()
        self._work_mode = None
        # Update plot settings at next measurement cycle (place settings here or None)
        self._settings_update_next_cycle = None
        # Set to True to skip next measured curves
        self._skip_curve = False
        self._hide_curve_test = False
        self._hide_curve_ref = False
        self._ref_curve = None
        self._test_curve = None
        self._current_file_path = None
        self._score_wrapper.set_dummy_score()

    def _create_measurer_setting_actions(self):
        """
        Method creates menu items to select settings for available measurers.
        """

        self.measurers_menu.clear()
        for measurer in self._msystem.measurers:
            device_name = measurer.name
            action = QAction(device_name, self)
            action.triggered.connect(partial(self._on_show_device_settings, measurer))
            self.measurers_menu.addAction(action)

    def _create_radio_buttons_for_parameter(self, param_name: EyePointProduct.Parameter,
                                            available_options: List) -> QWidget:
        """
        Method creates radio buttons for options of given parameter and puts
        them on widget.
        :param param_name: name of parameter;
        :param available_options: available options for parameter.
        :return: widget with radio buttons.
        """

        lang = qApp.instance().property("language")
        layout = QVBoxLayout()
        self._option_buttons[param_name] = {}
        for option in available_options:
            button = QRadioButton()
            layout.addWidget(button)
            button.setText(option.label_ru if lang is Language.RU else option.label_en)
            button.clicked.connect(self._on_select_option)
            self._option_buttons[param_name][option.name] = button
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _create_scroll_areas_for_parameters(self, settings: MeasurementSettings):
        """
        Method creates scroll areas for different parameters of measuring
        system. Scroll areas has radio buttons to choose options of parameters.
        :param settings: measurement settings.
        """

        available = self._product.get_available_options(settings)
        self._parameters_scroll_areas = {}
        layouts = self.freqLayout.layout(), self.voltageLayout.layout(), self.currentLayout.layout()
        parameters = (EyePointProduct.Parameter.frequency, EyePointProduct.Parameter.voltage,
                      EyePointProduct.Parameter.sensitive)
        for i_parameter, parameter in enumerate(parameters):
            widget_with_options = self._create_radio_buttons_for_parameter(parameter,
                                                                           available[parameter])
            scroll_area = QScrollArea()
            scroll_area.setVerticalScrollBarPolicy(QtC.ScrollBarAlwaysOn)
            scroll_area.setHorizontalScrollBarPolicy(QtC.ScrollBarAlwaysOff)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(widget_with_options)
            self._parameters_scroll_areas[parameter] = scroll_area
            self._clear_layout(layouts[i_parameter])
            layouts[i_parameter].addWidget(scroll_area)

    def _disable_optimal_parameter_searcher(self):
        """
        Method disables searcher of optimal parameters. Now searcher can work
        only for IVMeasurerIVM10.
        """

        for measurer in self._msystem.measurers:
            if not isinstance(measurer, (IVMeasurerIVM10, IVMeasurerVirtual)):
                self.search_optimal_action.setEnabled(False)
                return

    def _enable_widgets(self, enabled: bool):
        """
        Method sets widgets to given state (enabled or disabled).
        :param enabled: if True widgets will be set to enabled state.
        """

        widgets = (self.new_file_action, self.open_file_action, self.save_file_action,
                   self.save_as_file_action, self.save_screen_action, self.open_window_board_action,
                   self.freeze_curve_a_action, self.freeze_curve_b_action, self.hide_curve_a_action,
                   self.hide_curve_b_action, self.search_optimal_action, self.comparing_mode_action,
                   self.writing_mode_action, self.testing_mode_action, self.settings_mode_action,
                   self.next_point_action, self.last_point_action, self.new_point_action,
                   self.save_point_action, self.add_board_image_action, self.create_report_action,
                   self.add_cursor_action, self.remove_cursor_action, self.freqDock,
                   self.currentDock, self.voltageDock)
        for widget in widgets:
            widget.setEnabled(enabled)

    def _get_noise_amplitude(self, settings: MeasurementSettings) -> Tuple[float, float]:
        """
        Return noise amplitudes for given measurement settings.
        :param settings: measurement settings.
        :return: noise amplitudes for voltage and current.
        """

        return self._product.adjust_noise_amplitude(settings)

    def _get_options_from_ui(self) -> Dict[EyePointProduct.Parameter, str]:
        """
        Method returns current options for parameters of measuring system
        from UI.
        :return: dictionary with selected options for parameters.
        """

        def _get_checked_button(buttons: Dict) -> str:
            for name, button in buttons.items():
                if button.isChecked():
                    return name
        return {param: _get_checked_button(self._option_buttons[param])
                for param in self._option_buttons}

    def _init_threshold(self):
        """
        Method initializes initial value (50%) of score threshold.
        """

        threshold = self._score_wrapper.threshold
        self._update_threshold(threshold)

    def _init_ui(self, product: EyePointProduct, english: Optional[bool] = None):
        """
        Method initializes widgets on main window and objects.
        :param product: product;
        :param english: if True then interface language will be English.
        """

        self._translator = QTranslator()
        self._language_to_set: str = None
        if english:
            language = Language.EN
        else:
            language = ut.read_language_auto()
        if language is not Language.RU:
            translation_file = Language.get_translator_file(language)
            self._translator.load(translation_file)
            qApp.instance().installTranslator(self._translator)
            qApp.instance().setProperty("language", language)
        else:
            qApp.instance().setProperty("language", Language.RU)

        dir_name = os.path.dirname(os.path.abspath(__file__))
        loadUi(os.path.join(dir_name, "gui", "mainwindow.ui"), self)
        self._icon_path = os.path.join(dir_name, "media", "ico.png")
        self.setWindowIcon(QIcon(self._icon_path))
        self.setWindowTitle(self.windowTitle() + " " + Version.full)
        if system() == "Windows":
            self.setMinimumWidth(650)
        else:
            self.setMinimumWidth(700)
        self.move(50, 50)

        self._device_errors_handler = DeviceErrorsHandler()
        self._product = product
        self._msystem = None
        self._measurement_plan = None
        self._comparator = IVCComparator()

        self._score_wrapper = ScoreWrapper(self.score_label)
        self.__settings: Settings = None
        self._player = SoundPlayer()
        self._player.set_mute(not self.sound_enabled_action.isChecked())

        self._board_window = BoardWidget()
        self._board_window.resize(600, 600)
        self._board_window.setWindowIcon(QIcon("media/ico.png"))
        self._board_window.setWindowTitle("EPLab - Board")
        self._board_window.workspace.point_selected.connect(self._on_board_pin_selected)
        self._board_window.workspace.on_right_click.connect(self._on_board_right_click)
        self._board_window.workspace.point_moved.connect(self._on_board_pin_moved)

        self.low_panel_settings = LowSettingsPanel(self)
        self.main_widget = QWidget(self)
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        vbox = QVBoxLayout()
        self._iv_window = IVViewer(grid_color=QColor(255, 255, 255), back_color=QColor(0, 0, 0),
                                   solid_axis_enabled=False, axis_sign_enabled=False)
        self.reference_curve_plot = self._iv_window.plot.add_curve()
        self.test_curve_plot = self._iv_window.plot.add_curve()
        self.reference_curve_plot.set_curve_params(QColor(0, 128, 255, 200))
        self.test_curve_plot.set_curve_params(QColor(255, 0, 0, 200))
        self._iv_window.layout().setContentsMargins(0, 0, 0, 0)

        vbox.setSpacing(0)
        vbox.addWidget(self._iv_window)
        vbox.addLayout(self.grid_param)
        hbox = QHBoxLayout(self.main_widget)
        hbox.addLayout(vbox)

        self.connection_action.triggered.connect(self._on_connect_or_disconnect)
        self.open_window_board_action.triggered.connect(self._on_open_board_image)
        self.search_optimal_action.triggered.connect(self._on_search_optimal)
        self.new_file_action.triggered.connect(self._on_create_new_board)
        self.open_file_action.triggered.connect(self._on_load_board)
        self.save_file_action.triggered.connect(self._on_save_board)
        self.save_as_file_action.triggered.connect(self._on_save_board_as)
        self.last_point_action.triggered.connect(self._on_go_to_left_or_right_pin)
        self.num_point_line_edit = QLineEdit(self)
        self.num_point_line_edit.setFixedWidth(40)
        self.num_point_line_edit.setEnabled(False)
        self.toolBar_test.insertWidget(self.next_point_action, self.num_point_line_edit)
        self.num_point_line_edit.returnPressed.connect(self._on_go_selected_pin)
        self.next_point_action.triggered.connect(self._on_go_to_left_or_right_pin)
        self.new_point_action.triggered.connect(self._on_create_new_pin)
        self.save_point_action.triggered.connect(self._on_save_pin)
        self.add_board_image_action.triggered.connect(self._on_load_board_image)
        self.create_report_action.triggered.connect(self._on_create_report)
        self.about_action.triggered.connect(self._on_show_product_info)
        self.save_comment_push_button.clicked.connect(self._on_save_comment)
        self.line_comment_pin.returnPressed.connect(self._on_save_comment)
        self.sound_enabled_action.toggled.connect(self._on_enable_sound)
        self.freeze_curve_a_action.toggled.connect(partial(self._on_freeze_curve, 0))
        self.freeze_curve_b_action.toggled.connect(partial(self._on_freeze_curve, 1))
        self.hide_curve_a_action.toggled.connect(self._on_hide_curve)
        self.hide_curve_b_action.toggled.connect(self._on_hide_curve)
        self.add_cursor_action.toggled.connect(self._on_add_cursor)
        self.remove_cursor_action.setCheckable(False)
        self.remove_cursor_action.triggered.connect(self._on_show_context_menu_for_cursor_deletion)
        self.save_screen_action.triggered.connect(self._on_save_image)
        self.select_language_action.triggered.connect(self._on_select_language)

        self.comparing_mode_action.triggered.connect(
            lambda: self._on_switch_work_mode(WorkMode.compare))
        self.writing_mode_action.triggered.connect(
            lambda: self._on_switch_work_mode(WorkMode.write))
        self.testing_mode_action.triggered.connect(lambda: self._on_switch_work_mode(WorkMode.test))
        self.settings_mode_action.triggered.connect(self._on_show_settings_window)

        self._work_mode = None
        # Update plot settings at next measurement cycle (place settings here or None)
        self._settings_update_next_cycle = None
        # Set to True to skip next measured curves
        self._skip_curve = False
        self._hide_curve_test = False
        self._hide_curve_ref = False
        self._ref_curve = None
        self._test_curve = None
        self._current_file_path: str = None
        self._report_directory: str = None

        self._timer = QTimer()
        self._timer.setInterval(10)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_periodic_task)

    def _open_board_window_if_needed(self):
        if self._measurement_plan.image:
            self._board_window.show()

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
                self._update_curves(curves, self._msystem.get_settings())
                if self._settings_update_next_cycle:
                    # New curve with new settings - we must update plot parameters
                    self._adjust_plot_params(self._settings_update_next_cycle)
                    self._settings_update_next_cycle = None
                    # You need to redraw markers with new plot parameters
                    # (the scale of the plot has changed)
                    self._iv_window.plot.redraw_cursors()
            self._msystem.trigger_measurements()

    def _read_options_from_json(self) -> Optional[Dict]:
        """
        Method returns dictionary with options for parameters of measurement
        system.
        :return: dictionary with options for parameters.
        """

        for measurer in self.get_measurers():
            if isinstance(measurer, (IVMeasurerASA, IVMeasurerVirtualASA)):
                dir_name = os.path.dirname(os.path.abspath(__file__))
                file_name = os.path.join(dir_name, "resources", "eplab_asa_options.json")
                return ut.read_json(file_name)
        return None

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
                options = self._get_options_from_ui()
                settings = self._product.options_to_settings(options,
                                                             MeasurementSettings(-1, -1, -1, -1))
                self._set_msystem_settings(settings)
                self._msystem.trigger_measurements()

    def _reset_board(self):
        """
        Set measurement plan to default empty board.
        """

        # Create default board with 1 pin
        self._measurement_plan = MeasurementPlan(
            Board(elements=[Element(pins=[Pin(0, 0, measurements=[])])]),
            measurer=self._msystem.measurers[0])
        self._last_saved_measurement_plan_data: Dict = self._measurement_plan.to_json()

    def _remove_ref_curve(self):
        self._ref_curve = None

    def _set_comment(self):
        comment = self.line_comment_pin.text()
        self._measurement_plan.get_current_pin().comment = comment

    def _set_msystem_settings(self, settings: MeasurementSettings):
        self._msystem.set_settings(settings)
        # Skip next measurement because it still have old settings
        self._skip_curve = True
        # When new curve will be received plot parameters will be adjusted
        self._settings_update_next_cycle = settings

    def _set_options_to_ui(self, options: Dict[EyePointProduct.Parameter, str]):
        """
        Method sets options of parameters to UI.
        """

        for parameter, value in options.items():
            self._option_buttons[parameter][value].setChecked(True)

    def _set_plot_parameters(self, settings: MeasurementSettings):
        buttons = self._option_buttons[EyePointProduct.Parameter.sensitive]
        sensitive = buttons[self._product.settings_to_options(settings)[
            EyePointProduct.Parameter.sensitive]].text()
        voltage, current = self._iv_window.plot.get_minor_axis_step()
        param_dict = {"voltage": voltage,
                      "current": current,
                      "score": self._score_wrapper.get_score(),
                      "sensity": sensitive,
                      "max_voltage": np.round(settings.max_voltage, 1),
                      "probe_signal_frequency": np.round(settings.probe_signal_frequency, 1)}
        self.low_panel_settings.set_all_parameters(**param_dict)

    def _set_widgets_to_init_state(self):
        """
        Method initializes widgets on main window.
        """

        # Little bit hardcode here. See #39320
        # TODO: separate config file
        # Voltage in Volts, current in mA
        self._comparator.set_min_ivc(0.6, 0.002)
        self.__settings: Settings = None
        self._reset_board()
        self._board_window.set_board(self._measurement_plan)
        # Create menu items to select settings for available measurers
        self._create_measurer_setting_actions()
        # If necessary, deactivate the menu item for auto-selection
        self._disable_optimal_parameter_searcher()
        if len(self._msystem.measurers) < 2:
            self.freeze_curve_b_action.setEnabled(False)
            self.hide_curve_b_action.setEnabled(False)
        with self._device_errors_handler:
            for measurer in self._msystem.measurers:
                measurer.open_device()
        # Update plot settings at next measurement cycle (place settings here or None)
        self._settings_update_next_cycle = None
        # Set to True to skip next measured curves
        self._skip_curve = False
        self._hide_curve_test = False
        self._hide_curve_ref = False
        self._ref_curve = None
        self._test_curve = None
        # Set ui settings state to current device
        with self._device_errors_handler:
            settings = ut.read_settings_auto(self._product)
            if settings is not None:
                self._msystem.set_settings(settings)
            settings = self._msystem.get_settings()
            self._adjust_plot_params(settings)
            self._option_buttons = {}
            self._create_scroll_areas_for_parameters(settings)
            options = self._product.settings_to_options(settings)
            self._set_options_to_ui(options)
        self._work_mode = None
        self._change_work_mode(WorkMode.compare)  # default mode - compare two curves
        self._on_switch_work_mode(self._work_mode)
        self._update_current_pin()
        self._init_threshold()
        with self._device_errors_handler:
            self._msystem.trigger_measurements()
        self._current_file_path = None

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
                    self._set_options_to_ui(options)
                    self._update_curves({"ref": measurement.ivc},
                                        self._msystem.measurers[0].get_settings())
            else:
                self._remove_ref_curve()
                self._update_curves({}, self._msystem.measurers[0].get_settings())

    def _update_curves(self, curves: Dict[str, IVCurve] = None,
                       settings: MeasurementSettings = None):
        # TODO: let the function work with larger lists
        # Store last curves
        if curves is not None:
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
        if self._ref_curve and self._test_curve and self._work_mode != WorkMode.write:
            assert settings is not None
            score = self._calculate_score(self._ref_curve, self._test_curve, settings)
            self._score_wrapper.set_score(score)
            self._player.score_updated(score)
        else:
            self._score_wrapper.set_dummy_score()
        if settings is not None:
            self._set_plot_parameters(settings)

    def _update_scroll_areas_for_parameters(self, settings: MeasurementSettings):
        """
        Method updates scroll areas for different parameters of measuring
        system.
        :param settings: measurement settings.
        """

        available = self._product.get_available_options(settings)
        for parameter, scroll_area in self._parameters_scroll_areas.items():
            widget_with_options = self._create_radio_buttons_for_parameter(parameter,
                                                                           available[parameter])
            old_widget = scroll_area.takeWidget()
            del old_widget
            scroll_area.setWidget(widget_with_options)

    def _update_threshold(self, threshold: float):
        """
        Method updates score threshold value in _score_wrapper and _player.
        :param threshold: score threshold value.
        """

        self._score_wrapper.set_threshold(threshold)
        self._player.set_threshold(threshold)

    def _update_translation_for_scroll_areas_for_parameters(self):
        """
        Method updates translation of options in scroll areas for different parameters
        of measuring system.
        """

        lang = qApp.instance().property("language")
        settings = self._msystem.get_settings()
        available = self._product.get_available_options(settings)
        for parameter, buttons in self._option_buttons.items():
            for option_name, button in buttons.items():
                options = available[parameter]
                for option in options:
                    if option.name == option_name:
                        button.setText(option.label_ru if lang is Language.RU else option.label_en)

    @pyqtSlot(bool)
    def _on_add_cursor(self, state: bool):
        if state:
            self.remove_cursor_action.setChecked(False)
        self._iv_window.plot.set_state_adding_cursor(state)

    @pyqtSlot(int, QPointF)
    def _on_board_pin_moved(self, number: int, point: QPointF):
        self._measurement_plan.go_pin(number)
        self._measurement_plan.get_current_pin().x = point.x()
        self._measurement_plan.get_current_pin().y = point.y()

    @pyqtSlot(int)
    def _on_board_pin_selected(self, number: int):
        self._measurement_plan.go_pin(number)
        self._update_current_pin()

    @pyqtSlot(QPointF)
    def _on_board_right_click(self, point: QPointF):
        if self._work_mode is WorkMode.write:
            # Create new pin
            pin = Pin(x=point.x(), y=point.y(), measurements=[])
            self._measurement_plan.append_pin(pin)
            self._board_window.add_point(pin.x, pin.y, self._measurement_plan.get_current_index())
            self._update_current_pin()

    @pyqtSlot()
    def _on_connect_or_disconnect(self):
        """
        Slot shows dialog window to select devices for connection.
        """

        connection_wnd = ConnectionWindow(self)
        connection_wnd.exec()

    @pyqtSlot()
    def _on_create_new_board(self):
        if self._current_file_path is not None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle(qApp.translate("t", "Внимание"))
            msg.setWindowIcon(QIcon(self._icon_path))
            msg.setText(qApp.translate("t", "Сохранить изменения в файл?"))
            msg.addButton(qApp.translate("t", "Да"), QMessageBox.YesRole)
            msg.addButton(qApp.translate("t", "Нет"), QMessageBox.NoRole)
            msg.addButton(qApp.translate("t", "Отмена"), QMessageBox.RejectRole)
            result = msg.exec_()
            if result == 0:
                self._on_save_board()
            elif result == 1:
                pass
            else:
                return
        if not os.path.isdir(self.default_path):
            os.mkdir(self.default_path)
        if not os.path.isdir(os.path.join(self.default_path, "Reference")):
            os.mkdir(os.path.join(self.default_path, "Reference"))
        filename = QFileDialog.getSaveFileName(
            self, qApp.translate("t", "Создать новую плату"), filter="UFIV Archived File (*.uzf)",
            directory=os.path.join(self.default_path, "Reference", "board.uzf"))[0]
        if filename:
            self._current_file_path = filename
            self._reset_board()
            epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            self._board_window.set_board(self._measurement_plan)
            self._update_current_pin()

    @pyqtSlot()
    def _on_create_new_pin(self):
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
    def _on_create_report(self):
        """
        Slot shows dialog window to create report for board.
        """

        threshold_score = self._score_wrapper.threshold
        if self._check_measurement_plan(False):
            return
        report_generation_window = ReportGenerationWindow(
            self, self._measurement_plan, self._report_directory, threshold_score)
        report_generation_window.show()

    @pyqtSlot()
    def _on_delete_all_cursors(self):
        """
        Slot deletes all cursors from plot.
        """

        self._iv_window.plot.remove_all_cursors()

    @pyqtSlot(bool)
    def _on_enable_sound(self, state: bool):
        self._player.set_mute(not state)

    @pyqtSlot(int, bool)
    def _on_freeze_curve(self, measurer_id: int, state: bool):
        """
        Slot freezes or unfreezes curve for measurer with given index.
        :param measurer_id: index of measurer;
        :param state: if True then curve will be frozen.
        """

        if measurer_id < len(self._msystem.measurers):
            if state:
                self._msystem.measurers[measurer_id].freeze()
            else:
                self._msystem.measurers[measurer_id].unfreeze()

    @pyqtSlot()
    def _on_go_selected_pin(self):
        try:
            num_point = int(self.num_point_line_edit.text())
        except ValueError as exc:
            show_exception(qApp.translate("t", "Ошибка открытия точки"),
                           qApp.translate("t", "Неверный формат номера точки. Номер точки может"
                                               " принимать только целочисленное значение!"),
                           str(exc))
            return
        try:
            self._measurement_plan.go_pin(num_point)
        except ValueError as exc:
            show_exception(qApp.translate("t", "Ошибка открытия точки"),
                           qApp.translate("t", "Точка с таким номером не найдена на "
                                               "данной плате."), str(exc))
            return
        self._update_current_pin()
        self._open_board_window_if_needed()

    @pyqtSlot()
    def _on_go_to_left_or_right_pin(self):
        if self.sender() is self.last_point_action:
            self._measurement_plan.go_prev_pin()
        else:
            self._measurement_plan.go_next_pin()
        self._update_current_pin()
        self._open_board_window_if_needed()

    @pyqtSlot(bool)
    def _on_hide_curve(self, state: bool):
        """
        Slot sets parameter to hide or show curve.
        :param state: if True then curve will be hidden.
        """

        if self.sender() is self.hide_curve_a_action:
            self._hide_curve_test = state
        elif self.sender() is self.hide_curve_b_action:
            self._hide_curve_ref = state

    @pyqtSlot()
    def _on_load_board(self):
        """
        Slot loads board from file.
        """

        filename = QFileDialog.getOpenFileName(self, qApp.translate("t", "Открыть плату"),
                                               filter="Board Files (*.json *.uzf)")[0]
        if filename:
            try:
                board = epfilemanager.load_board_from_ufiv(filename, auto_convert_p10=True)
            except Exception as exc:
                show_exception(qApp.translate("t", "Ошибка"),
                               qApp.translate("t", "Формат файла не подходит"), str(exc))
                return
            if not ut.check_compatibility(self._product, board):
                text = qApp.translate("t", "План тестирования TEST_PLAN нельзя загрузить, "
                                           "поскольку он не соответствует режиму работы EPLab")
                show_exception(qApp.translate("t", "Ошибка"),
                               text.replace("TEST_PLAN", f"'{filename}'"))
                return
            self._measurement_plan = MeasurementPlan(board, measurer=self._msystem.measurers[0])
            self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
            # New workspace will be created here
            self._board_window.set_board(self._measurement_plan)
            self._update_current_pin()
            self._open_board_window_if_needed()

    @pyqtSlot()
    def _on_load_board_image(self):
        """
        Slot loads image for board from file.
        """

        filename = QFileDialog.getOpenFileName(
            self, qApp.translate("t", "Открыть изображение платы"),
            filter="Image Files (*.png *.jpg *.bmp)")[0]
        if filename:
            epfilemanager.add_image_to_ufiv(filename, self._measurement_plan)
            self._board_window.set_board(self._measurement_plan)
            self._update_current_pin()
            self._open_board_window_if_needed()

    @pyqtSlot()
    def _on_open_board_image(self):
        self._open_board_window_if_needed()
        if not self._measurement_plan.image:
            msg = QMessageBox()
            msg.setWindowTitle(qApp.translate("t", "Открытие изображения платы"))
            msg.setWindowIcon(QIcon(self._icon_path))
            msg.setText(qApp.translate("t", "Для данной платы изображение не задано!"))
            msg.exec_()

    @pyqtSlot()
    def _on_periodic_task(self):
        if self._device_errors_handler.all_ok:
            with self._device_errors_handler:
                self._read_curves_periodic_task()
        else:
            self._reconnect_periodic_task()
        # Add this task to event loop
        self._timer.start()

    @pyqtSlot()
    def _on_save_board(self) -> Optional[bool]:
        """
        Slot saves measurement plan in file.
        :return: True if measurement plan was saved otherwise False.
        """

        if self._check_measurement_plan():
            return None
        if not self._current_file_path:
            return self._on_save_board_as()
        self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
        self._current_file_path = epfilemanager.save_board_to_ufiv(self._current_file_path,
                                                                   self._measurement_plan)
        return True

    @pyqtSlot()
    def _on_save_board_as(self) -> Optional[bool]:
        """
        Slot saves measurement plan in new file.
        :return: True if measurement plan was saved otherwise False.
        """

        if self._check_measurement_plan():
            return None
        if not os.path.isdir(self.default_path):
            os.mkdir(self.default_path)
        if not os.path.isdir(os.path.join(self.default_path, "Reference")):
            os.mkdir(os.path.join(self.default_path, "Reference"))
        filename = QFileDialog.getSaveFileName(
            self, qApp.translate("t", "Сохранить плату"), filter="UFIV Archived File (*.uzf)",
            directory=os.path.join(self.default_path, "Reference", "board.uzf"))[0]
        if filename:
            self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
            self._current_file_path = epfilemanager.save_board_to_ufiv(filename,
                                                                       self._measurement_plan)
            return True
        return False

    @pyqtSlot()
    def _on_save_comment(self):
        comment = self.line_comment_pin.text()
        self._measurement_plan.get_current_pin().comment = comment

    @pyqtSlot()
    def _on_save_pin(self):
        """
        Save current pin IV-curve as reference for current pin.
        """

        with self._device_errors_handler:
            self._measurement_plan.save_last_measurement_as_reference()
        self._set_comment()
        self._update_current_pin()

    @pyqtSlot()
    def _on_save_image(self):
        # Freeze image at first
        image = self.grab(self.rect())
        filename = "eplab_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        dir_path = os.path.join(self.default_path, "Screenshot")
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        filename = QFileDialog.getSaveFileName(
            self, qApp.translate("t", "Сохранить ВАХ"), filter="Image (*.png)",
            directory=os.path.join(dir_path, filename))[0]
        if filename:
            if not filename.endswith(".png"):
                filename += ".png"
            image.save(filename)

    @pyqtSlot()
    def _on_search_optimal(self):
        with self._device_errors_handler:
            searcher = Searcher(self._msystem.measurers[0], self._product.get_parameters())
            optimal_settings = searcher.search_optimal_settings()
            self._set_msystem_settings(optimal_settings)
            options = self._product.settings_to_options(optimal_settings)
            self._set_options_to_ui(options)

    @pyqtSlot()
    def _on_select_language(self):
        """
        Slot shows dialog window to select language.
        """

        language_selection_wnd = LanguageSelectionWindow(self)
        if language_selection_wnd.exec():
            language = language_selection_wnd.get_language()
            if language != qApp.instance().property("language"):
                if self._msystem is not None:
                    settings = self._msystem.get_settings()
                else:
                    settings = None
                self._language_to_set = Language.get_language(language)
                ut.save_settings_auto(self._product, settings, self._language_to_set)
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle(qApp.translate("t", "Внимание"))
                msg.setWindowIcon(QIcon(self._icon_path))
                text_ru = ("Настройки языка сохранены. Чтобы изменения вступили в силу, "
                           "перезапустите программу.")
                text_en = ("The language settings are saved. Restart the program for the changes to"
                           " take effect.")
                if qApp.instance().property("language") is Language.RU:
                    text = text_ru + "\n" + text_en
                else:
                    text = text_en + "\n" + text_ru
                msg.setText(text)
                msg.exec_()

    @pyqtSlot(bool)
    def _on_select_option(self, checked: bool):
        """
        Slot handles selection of new option for parameter of measuring system.
        :param checked: if True radio button corresponding to option was selected.
        """

        if checked:
            settings = self._msystem.get_settings()
            old_settings = copy.deepcopy(settings)
            options = self._get_options_from_ui()
            settings = self._product.options_to_settings(options, settings)
            self._update_scroll_areas_for_parameters(settings)
            options = self._product.settings_to_options(settings)
            self._set_options_to_ui(options)
            try:
                self._set_msystem_settings(settings)
                if self._language_to_set is not None:
                    language = self._language_to_set
                else:
                    language = Language.get_language(qApp.instance().property("language"))
                ut.save_settings_auto(self._product, settings, language)
            except ValueError as exc:
                show_exception(qApp.translate("t", "Ошибка"),
                               qApp.translate("t", "Ошибка при установке настроек устройства"),
                               str(exc))
                self._update_scroll_areas_for_parameters(old_settings)
                self._set_msystem_settings(old_settings)
                old_options = self._product.settings_to_options(old_settings)
                self._set_options_to_ui(old_options)

    @pyqtSlot()
    def _on_set_cursor_deletion_mode(self):
        """
        Slot sets cursor deletion mode when one cursor at a time can be deleted.
        """

        self.remove_cursor_action.setCheckable(True)
        self.remove_cursor_action.setChecked(True)
        self.add_cursor_action.setChecked(False)
        self._iv_window.plot.set_state_removing_cursor(True)

    @pyqtSlot()
    def _on_show_context_menu_for_cursor_deletion(self):
        """
        Slot shows context menu for choosing to delete markers one at a time or
        all at once.
        """

        if self.remove_cursor_action.isCheckable():
            self.remove_cursor_action.setCheckable(False)
            self.remove_cursor_action.setChecked(False)
            self._iv_window.plot.set_state_removing_cursor(False)
            return
        widget = self.toolBar_cursor.widgetForAction(self.remove_cursor_action)
        menu = QMenu(widget)
        dir_name = os.path.dirname(os.path.abspath(__file__))
        icon = QIcon(os.path.join(dir_name, "media", "delete_cursor.png"))
        action_remove_cursor = QAction(icon, qApp.translate("t", "Удалить маркер"), menu)
        action_remove_cursor.triggered.connect(self._on_set_cursor_deletion_mode)
        menu.addAction(action_remove_cursor)
        icon = QIcon(os.path.join(dir_name, "media", "delete_all.png"))
        action_remove_all_cursors = QAction(icon, qApp.translate("t", "Удалить все маркеры"), menu)
        action_remove_all_cursors.triggered.connect(self._on_delete_all_cursors)
        menu.addAction(action_remove_all_cursors)
        position = widget.geometry()
        menu.popup(widget.mapToGlobal(QPoint(position.x(), position.y())))

    @pyqtSlot(IVMeasurerBase, bool)
    def _on_show_device_settings(self, selected_measurer: IVMeasurerBase, _: bool):
        """
        Slot shows window to select device settings.
        :param selected_measurer: measurer for which device settings should be
        displayed;
        :param _: not used.
        """

        for measurer in self._msystem.measurers:
            if measurer == selected_measurer:
                all_settings = measurer.get_all_settings()
                dialog = MeasurerSettingsWindow(self, all_settings, measurer)
                if dialog.exec_():
                    dialog.set_parameters()
                return

    @pyqtSlot()
    def _on_show_product_info(self):
        """
        Slot shows message box with information about application.
        """

        def handle_button_click(button: QPushButton):
            """
            Function handles click on button.
            :param button: button that was clicked.
            """

            page_url = "https://eyepoint.physlab.ru/"
            if qApp.instance().property("language") is Language.RU:
                page_url += "ru/"
            else:
                page_url += "en/"
            if button.text() in ("Перейти", "Go"):
                webbrowser.open_new_tab(page_url)

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(qApp.translate("t", "Справка"))
        msg.setWindowIcon(QIcon(self._icon_path))
        msg.setText(self.windowTitle())
        msg.setInformativeText(qApp.translate(
            "t", "Программное обеспечение для работы с устройствами линейки EyePoint,"
                 " предназначенными для поиска неисправностей на печатных платах в "
                 "ручном режиме (при помощи ручных щупов). Для более подробной информации "
                 "об Eyepoint, перейдите по ссылке http://eyepoint.physlab.ru."))
        msg.addButton(qApp.translate("t", "Перейти"), QMessageBox.YesRole)
        msg.addButton(qApp.translate("t", "ОК"), QMessageBox.NoRole)
        msg.buttonClicked.connect(handle_button_click)
        msg.exec_()

    @pyqtSlot()
    def _on_show_settings_window(self):
        """
        Slot is called when you click on 'Settings' button, it shows settings window.
        """

        self.__settings = None
        settings_window = SettingsWindow(self, self._score_wrapper.threshold)
        settings_window.exec()

    @pyqtSlot(WorkMode)
    def _on_switch_work_mode(self, mode: WorkMode):
        self.comparing_mode_action.setChecked(mode is WorkMode.compare)
        self.writing_mode_action.setChecked(mode is WorkMode.write)
        self.testing_mode_action.setChecked(mode is WorkMode.test)
        self.next_point_action.setEnabled(mode is not WorkMode.compare)
        self.last_point_action.setEnabled(mode is not WorkMode.compare)
        self.num_point_line_edit.setEnabled(mode is not WorkMode.compare)
        self.new_point_action.setEnabled(mode is WorkMode.write)
        self.save_point_action.setEnabled(mode is WorkMode.write)
        self.add_board_image_action.setEnabled(mode is WorkMode.write)
        self.create_report_action.setEnabled(mode is WorkMode.write)
        self._change_work_mode(mode)

    def apply_settings(self, threshold: float):
        """
        Method applies settings from settings window.
        :param threshold: threshold value.
        """

        if (self.__settings is None or
                (self.__settings and self.__settings.score_threshold != threshold)):
            # Settings were not loaded from file
            self._update_threshold(threshold)
            return
        # Settings were loaded from file
        self._on_switch_work_mode(self.__settings.work_mode)
        settings = self.__settings.measurement_settings()
        options = self._product.settings_to_options(settings)
        self._set_options_to_ui(options)
        self._set_msystem_settings(settings)
        self.hide_curve_a_action.setChecked(self.__settings.hide_curve_a)
        self.hide_curve_b_action.setChecked(self.__settings.hide_curve_b)
        self.sound_enabled_action.setChecked(self.__settings.sound_enabled)
        self._update_threshold(self.__settings.score_threshold)

    def closeEvent(self, event: QCloseEvent):
        self._board_window.close()
        if (self._measurement_plan and
                self._measurement_plan.to_json() != self._last_saved_measurement_plan_data):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle(qApp.translate("t", "Внимание"))
            msg.setWindowIcon(QIcon(self._icon_path))
            msg.setText(qApp.translate("t", "План тестирования не был сохранен. Сохранить "
                                            "последние изменения?"))
            msg.addButton(qApp.translate("t", "Да"), QMessageBox.YesRole)
            msg.addButton(qApp.translate("t", "Нет"), QMessageBox.NoRole)
            result = msg.exec_()
            if result == 0:
                if self._on_save_board() is None:
                    event.ignore()

    def changeEvent(self, event: QEvent):
        if event.type() == QEvent.LanguageChange:
            if self._msystem is not None:
                self._update_translation_for_scroll_areas_for_parameters()
            geometry = self.geometry()
            size = QSize(geometry.width(), geometry.height())
            event = QResizeEvent(size, size)
            self.resizeEvent(event)

    def connect_devices(self, port_1: str, port_2: str):
        """
        Method connects measurers with given ports.
        :param port_1: port for first measurer;
        :param port_2: port for second measurer.
        """

        if self._timer.isActive():
            self._timer.stop()
        if self._msystem:
            for measurer in self._msystem.measurers:
                measurer.close_device()
        self._msystem = ut.create_measurers(port_1, port_2)
        if not self._msystem:
            self._iv_window.plot.set_center_text(qApp.translate("t", "НЕТ ПОДКЛЮЧЕНИЯ"))
            enable = False
        else:
            self._iv_window.plot.clear_center_text()
            enable = True
            options_data = self._read_options_from_json()
            self._product.change_options(options_data)
            self._timer.start()
        self._enable_widgets(enable)
        self._set_widgets_to_init_state()

    def disconnect_devices(self):
        """
        Method disconnects measurers.
        """

        self._timer.stop()
        if self._msystem:
            for measurer in self._msystem.measurers:
                measurer.close_device()
        self._msystem = None
        self._iv_window.plot.set_center_text(qApp.translate("t", "НЕТ ПОДКЛЮЧЕНИЯ"))
        self._enable_widgets(False)
        self._clear_widgets()

    def get_measurers(self) -> list:
        """
        Method returns list of measurers.
        :return: list of measurers.
        """

        measurers = self._msystem.measurers if self._msystem else []
        return measurers

    def get_settings(self, threshold: float) -> Settings:
        """
        Method returns current applied settings in object.
        :param threshold: threshold value.
        :return: current settings.
        """

        settings = Settings()
        settings.set_measurement_settings(self._msystem.get_settings())
        if self.testing_mode_action.isChecked():
            settings.work_mode = WorkMode.test
        elif self.writing_mode_action.isChecked():
            settings.work_mode = WorkMode.write
        else:
            settings.work_mode = WorkMode.compare
        settings.score_threshold = threshold
        settings.hide_curve_a = bool(self.hide_curve_a_action.isChecked())
        settings.hide_curve_b = bool(self.hide_curve_b_action.isChecked())
        settings.sound_enabled = bool(self.sound_enabled_action.isChecked())
        return settings

    def open_settings_from_file(self, file_path: str) -> float:
        """
        Method reads settings from file with given path and returns score
        threshold.
        :param file_path: path to file with settings.
        :return: score threshold.
        """

        self.__settings = Settings()
        self.__settings.import_(path=file_path)
        return self.__settings.score_threshold

    def resizeEvent(self, event: QResizeEvent):
        """
        Method handles the resizing of the main window.
        :param event: resizing event.
        """

        # Determine the critical width of the window for given language and OS
        lang = qApp.instance().property("language")
        if system() == "Windows":
            size = 1150 if lang is Language.EN else 1350
        else:
            size = 1380 if lang is Language.EN else 1650
        # Change style of toolbars
        tool_bars = self.toolBar_write, self.toolBar_cursor, self.toolBar_mode
        for tool_bar in tool_bars:
            if self.width() < size:
                style = QtC.ToolButtonIconOnly
            else:
                style = QtC.ToolButtonTextBesideIcon
            tool_bar.setToolButtonStyle(style)
        super().resizeEvent(event)

    def set_report_directory(self, directory: str):
        """
        Method sets new value for report directory.
        :param directory: new report directory.
        """

        self._report_directory = directory
