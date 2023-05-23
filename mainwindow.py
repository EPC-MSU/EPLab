"""
File with class for main window of application.
"""

import copy
import logging
import os
import re
from datetime import datetime
from functools import partial
from platform import system
from typing import Dict, List, Optional, Tuple
import numpy as np
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QCoreApplication as qApp, QEvent, QObject, QPoint, Qt as QtC, QTimer,
                          QTranslator)
from PyQt5.QtGui import QCloseEvent, QColor, QIcon, QKeyEvent, QMouseEvent, QResizeEvent
from PyQt5.QtWidgets import (QAction, QFileDialog, QHBoxLayout, QLayout, QLineEdit, QMainWindow, QMenu, QMessageBox,
                             QRadioButton, QScrollArea, QVBoxLayout, QWidget)
from PyQt5.uic import loadUi
import epcore.filemanager as epfilemanager
from epcore.analogmultiplexer import BadMultiplexerOutputError
from epcore.elements import Board, Element, IVCurve, MeasurementSettings, Pin
from epcore.ivmeasurer import IVMeasurerASA, IVMeasurerBase, IVMeasurerIVM10, IVMeasurerVirtual, IVMeasurerVirtualASA
from epcore.measurementmanager import IVCComparator, MeasurementPlan, MeasurementSystem, Searcher
from epcore.product import EyePointProduct
from ivviewer import Viewer as IVViewer
from ivviewer.ivcviewer import PlotCurve
import connection_window as cw
import utils as ut
from about_window import show_product_info
from boardwindow import BoardWidget
from common import DeviceErrorsHandler, WorkMode
from language import Language, LanguageSelectionWindow
from measurer_settings_window import MeasurerSettingsWindow
from multiplexer import MuxAndPlanWindow
from player import SoundPlayer
from report_window import ReportGenerationThread, ReportGenerationWindow
from score import ScoreWrapper
from settings.settings import Settings
from settings.settingswindow import LowSettingsPanel, SettingsWindow
from version import Version

logger = logging.getLogger("eplab")


class EPLabWindow(QMainWindow):
    """
    Class for main window of application.
    """

    COLOR_FOR_REFERENCE: QColor = QColor(0, 128, 255, 200)
    COLOR_FOR_TEST: QColor = QColor(255, 0, 0, 200)
    COLOR_FOR_TEST_FROM_PLAN: QColor = QColor(255, 129, 129, 200)
    CRITICAL_WIDTH_FOR_LINUX_EN: int = 1380
    CRITICAL_WIDTH_FOR_LINUX_RU: int = 1650
    CRITICAL_WIDTH_FOR_WINDOWS_EN: int = 1150
    CRITICAL_WIDTH_FOR_WINDOWS_RU: int = 1350
    DEFAULT_PATH: str = os.path.join(ut.get_dir_name(), "EPLab-Files")
    DEFAULT_POS_X: int = 50
    DEFAULT_POS_Y: int = 50
    MIN_WIDTH_IN_LINUX: int = 700
    MIN_WIDTH_IN_WINDOWS: int = 650
    measurers_disconnected: pyqtSignal = pyqtSignal()
    work_mode_changed: pyqtSignal = pyqtSignal(WorkMode)

    def __init__(self, product: EyePointProduct, port_1: Optional[str] = None, port_2: Optional[str] = None,
                 english: Optional[bool] = None):
        """
        :param product: product;
        :param port_1: port for first measurer;
        :param port_2: port for second measurer;
        :param english: if True then interface language will be English.
        """

        super().__init__()
        self._icon: QIcon = QIcon(os.path.join(ut.DIR_MEDIA, "ico.png"))
        self._init_ui(product, english)
        self.installEventFilter(self)
        if port_1 is None and port_2 is None:
            self.disconnect_devices()
        else:
            self.connect_devices(port_1, port_2)

    @property
    def device_errors_handler(self) -> DeviceErrorsHandler:
        return self._device_errors_handler

    @property
    def measurement_plan(self) -> MeasurementPlan:
        return self._measurement_plan

    @property
    def product(self) -> EyePointProduct:
        return self._product

    @property
    def threshold(self) -> float:
        return self._score_wrapper.threshold

    @property
    def work_mode(self) -> WorkMode:
        return self._work_mode

    def _adjust_plot_params(self, settings: MeasurementSettings):
        """
        Method adjusts plot parameters.
        :param settings: measurement settings for which plot parameters to adjust.
        """

        scale = self._calculate_scales(settings)
        self._iv_window.plot.set_scale(*scale)
        self._iv_window.plot.set_min_borders(*scale)

    @staticmethod
    def _calculate_scales(settings: MeasurementSettings) -> Tuple[float, float]:
        """
        :param settings: measurement settings.
        :return: scale on horizontal and vertical axes.
        """

        scale_coefficient = 1.2
        x_scale = scale_coefficient * settings.max_voltage
        y_scale = 1000 * x_scale / settings.internal_resistance
        return x_scale, y_scale

    def _calculate_score(self, curve_1: IVCurve, curve_2: IVCurve, settings: MeasurementSettings) -> float:
        """
        Method calculates score for given IV-curves and measurement settings.
        :param curve_1: first IV-curve;
        :param curve_2: second IV-curve;
        :param settings: measurement settings.
        :return: score.
        """

        var_v, var_c = self._get_noise_amplitude(settings)
        # It is very important to set relevant noise levels
        self._comparator.set_min_ivc(var_v, var_c)
        return self._comparator.compare_ivc(curve_1, curve_2)

    def _change_work_mode(self, mode: WorkMode):
        """
        Method sets window settings for given work mode.
        :param mode: work mode.
        """

        self._player.set_work_mode(mode)
        if self._work_mode is mode:
            return
        # Comment is only for test and write mode
        self.line_comment_pin.setEnabled(mode is not WorkMode.COMPARE)
        if mode is WorkMode.COMPARE and len(self._msystem.measurers) < 2:
            # Remove reference curve in case we have only one IVMeasurer in compare mode
            self._remove_ref_curve()
        # Drag allowed only in write mode
        self._board_window.workspace.allow_drag(mode is WorkMode.WRITE)
        # Disable settings in test mode
        settings_enable = mode is not WorkMode.TEST
        for group in self._option_buttons.values():
            for button in group.values():
                button.setEnabled(settings_enable)
        self._work_mode = mode
        self.update_current_pin()

    def _check_measurement_plan_for_empty_pins(self) -> bool:
        """
        Method checks if there are pins without measurements in measurement plan.
        :return: True if there are pins without measurements.
        """

        empty_pins = ""
        for pin_index, pin in self._measurement_plan.all_pins_iterator():
            if not pin.measurements:
                if empty_pins:
                    empty_pins += ", "
                empty_pins += str(pin_index)
        if empty_pins:
            if "," in empty_pins:
                text = qApp.translate("t", "Точки POINTS_PARAM не содержат сохраненных измерений. Для сохранения "
                                           "плана тестирования все точки должны содержать сохраненные измерения")
            else:
                text = qApp.translate("t", "Точка POINTS_PARAM не содержит сохраненных измерений. Для сохранения "
                                           "плана тестирования все точки должны содержать сохраненные измерения")
            text = text.replace("POINTS_PARAM", empty_pins)
            ut.show_exception(qApp.translate("t", "Ошибка"), text, "")
            return True
        return False

    @staticmethod
    def _clear_layout(layout: QLayout):
        """
        Method removes all widgets from layout.
        :param layout: layout to clear.
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
        self.__settings = None
        self._option_buttons = {EyePointProduct.Parameter.frequency: dict(),
                                EyePointProduct.Parameter.voltage: dict(),
                                EyePointProduct.Parameter.sensitive: dict()}
        for widget in (self.freq_layout, self.current_layout, self.voltage_layout):
            layout = widget.layout()
            self._clear_layout(layout)
            layout.addWidget(QScrollArea())
        self.measurers_menu.clear()
        self._work_mode = None
        self._settings_update_next_cycle = None
        self._skip_curve = False
        self._hide_curve_test = False
        self._hide_curve_ref = False
        self._ref_curve = None
        self._test_curve = None
        self._test_curve_from_plan = None
        self._current_file_path = None
        self._score_wrapper.set_dummy_score()
        self.line_comment_pin.clear()
        self._mux_and_plan_window.close()
        self._report_generation_window.close()

    def _create_measurer_setting_actions(self):
        """
        Method creates menu items to select settings for available measurers.
        """

        self.measurers_menu.clear()
        for measurer in self._msystem.measurers:
            if isinstance(measurer, (IVMeasurerVirtual, IVMeasurerVirtualASA)):
                device_name = qApp.translate("t", "Эмулятор")
                icon = QIcon(os.path.join(ut.DIR_MEDIA, f"emulator_{measurer.name}.png"))
            elif isinstance(measurer, IVMeasurerIVM10):
                result = re.search(r"(?P<port>(COM\d+|ttyACM\d+))", measurer.url)
                device_name = "EyePoint IVM" if not result else f"EyePoint IVM ({result.group('port')})"
                icon = QIcon(os.path.join(ut.DIR_MEDIA, f"ivm_{measurer.name}.png"))
            elif isinstance(measurer, IVMeasurerASA):
                result = re.search(r"xmlrpc://(?P<url>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?P<port>(:\d+)?)",
                                   measurer.url)
                if result:
                    url = result.group("url")
                    port = result.group("port")
                    device_name = f"ASA ({url}:{port})" if port else f"ASA ({url})"
                else:
                    device_name = "ASA"
                icon = QIcon(os.path.join(ut.DIR_MEDIA, f"asa_{measurer.name}.png"))
            else:
                device_name = qApp.translate("t", "Неизвестный измеритель")
                icon = QIcon(os.path.join(ut.DIR_MEDIA, f"unknown_measurer_{measurer.name}.png"))
            action = QAction(icon, device_name, self)
            action.triggered.connect(partial(self.show_device_settings, measurer, device_name))
            self.measurers_menu.addAction(action)

    def _create_radio_buttons_for_parameter(self, param_name: EyePointProduct.Parameter,
                                            available_options: List) -> QWidget:
        """
        Method creates radio buttons for options of given parameter and puts them on widget.
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
        Method creates scroll areas for different parameters of measuring system.
        Scroll areas has radio buttons to choose options of parameters.
        :param settings: measurement settings.
        """

        available = self._product.get_available_options(settings)
        self._parameters_scroll_areas = {}
        layouts = self.freq_layout.layout(), self.voltage_layout.layout(), self.current_layout.layout()
        parameters = (EyePointProduct.Parameter.frequency, EyePointProduct.Parameter.voltage,
                      EyePointProduct.Parameter.sensitive)
        for i_parameter, parameter in enumerate(parameters):
            widget_with_options = self._create_radio_buttons_for_parameter(parameter, available[parameter])
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

    def _get_noise_amplitude(self, settings: MeasurementSettings) -> Tuple[float, float]:
        """
        Method returns noise amplitudes for given measurement settings.
        :param settings: measurement settings.
        :return: noise amplitudes for voltage and current.
        """

        return self._product.adjust_noise_amplitude(settings)

    def _get_options_from_ui(self) -> Dict[EyePointProduct.Parameter, str]:
        """
        Method returns current options for parameters of measuring system from UI.
        :return: dictionary with selected options for parameters.
        """

        def _get_checked_button(buttons: Dict) -> str:
            for name, button in buttons.items():
                if button.isChecked():
                    return name
        return {param: _get_checked_button(self._option_buttons[param]) for param in self._option_buttons}

    def _handle_key_press_event(self, obj: QObject, event: QEvent) -> bool:
        """
        Method handles key press events on main window.
        :param obj: main window;
        :param event: key press event.
        :return: handling result.
        """

        key = QKeyEvent(event).key()
        if key in (QtC.Key_Left, QtC.Key_Right) and self.next_point_action.isEnabled() and \
                self.previous_point_action.isEnabled():
            self.go_to_left_or_right_pin(key == QtC.Key_Left)
            return True
        if key in (QtC.Key_Enter, QtC.Key_Return) and self.save_point_action.isEnabled():
            self.save_pin()
            return True
        return super().eventFilter(obj, event)

    def _init_threshold(self):
        """
        Method initializes initial value of score threshold.
        """

        threshold = self._score_wrapper.threshold
        self._update_threshold(threshold)

    def _init_ui(self, product: EyePointProduct, english: Optional[bool] = None):
        """
        Method initializes widgets on main window and objects.
        :param product: product;
        :param english: if True then interface language will be English.
        """

        self._translator: QTranslator = QTranslator()
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
        self.setWindowIcon(self._icon)
        self.setWindowTitle(self.windowTitle() + " " + Version.full)
        if system().lower() == "windows":
            self.setMinimumWidth(self.MIN_WIDTH_IN_WINDOWS)
        else:
            self.setMinimumWidth(self.MIN_WIDTH_IN_LINUX)
        self.move(self.DEFAULT_POS_X, self.DEFAULT_POS_Y)

        self._device_errors_handler: DeviceErrorsHandler = DeviceErrorsHandler()
        self._product: EyePointProduct = product
        self._msystem: MeasurementSystem = None
        self._measurement_plan: MeasurementPlan = None
        self._comparator: IVCComparator = IVCComparator()

        self._score_wrapper: ScoreWrapper = ScoreWrapper(self.score_label)
        self.__settings: Settings = None
        self._player: SoundPlayer = SoundPlayer()
        self._player.set_mute(not self.sound_enabled_action.isChecked())

        self._board_window: BoardWidget = BoardWidget(self)
        self.low_panel_settings: LowSettingsPanel = LowSettingsPanel(self)
        self.main_widget: QWidget = QWidget(self)
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self._iv_window: IVViewer = IVViewer(grid_color=QColor(255, 255, 255), back_color=QColor(0, 0, 0),
                                             solid_axis_enabled=False, axis_label_enabled=False)
        dir_path = os.path.join(self.DEFAULT_PATH, "Screenshot")
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        self._iv_window.plot.set_path_to_directory(dir_path)
        self.reference_curve_plot: PlotCurve = self._iv_window.plot.add_curve()
        self.reference_curve_plot.set_curve_params(self.COLOR_FOR_REFERENCE)
        self.test_curve_plot: PlotCurve = self._iv_window.plot.add_curve()
        self.test_curve_plot.set_curve_params(self.COLOR_FOR_TEST)
        self.test_curve_plot_from_plan: PlotCurve = self._iv_window.plot.add_curve()
        self.test_curve_plot_from_plan.set_curve_params(self.COLOR_FOR_TEST_FROM_PLAN)
        self._iv_window.layout().setContentsMargins(0, 0, 0, 0)

        v_box_layout = QVBoxLayout()
        v_box_layout.setSpacing(0)
        v_box_layout.addWidget(self._iv_window)
        v_box_layout.addLayout(self.grid_param)
        h_box_layout = QHBoxLayout(self.main_widget)
        h_box_layout.addLayout(v_box_layout)

        self.connection_action.triggered.connect(self._on_connect_or_disconnect)
        self.open_window_board_action.triggered.connect(self._on_open_board_image)
        self.open_mux_window_action.triggered.connect(self._on_open_mux_window)
        self.search_optimal_action.triggered.connect(self._on_search_optimal)
        self.new_file_action.triggered.connect(self._on_create_new_board)
        self.open_file_action.triggered.connect(self._on_load_board)
        self.save_file_action.triggered.connect(self._on_save_board)
        self.save_as_file_action.triggered.connect(self._on_save_board_as)
        self.previous_point_action.triggered.connect(lambda: self.go_to_left_or_right_pin(True))
        self.num_point_line_edit = QLineEdit(self)
        self.num_point_line_edit.setFixedWidth(40)
        self.num_point_line_edit.setEnabled(False)
        self.num_point_line_edit.installEventFilter(self)
        self.toolBar_test.insertWidget(self.next_point_action, self.num_point_line_edit)
        self.num_point_line_edit.returnPressed.connect(self.go_to_selected_pin)
        self.next_point_action.triggered.connect(lambda: self.go_to_left_or_right_pin(False))
        self.new_point_action.triggered.connect(self.create_new_pin)
        self.save_point_action.triggered.connect(self.save_pin)
        self.add_board_image_action.triggered.connect(self._on_load_board_image)
        self.create_report_action.triggered.connect(self.create_report)
        self.about_action.triggered.connect(show_product_info)
        self.save_comment_push_button.clicked.connect(self._on_save_comment)
        self.line_comment_pin.installEventFilter(self)
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

        self.comparing_mode_action.triggered.connect(lambda: self._on_switch_work_mode(WorkMode.COMPARE))
        self.writing_mode_action.triggered.connect(lambda: self._on_switch_work_mode(WorkMode.WRITE))
        self.testing_mode_action.triggered.connect(lambda: self._on_switch_work_mode(WorkMode.TEST))
        self.settings_mode_action.triggered.connect(self._on_show_settings_window)

        self._work_mode: WorkMode = None
        # Update plot settings at next measurement cycle (place settings here or None)
        self._settings_update_next_cycle: MeasurementSettings = None
        # Set to True to skip next measured curves
        self._skip_curve: bool = False
        self._hide_curve_ref: bool = False
        self._hide_curve_test: bool = False
        self._ref_curve: IVCurve = None
        self._test_curve: IVCurve = None
        self._test_curve_from_plan: IVCurve = None
        self._current_file_path: str = None
        self._product_name: cw.ProductNames = None
        self._mux_and_plan_window: MuxAndPlanWindow = MuxAndPlanWindow(self)
        self.work_mode_changed.connect(self._mux_and_plan_window.change_work_mode)
        self.start_or_stop_entire_plan_measurement_action.triggered.connect(
            self._mux_and_plan_window.start_or_stop_plan_measurement)

        self._timer: QTimer = QTimer()
        self._timer.setInterval(10)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_periodic_task)
        self._report_generation_thread: ReportGenerationThread = ReportGenerationThread(parent=self)
        self._report_generation_thread.setTerminationEnabled(True)
        self._report_generation_thread.start()
        self._report_generation_window: ReportGenerationWindow = ReportGenerationWindow(self,
                                                                                        self._report_generation_thread)
        self._settings_path: str = ut.get_dir_name()

    def _open_board_window_if_needed(self):
        if self._measurement_plan.image:
            self._board_window.show()

    def _read_curves_periodic_task(self):
        if self._msystem.measurements_are_ready():
            if self._skip_curve:
                self._skip_curve = False
            else:
                # Get curves from devices
                curves = dict()
                curves["test"] = self._msystem.measurers[0].get_last_cached_iv_curve()
                if self._work_mode is WorkMode.COMPARE and len(self._msystem.measurers) > 1:
                    # Display two current curves
                    curves["ref"] = self._msystem.measurers[1].get_last_cached_iv_curve()
                self._update_curves(curves, self._msystem.get_settings())
                if self._mux_and_plan_window.measurement_plan_runner.is_running:
                    self._mux_and_plan_window.measurement_plan_runner.check_pin()
                if self._settings_update_next_cycle:
                    # New curve with new settings - we must update plot parameters
                    self._adjust_plot_params(self._settings_update_next_cycle)
                    self._settings_update_next_cycle = None
                    # You need to redraw markers with new plot parameters (the scale of the plot has changed)
                    self._iv_window.plot.redraw_cursors()
            self._msystem.trigger_measurements()

    def _read_options_from_json(self) -> Optional[Dict]:
        """
        Method returns dictionary with options for parameters of measurement system.
        :return: dictionary with options for parameters.
        """

        for measurer in self.get_measurers():
            if isinstance(measurer, (IVMeasurerASA, IVMeasurerVirtualASA)):
                dir_name = os.path.dirname(os.path.abspath(__file__))
                file_name = os.path.join(dir_name, "resources", "eplab_asa_options.json")
                return ut.read_json(file_name)
        return None

    def _reconnect_periodic_task(self):
        """
        Method try to reconnect measurer devices to app.
        """

        self.measurers_disconnected.emit()
        self._mux_and_plan_window.set_disconnection_mode()
        # Draw empty curves
        self.enable_widgets(False)
        self._test_curve = None
        if self._work_mode is WorkMode.COMPARE:
            self._ref_curve = None
        self._update_curves()
        self.reference_curve_plot.set_curve(None)
        self.test_curve_plot.set_curve(None)
        self.test_curve_plot_from_plan.set_curve(None)
        # Draw text
        self._iv_window.plot.set_center_text(qApp.translate("t", "НЕТ ПОДКЛЮЧЕНИЯ"))
        if self._msystem.reconnect():
            self.enable_widgets(True)
            self._mux_and_plan_window.set_connection_mode()
            # Reconnection success!
            self._device_errors_handler.reset_error()
            self._iv_window.plot.clear_center_text()
            with self._device_errors_handler:
                # Update current settings to reconnected device
                options = self._get_options_from_ui()
                settings = self._product.options_to_settings(options, MeasurementSettings(-1, -1, -1, -1))
                self._set_msystem_settings(settings)
                self._msystem.trigger_measurements()

    def _reset_board(self):
        """
        Method sets measurement plan to default empty board with 1 pin.
        """

        self._measurement_plan = MeasurementPlan(
            Board(elements=[Element(pins=[Pin(0, 0, measurements=[])])]), measurer=self._msystem.measurers[0],
            multiplexer=(None if not self._msystem.multiplexers else self._msystem.multiplexers[0]))
        self._last_saved_measurement_plan_data: Dict = self._measurement_plan.to_json()

    def _remove_ref_curve(self):
        self._ref_curve = None

    def _set_msystem_settings(self, settings: MeasurementSettings):
        """
        Method sets new measurement settings.
        :param settings: measurement settings to set.
        """

        self._msystem.set_settings(settings)
        # Skip next measurement because it still have old settings
        self._skip_curve = True
        # When new curve will be received plot parameters will be adjusted
        self._settings_update_next_cycle = settings

    def _set_options_to_ui(self, options: Dict[EyePointProduct.Parameter, str]):
        """
        Method sets options of parameters to UI.
        :param options: options that should be checked.
        """

        for parameter, value in options.items():
            self._option_buttons[parameter][value].setChecked(True)

    def _set_plot_parameters_to_low_panel_settings(self, settings: MeasurementSettings):
        """
        Method sets plot parameters to low panel on main window.
        :param settings: measurement settings.
        """

        buttons = self._option_buttons[EyePointProduct.Parameter.sensitive]
        sensitive = buttons[self._product.settings_to_options(settings)[EyePointProduct.Parameter.sensitive]].text()
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
        Method initializes widgets on main window and sets them to initial state.
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
        with self._device_errors_handler:
            for measurer in self._msystem.measurers:
                measurer.open_device()
            for multiplexer in self._msystem.multiplexers:
                multiplexer.open_device()
        self._settings_update_next_cycle = None
        self._skip_curve = False
        self._hide_curve_test = False
        self._hide_curve_ref = False
        self._ref_curve = None
        self._test_curve = None
        self._test_curve_from_plan = None
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
        self._mux_and_plan_window.update_info()
        self._work_mode = None
        self._change_work_mode(WorkMode.COMPARE)  # default mode - compare two curves
        self._on_switch_work_mode(self._work_mode)
        self.update_current_pin()
        self._init_threshold()
        with self._device_errors_handler:
            self._msystem.trigger_measurements()
        self._current_file_path = None

    def _update_curves(self, curves: Dict[str, Optional[IVCurve]] = None, settings: MeasurementSettings = None):
        """
        Method updates curves and calculates (if required) score.
        :param curves: dictionary with new curves;
        :param settings: measurement settings.
        """

        # TODO: let the function work with larger lists
        # Store last curves
        if curves is not None:
            if "ref" in curves.keys():
                self._ref_curve = curves["ref"]
            if "test" in curves.keys():
                self._test_curve = curves["test"]
            if "test_for_plan" in curves.keys():
                self._test_curve_from_plan = curves["test_for_plan"]
        # Update plots
        if not self._hide_curve_ref:
            self.reference_curve_plot.set_curve(self._ref_curve)
        else:
            self.reference_curve_plot.set_curve(None)
        if not self._hide_curve_test:
            self.test_curve_plot.set_curve(self._test_curve)
        else:
            self.test_curve_plot.set_curve(None)
        if self._work_mode != WorkMode.COMPARE:
            self.test_curve_plot_from_plan.set_curve(self._test_curve_from_plan)
        else:
            self.test_curve_plot_from_plan.set_curve(None)
        # Update score
        if self._ref_curve and self._test_curve and self._work_mode != WorkMode.WRITE:
            assert settings is not None
            score = self._calculate_score(self._ref_curve, self._test_curve, settings)
            self._score_wrapper.set_score(score)
            self._player.score_updated(score)
        else:
            self._score_wrapper.set_dummy_score()
        if settings is not None:
            self._set_plot_parameters_to_low_panel_settings(settings)

    def _update_scroll_areas_for_parameters(self, settings: MeasurementSettings):
        """
        Method updates scroll areas for different parameters of measuring system.
        :param settings: measurement settings.
        """

        available = self._product.get_available_options(settings)
        for parameter, scroll_area in self._parameters_scroll_areas.items():
            widget_with_options = self._create_radio_buttons_for_parameter(parameter, available[parameter])
            old_widget = scroll_area.takeWidget()
            del old_widget
            scroll_area.setWidget(widget_with_options)

    def _update_threshold(self, threshold: float):
        """
        Method updates score threshold value in _score_wrapper and _player.
        :param threshold: new score threshold value.
        """

        self._score_wrapper.set_threshold(threshold)
        self._player.set_threshold(threshold)

    @pyqtSlot(bool)
    def _on_add_cursor(self, state: bool):
        if state:
            self.remove_cursor_action.setChecked(False)
        self._iv_window.plot.set_state_adding_cursor(state)

    @pyqtSlot()
    def _on_connect_or_disconnect(self):
        """
        Slot shows dialog window to select devices for connection.
        """

        connection_wnd = cw.ConnectionWindow(self, self._product_name)
        connection_wnd.exec()

    @pyqtSlot()
    def _on_create_new_board(self):
        """
        Slot saves board information to file. Depending on conditions
        board is saved to a new or existing file.
        """

        if self._current_file_path is not None:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle(qApp.translate("t", "Внимание"))
            msg_box.setWindowIcon(self._icon)
            msg_box.setText(qApp.translate("t", "Сохранить изменения в файл?"))
            msg_box.addButton(qApp.translate("t", "Да"), QMessageBox.YesRole)
            msg_box.addButton(qApp.translate("t", "Нет"), QMessageBox.NoRole)
            msg_box.addButton(qApp.translate("t", "Отмена"), QMessageBox.RejectRole)
            result = msg_box.exec_()
            if result == 0:
                self._on_save_board()
            elif result == 1:
                pass
            else:
                return
        if not os.path.isdir(self.DEFAULT_PATH):
            os.mkdir(self.DEFAULT_PATH)
        if not os.path.isdir(os.path.join(self.DEFAULT_PATH, "Reference")):
            os.mkdir(os.path.join(self.DEFAULT_PATH, "Reference"))
        filename = QFileDialog.getSaveFileName(
            self, qApp.translate("t", "Создать новую плату"), filter="UFIV Archived File (*.uzf)",
            directory=os.path.join(self.DEFAULT_PATH, "Reference", "board.uzf"))[0]
        if filename:
            self._current_file_path = filename
            self._reset_board()
            epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            self._board_window.set_board(self._measurement_plan)
            self.update_current_pin()
            self._mux_and_plan_window.update_info()

    @pyqtSlot()
    def _on_delete_all_cursors(self):
        """
        Slot deletes all cursors from plot.
        """

        self._iv_window.plot.remove_all_cursors()

    @pyqtSlot(bool)
    def _on_enable_sound(self, state: bool):
        """
        Slot enables or disables sound.
        :param state: if True then sound will be enabled.
        """

        self._player.set_mute(not state)

    @pyqtSlot(int, bool)
    def _on_freeze_curve(self, measurer_id: int, state: bool):
        """
        Slot freezes or unfreezes curve for measurer with given index.
        :param measurer_id: index of measurer;
        :param state: if True then curve will be frozen.
        """

        if 0 <= measurer_id < len(self._msystem.measurers):
            if state:
                self._msystem.measurers[measurer_id].freeze()
            else:
                self._msystem.measurers[measurer_id].unfreeze()
                self._skip_curve = True

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
                ut.show_exception(qApp.translate("t", "Ошибка"), qApp.translate("t", "Формат файла не подходит"),
                                  str(exc))
                return
            if not ut.check_compatibility(self._product, board):
                text = qApp.translate("t", "План тестирования TEST_PLAN нельзя загрузить, поскольку он не "
                                           "соответствует режиму работы EPLab.")
                ut.show_exception(qApp.translate("t", "Ошибка"), text.replace("TEST_PLAN", f"'{filename}'"))
                return
            self._measurement_plan = MeasurementPlan(
                board, measurer=self._msystem.measurers[0],
                multiplexer=(None if not self._msystem.multiplexers else self._msystem.multiplexers[0]))
            self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
            # New workspace will be created here
            self._board_window.set_board(self._measurement_plan)
            self.update_current_pin()
            self._open_board_window_if_needed()
            self._mux_and_plan_window.update_info()

    @pyqtSlot()
    def _on_load_board_image(self):
        """
        Slot loads image for board from file.
        """

        filename = QFileDialog.getOpenFileName(self, qApp.translate("t", "Открыть изображение платы"),
                                               filter="Image Files (*.png *.jpg *.bmp)")[0]
        if filename:
            epfilemanager.add_image_to_ufiv(filename, self._measurement_plan)
            self._board_window.set_board(self._measurement_plan)
            self.update_current_pin()
            self._open_board_window_if_needed()

    @pyqtSlot()
    def _on_open_board_image(self):
        if not self._measurement_plan.image:
            ut.show_exception(qApp.translate("t", "Открытие изображения платы"),
                              qApp.translate("t", "Для данной платы изображение не задано!"))
        else:
            self._open_board_window_if_needed()

    @pyqtSlot()
    def _on_open_mux_window(self):
        """
        Slot shows window with measurement plan and multiplexer pinout.
        """

        if not self._mux_and_plan_window.isVisible():
            self._mux_and_plan_window.show()

    @pyqtSlot()
    def _on_periodic_task(self):
        if self._device_errors_handler.all_ok:
            with self._device_errors_handler:
                self._read_curves_periodic_task()
            self._mux_and_plan_window.measurement_plan_runner.save_pin()
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

        if self._check_measurement_plan_for_empty_pins():
            return None
        if not self._current_file_path:
            return self._on_save_board_as()
        self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
        self._current_file_path = epfilemanager.save_board_to_ufiv(self._current_file_path, self._measurement_plan)
        return True

    @pyqtSlot()
    def _on_save_board_as(self) -> Optional[bool]:
        """
        Slot saves measurement plan in new file.
        :return: True if measurement plan was saved otherwise False.
        """

        if self._check_measurement_plan_for_empty_pins():
            return None
        if not os.path.isdir(self.DEFAULT_PATH):
            os.mkdir(self.DEFAULT_PATH)
        if not os.path.isdir(os.path.join(self.DEFAULT_PATH, "Reference")):
            os.mkdir(os.path.join(self.DEFAULT_PATH, "Reference"))
        filename = QFileDialog.getSaveFileName(
            self, qApp.translate("t", "Сохранить плату"), filter="UFIV Archived File (*.uzf)",
            directory=os.path.join(self.DEFAULT_PATH, "Reference", "board.uzf"))[0]
        if filename:
            self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
            self._current_file_path = epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            return True
        return False

    @pyqtSlot()
    def _on_save_comment(self):
        pin_index = self._measurement_plan.get_current_index()
        self._measurement_plan.save_comment_to_pin_with_index(pin_index, self.line_comment_pin.text())

    @pyqtSlot()
    def _on_save_image(self):
        """
        Slot saves screenshot of main window.
        """

        image = self.grab(self.rect())
        filename = "eplab_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        dir_path = os.path.join(self.DEFAULT_PATH, "Screenshot")
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if system().lower() == "windows":
            filename = QFileDialog.getSaveFileName(self, qApp.translate("t", "Сохранить ВАХ"), filter="Image (*.png)",
                                                   directory=os.path.join(dir_path, filename))[0]
        else:
            filename = QFileDialog.getSaveFileName(self, qApp.translate("t", "Сохранить ВАХ"), filter="Image (*.png)",
                                                   directory=os.path.join(dir_path, filename),
                                                   options=QFileDialog.DontUseNativeDialog)[0]
        if filename:
            if not filename.endswith(".png"):
                filename += ".png"
            image.save(filename)

    @pyqtSlot()
    def _on_search_optimal(self):
        """
        Slot runs algorithm to search optimal measurement settings.
        """

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
            language = language_selection_wnd.get_language_value()
            if language != qApp.instance().property("language"):
                try:
                    if self._msystem is not None:
                        settings = self._msystem.get_settings()
                    else:
                        settings = None
                except Exception:
                    settings = None
                self._language_to_set = Language.get_language_name(language)
                ut.save_settings_auto(self._product, settings, self._language_to_set)
                text_ru = "Настройки языка сохранены. Чтобы изменения вступили в силу, перезапустите программу."
                text_en = "The language settings are saved. Restart the program for the changes to take effect."
                if qApp.instance().property("language") is Language.RU:
                    text = text_ru + "\n" + text_en
                else:
                    text = text_en + "\n" + text_ru
                ut.show_exception(qApp.translate("t", "Внимание"), text)

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
                    language = Language.get_language_name(qApp.instance().property("language"))
                ut.save_settings_auto(self._product, settings, language)
            except ValueError as exc:
                ut.show_exception(qApp.translate("t", "Ошибка"),
                                  qApp.translate("t", "Ошибка при установке настроек устройства"), str(exc))
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
        Slot shows context menu for choosing to delete cursors one at a time or
        all at once.
        """

        if self.remove_cursor_action.isCheckable():
            self.remove_cursor_action.setCheckable(False)
            self.remove_cursor_action.setChecked(False)
            self._iv_window.plot.set_state_removing_cursor(False)
            return
        widget = self.toolBar_cursor.widgetForAction(self.remove_cursor_action)
        menu = QMenu(widget)
        icon = QIcon(os.path.join(ut.DIR_MEDIA, "delete_cursor.png"))
        action_remove_cursor = QAction(icon, qApp.translate("t", "Удалить метку"), menu)
        action_remove_cursor.triggered.connect(self._on_set_cursor_deletion_mode)
        menu.addAction(action_remove_cursor)
        icon = QIcon(os.path.join(ut.DIR_MEDIA, "delete_all.png"))
        action_remove_all_cursors = QAction(icon, qApp.translate("t", "Удалить все метки"), menu)
        action_remove_all_cursors.triggered.connect(self._on_delete_all_cursors)
        menu.addAction(action_remove_all_cursors)
        position = widget.geometry()
        menu.popup(widget.mapToGlobal(QPoint(position.x(), position.y())))

    @pyqtSlot()
    def _on_show_settings_window(self):
        """
        Slot is called when you click on 'Settings' button, it shows settings window.
        """

        self.__settings = None
        settings_window = SettingsWindow(self, self._score_wrapper.threshold, self._settings_path)
        settings_window.exec()
        self._settings_path = settings_window.settings_directory

    @pyqtSlot(WorkMode)
    def _on_switch_work_mode(self, mode: WorkMode):
        """
        Slot switches work mode.
        :param mode: work mode to set.
        """

        self.open_mux_window_action.setEnabled(self._measurement_plan.multiplexer is not None)
        self.comparing_mode_action.setChecked(mode is WorkMode.COMPARE)
        self.writing_mode_action.setChecked(mode is WorkMode.WRITE)
        self.testing_mode_action.setChecked(mode is WorkMode.TEST)
        self.next_point_action.setEnabled(mode is not WorkMode.COMPARE)
        self.previous_point_action.setEnabled(mode is not WorkMode.COMPARE)
        self.num_point_line_edit.setEnabled(mode is not WorkMode.COMPARE)
        self.new_point_action.setEnabled(mode is WorkMode.WRITE)
        self.save_point_action.setEnabled(mode is not WorkMode.COMPARE)
        self.add_board_image_action.setEnabled(mode is WorkMode.WRITE)
        self.create_report_action.setEnabled(mode is not WorkMode.COMPARE)
        self.start_or_stop_entire_plan_measurement_action.setEnabled(mode is not WorkMode.COMPARE and
                                                                     self._measurement_plan.multiplexer is not None)
        self._change_work_mode(mode)
        self.work_mode_changed.emit(mode)
        if mode in (WorkMode.TEST, WorkMode.WRITE) and self._measurement_plan.multiplexer:
            self._on_open_mux_window()

    def apply_settings(self, threshold: float):
        """
        Method applies settings from settings window.
        :param threshold: threshold value.
        """

        if self.__settings is None or (self.__settings and self.__settings.score_threshold != threshold):
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
        if self._measurement_plan and self._measurement_plan.to_json() != self._last_saved_measurement_plan_data:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle(qApp.translate("t", "Внимание"))
            msg_box.setWindowIcon(self._icon)
            msg_box.setText(qApp.translate("t", "План тестирования не был сохранен. Сохранить последние изменения?"))
            msg_box.addButton(qApp.translate("t", "Да"), QMessageBox.YesRole)
            msg_box.addButton(qApp.translate("t", "Нет"), QMessageBox.NoRole)
            if msg_box.exec_() == 0:
                if self._on_save_board() is None:
                    event.ignore()
        self._mux_and_plan_window.close()
        if self._report_generation_thread:
            self._report_generation_thread.stop_thread()
            self._report_generation_thread.wait()

    def connect_devices(self, port_1: Optional[str], port_2: Optional[str],
                        product_name: Optional[cw.ProductNames] = None, mux_port: str = None):
        """
        Method connects measurers with given ports.
        :param port_1: port for first measurer;
        :param port_2: port for second measurer;
        :param product_name: name of product to work with application;
        :param mux_port: port for multiplexer.
        """

        if self._timer.isActive():
            self._timer.stop()
        if self.start_or_stop_entire_plan_measurement_action.isChecked():
            self.start_or_stop_entire_plan_measurement_action.setChecked(False)
        if self._msystem:
            for measurer in self._msystem.measurers:
                measurer.close_device()
            for multiplexer in self._msystem.multiplexers:
                multiplexer.close_device()
        good_com_ports, bad_com_ports = cw.utils.check_com_ports([port_1, port_2, mux_port])
        if bad_com_ports:
            if len(bad_com_ports) == 1:
                text = qApp.translate("t", "Проверьте, что устройство {} подключено к компьютеру и не удерживается "
                                           "другой программой.")
            else:
                text = qApp.translate("t", "Проверьте, что устройства {} подключены к компьютеру и не удерживаются "
                                           "другой программой.")
            ut.show_exception(qApp.translate("t", "Ошибка подключения"), text.format(", ".join(bad_com_ports)))
        self._msystem, bad_com_ports = ut.create_measurement_system(*good_com_ports)
        if bad_com_ports:
            if len(bad_com_ports) == 1:
                text = qApp.translate("t", "Не удалось подключиться к {0}. Убедитесь, что {0} - это устройство "
                                           "EyePoint, а не какое-то другое устройство.")
            else:
                text = qApp.translate("t", "Не удалось подключиться к {0}. Убедитесь, что {0} - это устройства "
                                           "EyePoint, а не какие-то другие устройства.")
            ut.show_exception(qApp.translate("t", "Ошибка подключения"), text.format(", ".join(bad_com_ports)))
        if not self._msystem:
            self.disconnect_devices()
            return
        self._iv_window.plot.clear_center_text()
        options_data = self._read_options_from_json()
        self._product.change_options(options_data)
        if product_name is None:
            self._product_name = cw.ProductNames.get_default_product_name_for_measurers(self._msystem.measurers)
        else:
            self._product_name = product_name
        self._timer.start()
        self.enable_widgets(True)
        self._set_widgets_to_init_state()

    @pyqtSlot()
    def create_new_pin(self, multiplexer_output=None):
        """
        Slot creates new pin.
        :param multiplexer_output: multiplexer output for new pin.
        """

        if self._measurement_plan.image:
            # Place at the center of current viewpoint by default
            width = self._board_window.workspace.width()
            height = self._board_window.workspace.height()
            point = self._board_window.workspace.mapToScene(int(width / 2), int(height / 2))
            pin = Pin(point.x(), point.y(), measurements=[], multiplexer_output=multiplexer_output)
        else:
            pin = Pin(0, 0, measurements=[], multiplexer_output=multiplexer_output)
        self._measurement_plan.append_pin(pin)
        self._board_window.add_pin(pin.x, pin.y, self._measurement_plan.get_current_index())
        self.line_comment_pin.setText(pin.comment or "")

        # It is important to initialize pin with real measurement. Otherwise user can create
        # several empty points and they will not be unique. This will cause some errors during
        # ufiv validation.
        # self._on_save_pin()
        self.update_current_pin()

    @pyqtSlot()
    def create_report(self, auto_start: bool = False):
        """
        Slot shows dialog window to create report for board.
        :param auto_start: if True then generation of report will start automatically.
        """

        if auto_start:
            self._report_generation_window.start_generation()
        if not self._report_generation_window.isVisible():
            self._report_generation_window.show()
        else:
            self._report_generation_window.activateWindow()

    def disconnect_devices(self):
        """
        Method disconnects measurers.
        """

        self._timer.stop()
        if self.start_or_stop_entire_plan_measurement_action.isChecked():
            self.start_or_stop_entire_plan_measurement_action.setChecked(False)
        if self._msystem:
            for measurer in self._msystem.measurers:
                measurer.close_device()
            for multiplexer in self._msystem.multiplexers:
                multiplexer.close_device()
        self._msystem = None
        self._iv_window.plot.set_center_text(qApp.translate("t", "НЕТ ПОДКЛЮЧЕНИЯ"))
        self.enable_widgets(False)
        self._clear_widgets()
        self._product_name = None

    def enable_widgets(self, enabled: bool):
        """
        Method sets widgets to given state (enabled or disabled).
        :param enabled: if True widgets will be set to enabled state.
        """

        widgets = (self.new_file_action, self.open_file_action, self.save_file_action, self.save_as_file_action,
                   self.save_screen_action, self.open_window_board_action, self.open_mux_window_action,
                   self.freeze_curve_a_action, self.freeze_curve_b_action, self.hide_curve_a_action,
                   self.hide_curve_b_action, self.search_optimal_action, self.comparing_mode_action,
                   self.writing_mode_action, self.testing_mode_action, self.settings_mode_action,
                   self.next_point_action, self.previous_point_action, self.new_point_action, self.save_point_action,
                   self.add_board_image_action, self.create_report_action, self.num_point_line_edit,
                   self.start_or_stop_entire_plan_measurement_action, self.add_cursor_action, self.remove_cursor_action,
                   self.score_dock, self.freq_dock, self.current_dock, self.voltage_dock, self.comment_dock,
                   self.measurers_menu)
        for widget in widgets:
            widget.setEnabled(enabled)
        if enabled and len(self._msystem.measurers) < 2:
            self.freeze_curve_b_action.setEnabled(False)
            self.hide_curve_b_action.setEnabled(False)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        Method handles events with main window and some its children (line edit widgets). Method does the following.
        When focus is on main window, navigates between measurement plan points using Left and Right keys, and takes
        measurement using Enter key. When focus is on line edit children, performs standard actions for those widgets.
        When clicking on main window, moves focus to main window.
        :param obj: object for which event occurred;
        :param event: event.
        :return: True if event should be filtered out, otherwise - False.
        """

        if obj in (self.num_point_line_edit, self.line_comment_pin):
            if isinstance(event, QKeyEvent):
                key_event = QKeyEvent(event)
                if key_event.type() == QEvent.KeyPress and key_event.key() in (QtC.Key_Enter, QtC.Key_Return):
                    obj.keyPressEvent(key_event)
                    return True
            return super().eventFilter(obj, event)
        if isinstance(event, QMouseEvent):
            self.setFocus()
        if obj == self and isinstance(event, QKeyEvent) and QKeyEvent(event).type() == QEvent.KeyPress and \
                self.measurement_plan:
            return self._handle_key_press_event(obj, event)
        return super().eventFilter(obj, event)

    def get_measurers(self) -> list:
        """
        Method returns list of measurers.
        :return: list of measurers.
        """

        return self._msystem.measurers if self._msystem else []

    def get_settings(self, threshold: float) -> Settings:
        """
        Method returns current applied settings in object.
        :param threshold: threshold value.
        :return: current settings.
        """

        settings = Settings()
        settings.set_measurement_settings(self._msystem.get_settings())
        if self.testing_mode_action.isChecked():
            settings.work_mode = WorkMode.TEST
        elif self.writing_mode_action.isChecked():
            settings.work_mode = WorkMode.WRITE
        else:
            settings.work_mode = WorkMode.COMPARE
        settings.score_threshold = threshold
        settings.hide_curve_a = bool(self.hide_curve_a_action.isChecked())
        settings.hide_curve_b = bool(self.hide_curve_b_action.isChecked())
        settings.sound_enabled = bool(self.sound_enabled_action.isChecked())
        return settings

    @pyqtSlot(bool)
    def go_to_left_or_right_pin(self, to_prev: bool) -> None:
        """
        Slot moves to next or previous pin in measurement plan.
        :param to_prev: if True, then there will be a transition to the previous point in measurement plan, otherwise -
        to next point.
        """

        try:
            if to_prev:
                self._measurement_plan.go_prev_pin()
            else:
                self._measurement_plan.go_next_pin()
        except BadMultiplexerOutputError:
            if not self._mux_and_plan_window.measurement_plan_runner.is_running:
                ut.show_exception(qApp.translate("t", "Ошибка открытия точки"),
                                  qApp.translate("t", "Подключенный мультиплексор имеет другую конфигурацию, выход "
                                                      "точки не был установлен."))
        except Exception:
            self._device_errors_handler.all_ok = False
        self.update_current_pin()
        self._open_board_window_if_needed()

    @pyqtSlot()
    def go_to_selected_pin(self, pin_index: int = None):
        """
        Slot sets given pin as current.
        :param pin_index: index of pin to be set as current.
        """

        if pin_index is not None:
            self.num_point_line_edit.setText(str(pin_index))
        try:
            pin_index = int(self.num_point_line_edit.text())
        except ValueError:
            ut.show_exception(qApp.translate("t", "Ошибка открытия точки"),
                              qApp.translate("t", "Неверный формат номера точки. Номер точки может принимать только "
                                                  "целочисленное значение!"))
            return
        try:
            with self._device_errors_handler:
                self._measurement_plan.go_pin(pin_index)
        except BadMultiplexerOutputError:
            if not self._mux_and_plan_window.measurement_plan_runner.is_running:
                ut.show_exception(qApp.translate("t", "Ошибка открытия точки"),
                                  qApp.translate("t", "Подключенный мультиплексор имеет другую конфигурацию, выход "
                                                      "точки не был установлен."))
        except ValueError as exc:
            ut.show_exception(qApp.translate("t", "Ошибка открытия точки"),
                              qApp.translate("t", "Точка с таким номером не найдена на данной плате."), str(exc))
            return
        self.update_current_pin()
        self._open_board_window_if_needed()

    def open_settings_from_file(self, file_path: str) -> float:
        """
        Method reads settings from file with given path and returns score threshold.
        :param file_path: path to file with settings.
        :return: score threshold.
        """

        self.__settings = Settings()
        self.__settings.import_(path=file_path)
        return self.__settings.score_threshold

    def resizeEvent(self, event: QResizeEvent):
        """
        Method handles resizing of main window.
        :param event: resizing event.
        """

        # Determine the critical width of the window for given language and OS
        lang = qApp.instance().property("language")
        if system().lower() == "windows":
            size = self.CRITICAL_WIDTH_FOR_WINDOWS_EN if lang is Language.EN else self.CRITICAL_WIDTH_FOR_WINDOWS_RU
        else:
            size = self.CRITICAL_WIDTH_FOR_LINUX_EN if lang is Language.EN else self.CRITICAL_WIDTH_FOR_LINUX_RU
        # Change style of toolbars
        tool_bars = self.toolBar_write, self.toolBar_cursor, self.toolBar_mode
        for tool_bar in tool_bars:
            if self.width() < size:
                style = QtC.ToolButtonIconOnly
            else:
                style = QtC.ToolButtonTextBesideIcon
            tool_bar.setToolButtonStyle(style)
        super().resizeEvent(event)

    @pyqtSlot()
    def save_pin(self) -> None:
        """
        Slot saves IV-curve to current pin.
        """

        with self._device_errors_handler:
            if self._work_mode == WorkMode.WRITE:
                self._measurement_plan.save_last_measurement_as_reference(True)
            elif self._work_mode == WorkMode.TEST:
                self._measurement_plan.save_last_measurement_as_test()
        self._on_save_comment()
        self.update_current_pin()

    @pyqtSlot(IVMeasurerBase, str, bool)
    def show_device_settings(self, selected_measurer: IVMeasurerBase, device_name: str, _: bool):
        """
        Slot shows window to select device settings.
        :param selected_measurer: measurer for which device settings should be displayed;
        :param device_name: name of measurer;
        :param _: not used.
        """

        for measurer in self._msystem.measurers:
            if measurer == selected_measurer:
                all_settings = measurer.get_all_settings()
                dialog = MeasurerSettingsWindow(self, all_settings, measurer, device_name)
                self.measurers_disconnected.connect(dialog.close)
                if dialog.exec_():
                    dialog.set_parameters()
                return

    def update_current_pin(self) -> None:
        """
        Call this method when current pin index changed.
        """

        index = self._measurement_plan.get_current_index()
        self.num_point_line_edit.setText(str(index))
        self._board_window.workspace.select_point(index)
        if self._work_mode in (WorkMode.TEST, WorkMode.WRITE):
            current_pin = self._measurement_plan.get_current_pin()
            self.line_comment_pin.setText(current_pin.comment or "")
            ref_for_plan, test_for_plan, settings = current_pin.get_reference_and_test_measurements()
            with self._device_errors_handler:
                if settings:
                    curves = {"ref": None if not ref_for_plan else ref_for_plan.ivc,
                              "test_for_plan": None if not test_for_plan else test_for_plan.ivc}
                    self._set_msystem_settings(settings)
                    options = self._product.settings_to_options(settings)
                    self._set_options_to_ui(options)
                    self._update_curves(curves, self._msystem.measurers[0].get_settings())
                else:
                    self._update_curves({"ref": None, "test_for_plan": None}, self._msystem.measurers[0].get_settings())
        if self._mux_and_plan_window:
            self._mux_and_plan_window.select_current_pin()
