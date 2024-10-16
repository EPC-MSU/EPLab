"""
File with the class of the main window of application.
"""

import copy
import logging
import os
import re
from datetime import datetime
from functools import partial
from platform import system
from typing import Any, Dict, List, Optional, Tuple
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, QEvent, QPointF, Qt, QTimer, QTranslator
from PyQt5.QtGui import QCloseEvent, QColor, QIcon, QKeySequence, QMouseEvent, QResizeEvent
from PyQt5.QtWidgets import (QAction, QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QShortcut, QStyle,
                             QVBoxLayout, QWidget)
from PyQt5.uic import loadUi
import epcore.filemanager as epfilemanager
from epcore.analogmultiplexer import BadMultiplexerOutputError
from epcore.elements import Board, Element, ImageNotFoundError, IVCurve, Measurement, MeasurementSettings, Pin
from epcore.ivmeasurer import IVMeasurerASA, IVMeasurerBase, IVMeasurerIVM10, IVMeasurerVirtual, IVMeasurerVirtualASA
from epcore.measurementmanager import IVCComparator, MeasurementPlan, MeasurementSystem, Searcher
from epcore.product import EyePointProduct, MeasurementParameterOption
from ivviewer import Viewer as IVViewer
from ivviewer.ivcviewer import PlotCurve
import connection_window as cw
from dialogs import (ReportGenerationThread, show_keymap_info, show_language_selection_window,
                     show_measurer_settings_window, show_product_info, show_report_generation_window)
from multiplexer import MuxAndPlanWindow
from settings import AutoSettings, LowSettingsPanel, Settings, SettingsWindow
from version import Version
from . import utils as ut
from .boardwidget import BoardWidget
from .breaksignaturessaver import BreakSignaturesSaver, check_break_signatures
from .commentwidget import CommentWidget
from .common import DeviceErrorsHandler, WorkMode
from .connectionchecker import analyze_connection_params, ConnectionChecker, ConnectionData
from .curvestates import CurveStates
from .language import get_language, Language, Translator
from .measuredpinschecker import MeasuredPinsChecker
from .measurementplanpath import MeasurementPlanPath
from .parameterwidget import ParameterWidget
from .pedalhandler import add_pedal_handler
from .pinindexwidget import PinIndexWidget
from .planautotransition import PlanAutoTransition
from .plancompatibility import PlanCompatibility
from .scaler import get_scale_factor, update_scale_of_action, update_scale_of_class
from .scorewrapper import check_difference_not_greater_tolerance, ScoreWrapper
from .soundplayer import SoundPlayer


logger = logging.getLogger("eplab")


@add_pedal_handler
@update_scale_of_class
class EPLabWindow(QMainWindow):
    """
    Class for the main window of application.
    """

    COLOR_FOR_CURRENT: QColor = QColor(255, 0, 0, 200)
    COLOR_FOR_REFERENCE: QColor = QColor(0, 128, 255, 200)
    COLOR_FOR_TEST: QColor = QColor(255, 129, 129, 200)
    CRITICAL_WIDTH_FOR_LINUX_EN: int = 1535
    CRITICAL_WIDTH_FOR_LINUX_RU: int = 1740
    CRITICAL_WIDTH_FOR_WINDOWS_EN: int = 1230
    CRITICAL_WIDTH_FOR_WINDOWS_RU: int = 1415
    DEFAULT_COMPARATOR_MIN_CURRENT: float = 0.002
    DEFAULT_COMPARATOR_MIN_VOLTAGE: float = 0.6
    DELAY_TO_GO_TO_NEXT_PIN_MS: int = 500
    FILENAME_FOR_AUTO_SETTINGS: str = os.path.join(ut.get_dir_name(), "eplab_settings_for_auto_save_and_read.ini")
    INIT_HEIGHT: int = 730
    MIN_WIDTH_IN_LINUX: int = 700
    MIN_WIDTH_IN_WINDOWS: int = 650
    measurers_connected: pyqtSignal = pyqtSignal(bool)
    measurers_disconnected: pyqtSignal = pyqtSignal()
    work_mode_changed: pyqtSignal = pyqtSignal(WorkMode)

    def __init__(self, product: EyePointProduct, uri_1: Optional[str] = None, uri_2: Optional[str] = None,
                 english: Optional[bool] = None, path: str = None) -> None:
        """
        :param product: product;
        :param uri_1: URI for the first IV-measurer;
        :param uri_2: URI for the second IV-measurer;
        :param english: if True then interface language will be English;
        :param path: path to the measurement plan to be opened.
        """

        super().__init__()
        self._auto_settings: AutoSettings = AutoSettings(path=EPLabWindow.FILENAME_FOR_AUTO_SETTINGS)
        self._comparator: IVCComparator = IVCComparator()
        self._device_errors_handler: DeviceErrorsHandler = DeviceErrorsHandler()
        self._dir_chosen_by_user: str = ut.get_user_documents_path()
        self._hide_reference_curve: bool = False
        self._hide_current_curve: bool = False
        self._last_saved_measurement_plan_data: Optional[Dict[str, Any]] = None
        self._measurement_plan: Optional[MeasurementPlan] = None
        self._measured_pins_checker: MeasuredPinsChecker = MeasuredPinsChecker(self)
        self._measured_pins_checker.measured_pin_in_plan_signal.connect(self.handle_measurement_plan_change)
        self._measurement_plan_path: MeasurementPlanPath = MeasurementPlanPath(self)
        self._measurement_plan_path.name_changed.connect(self.change_window_title)
        self._msystem: Optional[MeasurementSystem] = None
        self._product: EyePointProduct = product
        self._product_name: Optional[cw.ProductName] = None
        self._report_generation_thread: ReportGenerationThread = ReportGenerationThread(self)
        self._report_generation_thread.start()
        self._skip_curve: bool = False  # set to True to skip next measured curves

        self._timer: QTimer = QTimer()
        self._timer.setInterval(10)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._handle_periodic_task)

        self._timer_to_go_to_next_pin: QTimer = QTimer()
        self._timer_to_go_to_next_pin.setInterval(EPLabWindow.DELAY_TO_GO_TO_NEXT_PIN_MS)
        self._timer_to_go_to_next_pin.setSingleShot(True)
        self._timer_to_go_to_next_pin.timeout.connect(lambda: self.go_to_left_or_right_pin(False, False))

        self._work_mode: Optional[WorkMode] = None

        self._load_translation(english)
        self._init_ui()
        self._adjust_critical_width()
        self._set_init_position()
        self._connect_scale_change_signal()
        self.measurers_connected.connect(self.handle_connection)
        self._connection_checker: ConnectionChecker = ConnectionChecker(self._auto_settings)
        self._connection_checker.connect_signal.connect(self.handle_connection_signal_from_checker)
        self._break_signature_saver: BreakSignaturesSaver = BreakSignaturesSaver(self.product, self._auto_settings)
        self._break_signature_saver.new_settings_signal.connect(self.set_measurement_settings_and_update_ui)
        self._plan_auto_transition: PlanAutoTransition = PlanAutoTransition(self.product, self._auto_settings,
                                                                            self._score_wrapper,
                                                                            self._calculate_difference,
                                                                            self._break_signature_saver.DIR_PATH)
        self._plan_auto_transition.go_to_next_signal.connect(self.go_to_left_or_right_pin)
        self._plan_auto_transition.save_pin_signal.connect(self.save_pin)

        if uri_1 is None and uri_2 is None:
            self._connection_checker.run_check()
            self._disconnect_devices()
        else:
            uris, product_name = analyze_connection_params([uri_1, uri_2])
            self.connect_devices(*uris, product_name=product_name)

        if path:
            self.load_board(path)

    @property
    def device_errors_handler(self) -> DeviceErrorsHandler:
        """
        :return: device errors handler.
        """

        return self._device_errors_handler

    @property
    def dir_chosen_by_user(self) -> str:
        """
        :return: the last directory that the user selected when working with the application.
        """

        if os.path.exists(self._dir_chosen_by_user) and os.path.isdir(self._dir_chosen_by_user):
            return self._dir_chosen_by_user

        return ut.get_user_documents_path()

    @dir_chosen_by_user.setter
    def dir_chosen_by_user(self, path: str) -> None:
        """
        :param path: path chosen by the user when working with the application.
        """

        if os.path.exists(path):
            self._dir_chosen_by_user = os.path.dirname(path) if not os.path.isdir(path) else path
            self._iv_window.plot.set_path_to_directory(self._dir_chosen_by_user)

    @property
    def can_be_measured(self) -> bool:
        """
        :return: True if the measurement at the current pin can be carried out, otherwise False. Used for auto
        measurement according to plan.
        """

        if self._work_mode is WorkMode.WRITE:
            return True

        if self._work_mode is WorkMode.TEST and not self._measured_pins_checker.check_empty_current_pin():
            return True

        return False

    @property
    def is_measured_pin(self) -> bool:
        """
        :return: True, if the measurement plan contains a pin with a measured reference signature.
        """

        return self._measured_pins_checker.is_measured_pin

    @property
    def measurement_plan(self) -> Optional[MeasurementPlan]:
        """
        :return: object with measurement plan.
        """

        return self._measurement_plan

    @property
    def product(self) -> EyePointProduct:
        """
        :return: product object.
        """

        return self._product

    @property
    def tolerance(self) -> float:
        """
        :return: tolerance value for comparing signatures.
        """

        return self._score_wrapper.tolerance

    @property
    def work_mode(self) -> Optional[WorkMode]:
        """
        :return: current operating mode.
        """

        return self._work_mode

    def _add_callbacks_to_measurement_plan(self) -> None:
        """
        Method adds the required callback functions to the measurement plan.
        """

        self.measurement_plan.remove_all_callback_funcs_for_pin_changes()
        self.measurement_plan.add_callback_func_for_pin_changes(self._change_menu_items_for_current_pin_change)
        self.measurement_plan.add_callback_func_for_pin_changes(
            self._measured_pins_checker.handle_measurement_plan_change)
        self.measurement_plan.remove_all_callback_funcs_for_mux_output_change()
        self.measurement_plan.add_callback_func_for_mux_output_change(
            self._mux_and_plan_window.multiplexer_pinout_widget.set_connected_channel)

    def _adjust_critical_width(self) -> None:
        """
        Method updates the critical window width at which it is necessary to change the toolbar display mode from text
        to icon. When updating the width, the current screen scale is taken into account.
        """

        scale_factor = get_scale_factor()
        for width in ("CRITICAL_WIDTH_FOR_LINUX_EN", "CRITICAL_WIDTH_FOR_LINUX_RU", "CRITICAL_WIDTH_FOR_WINDOWS_EN",
                      "CRITICAL_WIDTH_FOR_WINDOWS_RU", "INIT_HEIGHT", "MIN_WIDTH_IN_LINUX", "MIN_WIDTH_IN_WINDOWS"):
            width_value = getattr(self, width, None)
            if isinstance(width_value, (int, float)):
                setattr(self, width, int(scale_factor * width_value))

    def _adjust_plot_params(self, settings: MeasurementSettings) -> None:
        """
        :param settings: measurement settings for which plot parameters to adjust.
        """

        scale = ut.calculate_scales(settings)
        self._iv_window.plot.set_scale(*scale)
        self._iv_window.plot.set_min_borders(*scale)

    def _calculate_difference(self, curve_1: IVCurve, curve_2: IVCurve, settings: MeasurementSettings) -> float:
        """
        :param curve_1: first signature;
        :param curve_2: second signature;
        :param settings: measurement settings.
        :return: difference between given signatures at given settings.
        """

        # It is very important to set relevant noise levels
        self._comparator.set_min_ivc(*self._get_noise_amplitudes(settings))
        return self._comparator.compare_ivc(curve_1, curve_2)

    def _change_menu_items_for_current_pin_change(self, *args) -> None:
        """
        Method changes the states of menu items when the current pin in the measurement plan changes.
        """

        if self._mux_and_plan_window.measurement_plan_runner.is_running:
            return

        if self.measurement_plan.pins_number == 0:
            for action in (self.next_point_action, self.previous_point_action, self.remove_point_action,
                           self.save_point_action, self.pin_index_widget):
                action.setEnabled(False)
        else:
            enable = bool(self.work_mode is WorkMode.WRITE and self.measurement_plan.multiplexer is None)
            self.remove_point_action.setEnabled(enable)
            enable = self.work_mode is not WorkMode.COMPARE
            for action in (self.next_point_action, self.previous_point_action, self.pin_index_widget):
                action.setEnabled(enable)
            self.save_point_action.setEnabled(self.work_mode != WorkMode.READ_PLAN)
            self.set_enabled_save_point_action_at_test_mode()

    def _change_save_point_action_name(self, mode: Optional[WorkMode] = None) -> None:
        """
        :param mode: new work mode.
        """

        save_point_names = {WorkMode.COMPARE: qApp.translate("t", "Зафиксировать"),
                            WorkMode.TEST: qApp.translate("t", "Зафиксировать тест"),
                            WorkMode.WRITE: qApp.translate("t", "Зафиксировать эталон")}
        name = save_point_names.get(mode, qApp.translate("t", "Зафиксировать"))
        self.save_point_action.setIconText(name)
        self.save_point_action.setText(name)

    def _change_work_mode(self, mode: WorkMode) -> None:
        """
        Method changes window widgets for given work mode.
        :param mode: new work mode.
        """

        if mode == WorkMode.READ_PLAN:
            self.open_window_board_action.setEnabled(True)
        enable = bool(self.measurement_plan and self.measurement_plan.multiplexer is not None)
        self.open_mux_window_action.setEnabled(enable)
        self.comparing_mode_action.setChecked(mode is WorkMode.COMPARE)
        self.writing_mode_action.setChecked(mode is WorkMode.WRITE)
        self.testing_mode_action.setChecked(mode is WorkMode.TEST)
        enable = mode is not WorkMode.COMPARE
        self.next_point_action.setEnabled(enable)
        self.previous_point_action.setEnabled(enable)
        self.pin_index_widget.setEnabled(enable)
        enable = bool(mode is WorkMode.WRITE and
                      not (self.measurement_plan and self.measurement_plan.multiplexer is not None))
        self.new_point_action.setEnabled(enable)
        self.remove_point_action.setEnabled(enable and self.measurement_plan.pins_number > 0)
        self.save_point_action.setEnabled(mode != WorkMode.READ_PLAN)
        self.add_board_image_action.setEnabled(mode is WorkMode.WRITE)
        self.create_report_action.setEnabled(mode not in (WorkMode.COMPARE, WorkMode.READ_PLAN))
        enable = bool(mode is not WorkMode.COMPARE and self.measurement_plan and
                      self.measurement_plan.multiplexer is not None)
        self.start_or_stop_entire_plan_measurement_action.setEnabled(enable)
        self._change_save_point_action_name(mode)

        self._player.set_work_mode(mode)
        self._comment_widget.set_work_mode(mode)
        self._disable_optimal_parameter_searcher(mode)
        if mode is WorkMode.COMPARE and len(self._msystem.measurers) < 2:
            # Remove reference curve in case we have only one IVMeasurer in compare mode
            self._remove_ref_curve()
        # Drag allowed only in write mode
        self._board_window.allow_drag(mode is WorkMode.WRITE)
        # Disable settings in test mode
        for scroll_area in self._parameters_widgets.values():
            scroll_area.enable_buttons(mode in (WorkMode.COMPARE, WorkMode.WRITE))

        if mode is WorkMode.READ_PLAN:
            _ = [dock_widget.setEnabled(True) for dock_widget in (self.comment_dock, self.score_dock, self.freq_dock,
                                                                  self.current_dock, self.voltage_dock)]
            _ = [widget.setEnabled(False) for widget in self._parameters_widgets.values()]
        elif mode is WorkMode.TEST:
            self._check_break_signatures_for_auto_transition()

        self._compare_measurement = None
        self._work_mode = mode

    def _change_work_mode_for_new_measurement_plan(self) -> None:
        """
        Method changes the work mode of the main window when a new measurement plan is initialized. If the new plan
        does not contain pins with measured reference signatures, and the current work mode is TEST, then you need to
        change the work mode to COMPARE (see ticket #89690).
        """

        if self._work_mode == WorkMode.TEST and not self.is_measured_pin:
            self._change_work_mode(WorkMode.COMPARE)

    def _check_break_signatures_for_auto_transition(self) -> None:
        """
        Method checks whether auto transition is set in test mode according to plan. If auto transition is set, then
        the presence of break signatures is checked for all measurement settings.
        """

        if (self._auto_settings.auto_transition and self._product_name not in (None, cw.ProductName.EYEPOINT_H10)
                and not check_break_signatures(self._break_signature_saver.DIR_PATH, self._product)):
            ut.show_message(qApp.translate("t", "Информация"),
                            qApp.translate("t", "Включен автопереход в режиме тестирования по плану. Но в приложении "
                                                "нет некоторых сигнатур разрыва, поэтому автопереход может работать "
                                                "некорректно."), icon=QMessageBox.Information)

    def _check_plan_compatibility(self, plan: MeasurementPlan, is_new_plan: bool = False,
                                  filename: Optional[str] = None) -> None:
        """
        Method checks the measurement plan for compatibility with the product (available measurement settings) and
        multiplexer.
        :param plan: measurement plan that is checked for compatibility;
        :param is_new_plan: if True, then the new measurement plan will be checked for compatibility;
        :param filename: name of the measurement plan file.
        """

        checker = PlanCompatibility(self, self._msystem, self._product)
        self._measurement_plan, new_plan_created = checker.get_compatible_plan(plan, is_new_plan, filename)
        self._measurement_plan_path.path = None if new_plan_created else filename

        self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
        self._measured_pins_checker.set_new_plan()
        self._update_mux_actions()

    def _check_transition_without_break(self, to_prev: bool) -> bool:
        """
        :param to_prev: if True, then the transition should be to the previous pin in the measurement plan, otherwise
        to the next one.
        :return: True if the transition can be made without breaking (that is, it is not a transition from the last pin
        to the first or from the first to the last).
        """

        current_pin_index = self._measurement_plan.get_current_index()
        if ((to_prev and current_pin_index == 0) or
                (not to_prev and current_pin_index == self._measurement_plan.pins_number - 1)):
            return False

        return True

    def _clear_widgets(self) -> None:
        """
        Method clears widgets on the main window.
        """

        self._comparator.set_min_ivc(*self._get_noise_amplitudes())

        for widget in (self.freq_dock_widget, self.current_dock_widget, self.voltage_dock_widget):
            layout = widget.layout()
            ut.clear_layout(layout)

        for action in (self.comparing_mode_action, self.writing_mode_action, self.testing_mode_action):
            action.setChecked(False)

        self.low_settings_panel.clear_panel()
        self.measurers_menu.clear()
        self.pin_index_widget.clear()
        self._iv_window.plot.remove_all_cursors()
        self._mux_and_plan_window.close()
        self._score_wrapper.set_dummy_difference()

        self._settings_update_next_cycle = None
        self._skip_curve = False
        self._work_mode = None
        self._hide_current_curve = False
        self._hide_reference_curve = False
        self._compare_measurement = None
        self._current_curve = None
        self._reference_curve = None
        self._test_curve = None
        self._change_save_point_action_name()

    def _connect_devices(self, measurement_system: MeasurementSystem, product_name: Optional[cw.ProductName] = None
                         ) -> None:
        """
        :param measurement_system: measurement system with measurers and multiplexer;
        :param product_name: product name.
        """

        self._msystem = measurement_system

        self._clear_widgets()
        self._comment_widget.clear_table()
        self._iv_window.plot.clear_center_text()
        options_data = self._read_options_from_json()
        self._product.change_options(options_data)
        if product_name is None:
            self._product_name = cw.ProductName.get_default_product_name_for_measurers(self._msystem.measurers)
        else:
            self._product_name = product_name
        self.enable_widgets(True)

        if self.measurement_plan:
            self._check_plan_compatibility(self.measurement_plan, False, self._measurement_plan_path.path)
        else:
            self._reset_board()

        self._set_widgets_to_init_state()
        self.measurers_connected.emit(True)
        self._timer.start()

    def _connect_scale_change_signal(self) -> None:
        """
        Method connects the screen zoom signal.
        """

        screens = qApp.instance().screens()
        if len(screens) > 0:
            screen = screens[0]
            screen.logicalDotsPerInchChanged.connect(self.handle_scale_change)

    def _create_measurer_setting_actions(self) -> None:
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
            update_scale_of_action(action)
            self.measurers_menu.addAction(action)

    def _create_scroll_areas_for_parameters(self, available: Dict[EyePointProduct.Parameter,
                                                                  List[MeasurementParameterOption]]) -> None:
        """
        Method creates scroll areas for different parameters of the measuring system. Scroll areas have radio buttons
        to choose options of parameters.
        :param available: dictionary with available options for parameters.
        """

        self._parameters_widgets = dict()
        layouts = [widget.layout() for widget in (self.freq_dock_widget, self.voltage_dock_widget,
                                                  self.current_dock_widget)]
        parameters = (EyePointProduct.Parameter.frequency, EyePointProduct.Parameter.voltage,
                      EyePointProduct.Parameter.sensitive)
        for layout, parameter in zip(layouts, parameters):
            widget = ParameterWidget(parameter, available[parameter])
            widget.option_changed.connect(self.select_option)
            self._parameters_widgets[parameter] = widget
            ut.clear_layout(layout)
            layout.addWidget(widget)

    def _delete_measurement_plan(self) -> None:
        self._last_saved_measurement_plan_data = None
        self._measurement_plan = None
        self._measured_pins_checker.set_new_plan()
        self._measurement_plan_path.path = None

    def _disable_optimal_parameter_searcher(self, mode: WorkMode = None) -> None:
        """
        Method disables searcher of the optimal parameters. Searcher can work only for IVMeasurerIVM10.
        :param mode: work mode.
        """

        if self._msystem:
            for measurer in self._msystem.measurers:
                if isinstance(measurer, (IVMeasurerASA, IVMeasurerVirtualASA)):
                    self.search_optimal_action.setEnabled(False)
                    return

        if mode is None:
            mode = self.work_mode
        self.search_optimal_action.setEnabled(mode in (WorkMode.COMPARE, WorkMode.WRITE))

    def _disconnect_devices(self) -> None:
        self._timer.stop()
        if self.start_or_stop_entire_plan_measurement_action.isChecked():
            self.start_or_stop_entire_plan_measurement_action.setChecked(False)
        if self._msystem:
            for measurer in self._msystem.measurers:
                measurer.close_device()
            for multiplexer in self._msystem.multiplexers:
                multiplexer.close_device()

        self._msystem = None
        self._product_name = None
        self._iv_window.plot.set_center_text(qApp.translate("t", "НЕТ ПОДКЛЮЧЕНИЯ"))
        self.enable_widgets(False)
        self._clear_widgets()
        self._comment_widget.clear_table()
        self._board_window.close()

    def _get_curves_for_legend(self) -> Dict[str, bool]:
        """
        :return: a dictionary containing the signatures displayed in the application window.
        """

        return {"current": bool(self.current_curve_plot.curve),
                "reference": bool(self.reference_curve_plot.curve),
                "test": bool(self.test_curve_plot.curve)}

    def _get_curves_for_periodic_task(self) -> Tuple[Dict[str, IVCurve], MeasurementSettings]:
        """
        :return: dictionary with current measurements and measurement settings.
        """

        curves = {"current": self._msystem.measurers[0].get_last_cached_iv_curve()}
        if self._work_mode is WorkMode.COMPARE and len(self._msystem.measurers) > 1:
            # Display two current curves
            curves["reference"] = self._msystem.measurers[1].get_last_cached_iv_curve()
        measurement_settings = self._msystem.get_settings()

        if self._compare_measurement:
            if self._compare_measurement.settings == measurement_settings:
                curves["compare"] = self._compare_measurement.ivc
            else:
                self._compare_measurement = None
        return curves, measurement_settings

    def _get_noise_amplitudes(self, settings: Optional[MeasurementSettings] = None) -> Tuple[float, float]:
        """
        :param settings: measurement settings.
        :return: noise amplitudes of voltage and current for given measurement settings.
        """

        if settings is None or self._product is None:
            return EPLabWindow.DEFAULT_COMPARATOR_MIN_VOLTAGE, EPLabWindow.DEFAULT_COMPARATOR_MIN_CURRENT

        return self._product.adjust_noise_amplitude(settings)

    def _get_options_from_ui(self) -> Dict[EyePointProduct.Parameter, str]:
        """
        :return: dictionary with selected options for parameters of measuring system from UI.
        """

        return {param: widget.get_checked_option() for param, widget in self._parameters_widgets.items()}

    def _go_to_left_or_right_pin_for_hotkeys(self, prev_pin: bool) -> None:
        """
        Method processes signals from hotkeys UP and DOWN to move through pins.
        :param prev_pin: if True, then there will be a transition to the previous pin in measurement plan, otherwise -
        to the next pin.
        """

        action = self.previous_point_action if prev_pin else self.next_point_action
        if action.isEnabled():
            self.go_to_left_or_right_pin(prev_pin)

    def _handle_freezing_curves_with_pedal(self, pressed: bool) -> None:
        """
        Method freezes the measurers signatures using a pedal. The signatures are frozen when the pedal is pressed in
        comparison mode. And they defrost when the pedal is released.
        :param pressed: if True, then the pedal is pressed, otherwise it is released.
        """

        if pressed:
            self._curves_states.store_states()
            for action in (self.freeze_curve_a_action, self.freeze_curve_b_action):
                if action.isEnabled() and not action.isChecked():
                    action.trigger()
                action.setEnabled(False)
        else:
            self._curves_states.restore_states()

    @pyqtSlot()
    def _handle_periodic_task(self) -> None:
        if self._device_errors_handler.all_ok:
            with self._device_errors_handler:
                self._read_curves_periodic_task()
            self._plan_auto_transition.save_measurements()
            self._mux_and_plan_window.measurement_plan_runner.save_measurements()
            self._timer.start()  # add this task to the event loop
        else:
            self._device_errors_handler.reset_error()
            self._mux_and_plan_window.close_and_stop_plan_measurement()
            self._disconnect_devices()
            self._connection_checker.run_check()

    def _init_tolerance(self) -> None:
        """
        Method initializes the initial value of the tolerance.
        """

        self._update_tolerance(self._score_wrapper.tolerance)

    def _init_ui(self) -> None:
        loadUi(os.path.join(os.path.dirname(ut.DIR_MEDIA), "gui", "mainwindow.ui"), self)
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
        self.setWindowTitle(self.windowTitle() + " " + Version.full)

        self._board_window: BoardWidget = BoardWidget(self)
        self._board_window.current_pin_signal.connect(self.go_to_selected_pin)
        self._parameters_widgets: Dict[EyePointProduct.Parameter, ParameterWidget] = dict()
        self._player: SoundPlayer = SoundPlayer()
        self._player.set_mute(not self.sound_enabled_action.isChecked())
        self._score_wrapper: ScoreWrapper = ScoreWrapper(self.score_label)

        self.low_settings_panel: LowSettingsPanel = LowSettingsPanel()
        self.main_widget: QWidget = QWidget(self)
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self._iv_window: IVViewer = IVViewer(self.main_widget, grid_color=QColor(255, 255, 255),
                                             back_color=QColor(0, 0, 0), solid_axis_enabled=False,
                                             axis_label_enabled=False, color_for_rest_cursors=QColor(102, 255, 0),
                                             color_for_selected_cursor=QColor(102, 255, 0))
        self._iv_window.setFocusPolicy(Qt.ClickFocus)
        self._iv_window.layout().setContentsMargins(0, 0, 0, 0)
        self._iv_window.plot.default_path_changed.connect(self.set_dir_chosen_by_user)
        self._iv_window.plot.enable_context_menu()
        self._iv_window.plot.localize_widget(add_cursor=qApp.translate("t", "Добавить метку"),
                                             export_ivc=qApp.translate("t", "Экспортировать сигнатуры в файл"),
                                             remove_all_cursors=qApp.translate("t", "Удалить все метки"),
                                             remove_cursor=qApp.translate("t", "Удалить метку"),
                                             save_screenshot=qApp.translate("MainWindow", "Сохранить скриншот"))
        self._iv_window.plot.set_path_to_directory(self.dir_chosen_by_user)
        self.current_curve_plot: PlotCurve = self._iv_window.plot.add_curve("Current signature")
        self.current_curve_plot.set_curve_params(EPLabWindow.COLOR_FOR_CURRENT)
        self.reference_curve_plot: PlotCurve = self._iv_window.plot.add_curve("Reference signature")
        self.reference_curve_plot.set_curve_params(EPLabWindow.COLOR_FOR_REFERENCE)
        self.test_curve_plot: PlotCurve = self._iv_window.plot.add_curve("Test signature")
        self.test_curve_plot.set_curve_params(EPLabWindow.COLOR_FOR_TEST)

        v_box_layout = QVBoxLayout()
        v_box_layout.setSpacing(0)
        v_box_layout.addWidget(self._iv_window)
        v_box_layout.addWidget(self.low_settings_panel)
        h_box_layout = QHBoxLayout(self.main_widget)
        h_box_layout.addLayout(v_box_layout)

        self.connection_action.triggered.connect(self.connect_or_disconnect)
        self.open_window_board_action.triggered.connect(self.open_board_image)
        self.open_mux_window_action.triggered.connect(self.open_mux_window)
        self.search_optimal_action.triggered.connect(self.search_optimal)
        self.new_file_action.triggered.connect(self.create_new_board)
        self.open_file_action.triggered.connect(self.load_board)
        self.save_file_action.triggered.connect(self.save_board)
        self.save_as_file_action.triggered.connect(self.save_board_as)
        self.previous_point_action.triggered.connect(lambda: self.go_to_left_or_right_pin(True))
        self.pin_index_widget: PinIndexWidget = PinIndexWidget(self)
        self.pin_index_widget.setEnabled(False)
        self.toolbar_test.insertWidget(self.next_point_action, self.pin_index_widget)
        self.pin_index_widget.returnPressed.connect(self.go_to_pin_selected_in_widget)
        self.next_point_action.triggered.connect(lambda: self.go_to_left_or_right_pin(False))
        self._set_hotkeys_for_moving_through_pins()
        self.new_point_action.triggered.connect(self.create_new_pin)
        self.remove_point_action.triggered.connect(self.remove_pin)
        self.save_point_action.triggered.connect(self.save_pin_and_go_to_next)
        self.add_board_image_action.triggered.connect(self.load_board_image)
        self.create_report_action.triggered.connect(self.create_report)
        self.about_action.triggered.connect(show_product_info)
        self.action_keymap.triggered.connect(lambda: show_keymap_info(self))
        self.sound_enabled_action.toggled.connect(self.enable_sound)
        self.freeze_curve_a_action.toggled.connect(partial(self.freeze_curve, 0))
        self.freeze_curve_b_action.toggled.connect(partial(self.freeze_curve, 1))
        self._curves_states: CurveStates = CurveStates(self.freeze_curve_a_action, self.freeze_curve_b_action)
        self.hide_curve_a_action.toggled.connect(self.hide_curve)
        self.hide_curve_b_action.toggled.connect(self.hide_curve)
        self.save_screen_action.triggered.connect(self.save_image)
        self.select_language_action.triggered.connect(self.select_language)

        self.comparing_mode_action.triggered.connect(lambda: self._switch_work_mode(WorkMode.COMPARE))
        self.writing_mode_action.triggered.connect(lambda: self._switch_work_mode(WorkMode.WRITE))
        self.testing_mode_action.triggered.connect(lambda: self._switch_work_mode(WorkMode.TEST))
        self.settings_mode_action.triggered.connect(self.show_settings_window)

        self._comment_widget: CommentWidget = CommentWidget(self)
        self._comment_widget.current_row_signal.connect(self.go_to_selected_pin)
        self.comment_vertical_layout.insertWidget(0, self._comment_widget)

        # Update plot settings at next measurement cycle (place settings here or None)
        self._settings_update_next_cycle: Optional[MeasurementSettings] = None
        self._compare_measurement: Optional[Measurement] = None
        self._current_curve: Optional[IVCurve] = None
        self._reference_curve: Optional[IVCurve] = None
        self._test_curve: Optional[IVCurve] = None
        self._mux_and_plan_window: MuxAndPlanWindow = MuxAndPlanWindow(self)
        self._mux_and_plan_window.measurement_plan_widget.current_row_signal.connect(self.go_to_selected_pin)
        self.work_mode_changed.connect(self._mux_and_plan_window.change_work_mode)
        self.start_or_stop_entire_plan_measurement_action.triggered.connect(
            self._mux_and_plan_window.start_or_stop_plan_measurement)

    def _load_translation(self, english: Optional[bool] = None) -> None:
        """
        :param english: if True then the interface language will be English.
        """

        language = Language.EN if english else self._auto_settings.language
        if language is not Language.RU:
            translation_file = Translator.get_translator_file(language)
            self._translator: QTranslator = QTranslator()
            self._translator.load(translation_file)
            qApp.instance().installTranslator(self._translator)
        qApp.instance().setProperty("language", language)

    def _open_board_window_if_needed(self) -> None:
        if self._measurement_plan.image:
            if not self._board_window.isVisible():
                self._board_window.show()
            else:
                self._board_window.activateWindow()

    def _read_measurement_plan(self, filename: Optional[str] = None) -> Tuple[Optional[Board], Optional[str]]:
        """
        :param filename: path to the file with the measurement plan that needs to be opened.
        :return: measurement plan read from file and file name.
        """

        if not (isinstance(filename, str) and os.path.exists(filename)):
            filename = QFileDialog.getOpenFileName(self, qApp.translate("MainWindow", "Открыть план тестирования"),
                                                   directory=self.dir_chosen_by_user,
                                                   filter="Board Files (*.json *.uzf)")[0]
        board = None
        if filename:
            try:
                board = epfilemanager.load_board_from_ufiv(filename, auto_convert_p10=True)
                self.dir_chosen_by_user = filename
            except ImageNotFoundError:
                ut.show_message(qApp.translate("t", "Ошибка"),
                                qApp.translate("t", "Формат файла не подходит. Указан неверный путь до изображения "
                                                    "платы."))
            except Exception as exc:
                ut.show_message(qApp.translate("t", "Ошибка"), qApp.translate("t", "Формат файла не подходит."),
                                detailed_text=str(exc))
        return board, filename

    def _read_curves_periodic_task(self) -> None:
        if self._msystem.measurements_are_ready():
            if self._skip_curve:
                self._skip_curve = False
            else:
                curves, measurement_settings = self._get_curves_for_periodic_task()
                self._update_signatures(curves, measurement_settings)
                if self._mux_and_plan_window.measurement_plan_runner.is_running:
                    self._mux_and_plan_window.measurement_plan_runner.check_pin()
                elif self.measurement_plan and not self.measurement_plan.multiplexer:
                    self._plan_auto_transition.check_auto_transition(self.work_mode, self._product_name,
                                                                     measurement_settings, self._current_curve,
                                                                     self._reference_curve)
                    # Break signatures are only saved when debugging the application
                    # self._break_signature_saver.save_signature(measurement_settings, curves["current"])

                if self._settings_update_next_cycle:
                    # New curve with new settings - we must update plot parameters
                    self._adjust_plot_params(self._settings_update_next_cycle)
                    self._settings_update_next_cycle = None
                    # You need to redraw markers with new plot parameters (the scale of the plot has changed)
                    self._iv_window.plot.redraw_cursors()
            self._msystem.trigger_measurements()

    def _read_options_from_json(self) -> Optional[Dict[str, Any]]:
        """
        :return: dictionary with options for parameters of the measurement system. If the measurers are standard type
        IVMeasurerIVM10, then the option parameters are not returned.
        """

        for measurer in self.get_measurers():
            if isinstance(measurer, (IVMeasurerASA, IVMeasurerVirtualASA)):
                dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                file_name = os.path.join(dir_name, "resources", "eplab_asa_options.json")
                return ut.read_json(file_name)

        return None

    def _remove_ref_curve(self) -> None:
        self._reference_curve = None

    def _report_measurers_disconnected(self) -> None:
        """
        Method sends a signal that the measurers have been disconnected by user.
        """

        self.measurers_connected.emit(False)

    def _reset_board(self) -> None:
        """
        Method sets the measurement plan to the default empty board with 1 pin.
        """

        self._measurement_plan = MeasurementPlan(
            Board(elements=[Element(pins=[Pin(0, 0, measurements=[])])]), measurer=self._msystem.measurers[0],
            multiplexer=(None if not self._msystem.multiplexers else self._msystem.multiplexers[0]))
        self._check_plan_compatibility(self._measurement_plan, True)
        self._measurement_plan_path.path = None

    def _save_changes_in_measurement_plan(self, additional_info: str = None) -> bool:
        """
        :param additional_info: additional text to the question.
        :return: True if the user has chosen to either save the changes or ignore them. If False, then the user has not
        selected anything.
        """

        result = 0
        if self._measurement_plan and self._last_saved_measurement_plan_data != self._measurement_plan.to_json():
            if self._measurement_plan_path.path:
                main_text = qApp.translate("t", "Сохранить изменения в '{}'?").format(self._measurement_plan_path.path)
            else:
                main_text = qApp.translate("t", "Сохранить изменения в файл?")
            text = f"{additional_info} {main_text}" if additional_info else main_text
            result = ut.show_message(qApp.translate("t", "Внимание"), text, icon=QMessageBox.Information,
                                     yes_button=True, no_button=True, cancel_button=True)
            if result == 0:
                # You need to save the changes to an existing file
                if self.save_board() is None:
                    result = 2
        return result in (0, 1)

    def _save_last_signatures(self, curves: Dict[str, Optional[IVCurve]]) -> None:
        """
        :param curves: dictionary with new signatures.
        """

        curves_dict = {"current": "_current_curve",
                       "reference": "_reference_curve",
                       "test": "_test_curve"}
        for curve_name, attr_name in curves_dict.items():
            if curve_name in curves:
                setattr(self, attr_name, curves[curve_name])

        if self._work_mode is WorkMode.COMPARE:
            compare_curve = curves.get("compare", None)
            if len(self._msystem.measurers) == 1:
                self._reference_curve = compare_curve
                self._test_curve = None
            else:
                self._test_curve = compare_curve

    def _save_measurement_in_compare_mode(self) -> None:
        """
        Method saves the signature in comparison mode. This functionality was added in ticket #93000.
        """

        if self._msystem and len(self._msystem.measurers) > 0:
            curve = self._msystem.measurers[0].get_last_cached_iv_curve()
            settings = self._msystem.get_settings()
            self._compare_measurement = Measurement(settings=settings, ivc=curve)

    def _set_hotkeys_for_moving_through_pins(self) -> None:
        """
        Method sets hotkeys UP and DOWN for moving to the previous and next pins.
        """

        self._shortcut_down: QShortcut = QShortcut(QKeySequence(Qt.Key_Down), self)
        self._shortcut_down.setContext(Qt.ApplicationShortcut)
        self._shortcut_down.activated.connect(lambda: self._go_to_left_or_right_pin_for_hotkeys(False))
        self._shortcut_up: QShortcut = QShortcut(QKeySequence(Qt.Key_Up), self)
        self._shortcut_up.setContext(Qt.ApplicationShortcut)
        self._shortcut_up.activated.connect(lambda: self._go_to_left_or_right_pin_for_hotkeys(True))

    def _set_init_position(self) -> None:
        """
        Method moves the window to the desired position and sets the initial dimensions.
        """

        if system().lower() == "windows":
            self.setMinimumWidth(self.MIN_WIDTH_IN_WINDOWS)
            width = self.CRITICAL_WIDTH_FOR_WINDOWS_RU
        else:
            self.setMinimumWidth(self.MIN_WIDTH_IN_LINUX)
            width = self.CRITICAL_WIDTH_FOR_LINUX_RU
        height = self.INIT_HEIGHT

        geometry = qApp.instance().desktop().availableGeometry()
        available_height = geometry.height() - self.style().pixelMetric(QStyle.PM_TitleBarHeight)
        available_width = geometry.width()

        height = min(height, available_height)
        width = min(width, available_width)
        pos_x = geometry.x() + (available_width - width) / 2
        pos_y = geometry.y() + (available_height - height) / 2
        self.move(pos_x, pos_y)
        self.resize(width, height)

    def _set_msystem_settings(self, settings: MeasurementSettings) -> None:
        """
        :param settings: measurement settings to set.
        """

        self._msystem.set_settings(settings)
        # Skip next measurement because it still has old settings
        self._skip_curve = True
        # When new curve will be received plot parameters will be adjusted
        self._settings_update_next_cycle = settings

    def _set_options_to_ui(self, options: Dict[EyePointProduct.Parameter, str]) -> None:
        """
        :param options: options that should be checked.
        """

        for parameter, value in options.items():
            self._parameters_widgets[parameter].set_checked_option(value)

    def _set_plot_parameters_to_low_settings_panel(self, settings: MeasurementSettings) -> None:
        """
        :param settings: new measurement settings that need to be shown on the bottom panel on the main window.
        """

        sensitivity_widget = self._parameters_widgets[EyePointProduct.Parameter.sensitive]
        sensitivity = sensitivity_widget.get_checked_option_label()
        voltage_per_division, current_per_division = self._iv_window.plot.get_minor_axis_step()
        param_dict = {"current_per_div": current_per_division,
                      "frequency": settings.probe_signal_frequency,
                      "max_voltage": settings.max_voltage,
                      "score": self._score_wrapper.get_friendly_score(),
                      "sensitivity": sensitivity,
                      "voltage_per_div": voltage_per_division}
        legend_dict = self._get_curves_for_legend()
        self.low_settings_panel.set_all_parameters(**param_dict, **legend_dict)

    def _set_widgets_to_init_state(self) -> None:
        self._board_window.update_board()
        self._create_measurer_setting_actions()
        self._disable_optimal_parameter_searcher()

        with self._device_errors_handler:
            for measurer in self._msystem.measurers:
                measurer.open_device()
            for multiplexer in self._msystem.multiplexers:
                multiplexer.open_device()

        self._settings_update_next_cycle = None
        self._skip_curve = False
        self._hide_current_curve = False
        self._hide_reference_curve = False
        self._compare_measurement = None
        self._current_curve = None
        self._reference_curve = None
        self._test_curve = None

        for action in (self.freeze_curve_a_action, self.freeze_curve_b_action, self.hide_curve_a_action,
                       self.hide_curve_b_action):
            action.setChecked(False)

        self._iv_window.plot.set_state_adding_cursor(False)
        self._iv_window.plot.set_state_removing_cursor(False)

        # Set ui settings state to current device
        with self._device_errors_handler:
            settings = self._auto_settings.get_measurement_settings(self._product)
            if settings is not None:
                self._msystem.set_settings(settings)
            settings = self._msystem.get_settings()
            self._adjust_plot_params(settings)
            self._create_scroll_areas_for_parameters(self._product.get_available_options(settings))
            options = self._product.settings_to_options(settings)
            self._set_options_to_ui(options)

        self._mux_and_plan_window.update_info()
        self._comment_widget.update_info()
        self._add_callbacks_to_measurement_plan()
        self._switch_work_mode(WorkMode.COMPARE)
        self._init_tolerance()
        with self._device_errors_handler:
            self._msystem.trigger_measurements()

    def _show_pin_shift_warning(self, main_text: str, text: str) -> int:
        """
        Method displays a message stating that adding a new point or deleting an old point will cause the point
        numbering to shift. It is also suggested to update the setting that is responsible for displaying this warning
        in the future.
        :param main_text: main text;
        :param text: warning message.
        :return: code of the button that the user clicked in the message box.
        """

        main_text = f'<font color="#003399" size="+1">{main_text}</font>'
        result, not_show_again = ut.show_message_with_option(qApp.translate("t", "Внимание"), main_text,
                                                             qApp.translate("t", "Не показывать снова"), text,
                                                             cancel_button=True)
        if not_show_again:
            self._auto_settings.save_pin_shift_warning_info(False)
        return result

    @pyqtSlot(WorkMode)
    def _switch_work_mode(self, mode: WorkMode) -> None:
        """
        :param mode: work mode to set.
        """

        self._change_work_mode(mode)

        self.update_current_pin()
        self.work_mode_changed.emit(mode)
        if mode in (WorkMode.TEST, WorkMode.WRITE) and self._measurement_plan.multiplexer:
            self.open_mux_window()
        self._change_menu_items_for_current_pin_change()

    def _update_mux_actions(self) -> None:
        """
        Method updates the state of menu actions responsible for working with the multiplexer.
        """

        enable = bool(self._measurement_plan and self._measurement_plan.multiplexer is not None)
        self.open_mux_window_action.setEnabled(enable)
        if not enable:
            self._mux_and_plan_window.close()

        enable = bool(enable and self.work_mode is not WorkMode.COMPARE)
        self.start_or_stop_entire_plan_measurement_action.setEnabled(enable)

    def _update_scroll_areas_for_parameters(self, available: Dict[EyePointProduct.Parameter,
                                                                  List[MeasurementParameterOption]]) -> None:
        """
        Method updates the scroll areas for different parameters of the measuring system.
        :param available: dictionary with available options for parameters.
        """

        for parameter, scroll_area in self._parameters_widgets.items():
            scroll_area.update_options(available[parameter])

    def _update_signatures(self, curves: Dict[str, Optional[IVCurve]], settings: Optional[MeasurementSettings] = None
                           ) -> None:
        """
        Method updates signatures and calculates (if required) their difference.
        :param curves: dictionary with new signatures;
        :param settings: measurement settings.
        """

        self._save_last_signatures(curves)

        # Update plots
        for hide, plot, curve in zip((self._hide_reference_curve, self._hide_current_curve, False),
                                     (self.reference_curve_plot, self.current_curve_plot, self.test_curve_plot),
                                     (self._reference_curve, self._current_curve, self._test_curve)):
            if not hide:
                plot.set_curve(curve)
            else:
                plot.set_curve(None)

        # Update difference
        curve_1 = self._reference_curve
        if self._work_mode in (WorkMode.COMPARE, WorkMode.TEST):
            curve_2 = self._current_curve
        elif self._work_mode is WorkMode.READ_PLAN:
            curve_2 = self._test_curve
        else:
            curve_2 = None
        if None not in (curve_1, curve_2, settings):
            difference = self._calculate_difference(curve_1, curve_2, settings)
            self._score_wrapper.set_difference(difference)
            self._player.update_difference(difference)
        else:
            self._score_wrapper.set_dummy_difference()

        if settings is not None:
            self._set_plot_parameters_to_low_settings_panel(settings)

    def _update_signatures_and_settings_in_plan_reading_mode(self, ref_curve: Optional[Measurement],
                                                             test_curve: Optional[Measurement],
                                                             settings: Optional[MeasurementSettings]) -> None:
        """
        :param ref_curve: reference measurement;
        :param test_curve: test measurement;
        :param settings: measurement settings.
        """

        with self._device_errors_handler:
            if settings:
                available = {
                    EyePointProduct.Parameter.frequency: [
                        MeasurementParameterOption(name=f"{settings.probe_signal_frequency}",
                                                   value=settings.probe_signal_frequency,
                                                   label_ru=f"{round(settings.probe_signal_frequency, 2)} Гц",
                                                   label_en=f"{round(settings.probe_signal_frequency, 2)} Hz")],
                    EyePointProduct.Parameter.sensitive: [
                        MeasurementParameterOption(name=f"{settings.internal_resistance}",
                                                   value=settings.internal_resistance,
                                                   label_ru=f"{round(settings.internal_resistance, 2)} Ом",
                                                   label_en=f"{round(settings.internal_resistance, 2)} Ohm")],
                    EyePointProduct.Parameter.voltage: [
                        MeasurementParameterOption(name=f"{settings.max_voltage}",
                                                   value=settings.max_voltage,
                                                   label_ru=f"{round(settings.max_voltage, 2)} В",
                                                   label_en=f"{round(settings.max_voltage, 2)} V")]
                }
                self._update_scroll_areas_for_parameters(available)
                options = {
                    EyePointProduct.Parameter.frequency: f"{settings.probe_signal_frequency}",
                    EyePointProduct.Parameter.sensitive: f"{settings.internal_resistance}",
                    EyePointProduct.Parameter.voltage: f"{settings.max_voltage}"
                }
                self._set_options_to_ui(options)
                self._adjust_plot_params(settings)

                curves = {"reference": None if not ref_curve else ref_curve.ivc,
                          "test": None if not test_curve else test_curve.ivc}
                self._update_signatures(curves, settings)
            else:
                for plot in (self.reference_curve_plot, self.current_curve_plot, self.test_curve_plot):
                    plot.set_curve(None)
                pin_index = self.pin_index_widget.text()
                self._clear_widgets()
                self.pin_index_widget.setText(pin_index)

    def _update_signatures_and_settings_in_test_and_write_mode(self, ref_curve: Optional[Measurement],
                                                               test_curve: Optional[Measurement],
                                                               settings: Optional[MeasurementSettings]) -> None:
        """
        :param ref_curve: reference measurement;
        :param test_curve: test measurement;
        :param settings: measurement settings.
        """

        with self._device_errors_handler:
            if settings:
                self._reference_curve = None if not ref_curve else ref_curve.ivc
                self._test_curve = None if not test_curve else test_curve.ivc
                self._set_msystem_settings(settings)
                options = self._product.settings_to_options(settings)
                self._set_options_to_ui(options)
            else:
                self._reference_curve = None
                self._test_curve = None

    def _update_tolerance(self, tolerance: float) -> None:
        """
        Method updates tolerance value in _score_wrapper and _player.
        :param tolerance: new tolerance value.
        """

        self._score_wrapper.set_tolerance(tolerance)
        self._player.set_tolerance(tolerance)
        self._comment_widget.update_table_for_new_tolerance()

    @pyqtSlot(Settings)
    def apply_settings(self, new_settings: Settings) -> None:
        """
        Slot applies settings from settings window.
        :param new_settings: new settings.
        """

        self._switch_work_mode(new_settings.work_mode)
        measurement_settings = new_settings.get_measurement_settings()
        options = self._product.settings_to_options(measurement_settings)
        self._set_options_to_ui(options)
        self._set_msystem_settings(measurement_settings)
        self.hide_curve_a_action.setChecked(new_settings.hide_curve_a)
        self.hide_curve_b_action.setChecked(new_settings.hide_curve_b)
        self.sound_enabled_action.setChecked(new_settings.sound_enabled)
        self._auto_settings.auto_transition = new_settings.auto_transition
        self._auto_settings.max_optimal_voltage = new_settings.max_optimal_voltage
        self._auto_settings.pin_shift_warning_info = new_settings.pin_shift_warning_info
        self._update_tolerance(new_settings.tolerance)

    @pyqtSlot(str)
    def change_window_title(self, measurement_plan_name: str) -> None:
        """
        :param measurement_plan_name: new name for measurement plan.
        """

        if measurement_plan_name:
            self.setWindowTitle(f"{measurement_plan_name} - EPLab {Version.full}")
        else:
            self.setWindowTitle(f"EPLab {Version.full}")

    def check_good_difference(self, curve_1: IVCurve, curve_2: IVCurve, settings: MeasurementSettings) -> bool:
        """
        Method calculates the difference for the given signatures and compares the calculated value with the tolerance.
        :param curve_1: first signature;
        :param curve_2: second signature;
        :param settings: measurement settings.
        :return: True if difference is not greater than the tolerance, otherwise False.
        """

        difference = self._calculate_difference(curve_1, curve_2, settings)
        return check_difference_not_greater_tolerance(difference, self._score_wrapper.tolerance)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        :param event: close event.
        """

        if not self._save_changes_in_measurement_plan(qApp.translate("t", "План тестирования не был сохранен.")):
            event.ignore()
            return

        self._board_window.close()
        self._mux_and_plan_window.close()
        if self._report_generation_thread:
            self._report_generation_thread.stop_thread()
            self._report_generation_thread.wait()

    def connect_devices(self, uri_1: Optional[str] = None, uri_2: Optional[str] = None,
                        mux_uri: str = None, product_name: Optional[cw.ProductName] = None) -> None:
        """
        Method connects IV-measurers and a multiplexer with given URIs.
        :param uri_1: URI for the first IV-measurer;
        :param uri_2: URI for the second IV-measurer;
        :param mux_uri: URI for multiplexer;
        :param product_name: name of product to work with application.
        """

        self._connection_checker.stop_check()
        measurement_system, product_name = self._connection_checker.connect_devices_by_user(uri_1, uri_2, mux_uri,
                                                                                            product_name)
        if measurement_system:
            self._connect_devices(measurement_system, product_name)
        else:
            self._disconnect_devices()
            self._delete_measurement_plan()

    @pyqtSlot()
    def connect_or_disconnect(self) -> None:
        """
        Slot displays a dialog box for selecting devices to connect or disconnect.
        """

        cw.show_connection_window(self, self._product_name)

    @pyqtSlot()
    def create_new_board(self) -> None:
        """
        Slot processes the signal that a new file with the board needs to be created. If a file with a board is already
        open, then before creating a new file, you will be asked to save the changes to the open file.
        """

        if not self._save_changes_in_measurement_plan():
            return

        self._reset_board()
        self._board_window.update_board()
        self.update_current_pin()
        self._mux_and_plan_window.update_info()
        self._comment_widget.update_info()
        self._add_callbacks_to_measurement_plan()
        self._change_menu_items_for_current_pin_change()
        self._change_work_mode_for_new_measurement_plan()

    @pyqtSlot()
    def create_new_pin(self, point: Optional[QPointF] = None, pin_centering: bool = True) -> bool:
        """
        :param point: coordinates of the pin to be created;
        :param pin_centering: if True, then the selected pin will be centered on the board window.
        :return: if True, then a new pin was created, otherwise the pin was not created.
        """

        if self._auto_settings.pin_shift_warning_info and self.measurement_plan.check_pin_indices_change():
            pin_index = self.measurement_plan.get_current_index() + 2
            main_text = qApp.translate("t", "Добавление точки приведет к сдвигу нумерации.")
            text = qApp.translate("t", "Добавленная точка будет иметь номер {0}. Номера имеющихся точек, начиная с {0},"
                                       " будут увеличены на 1.").format(pin_index)
            if self._show_pin_shift_warning(main_text, text) != 0:
                return False

        x, y = (point.x(), point.y()) if point else self.get_default_pin_coordinates()
        pin = Pin(x, y, measurements=[])
        self.measurement_plan.append_pin(pin)
        index = self.measurement_plan.get_current_index()
        self._board_window.add_pin_to_board_image(pin.x, pin.y, index)
        self._comment_widget.add_comment(index, pin)

        # It is important to initialize pin with real measurement. Otherwise, user can create several empty points and
        # they will not be unique. This will cause some errors during ufiv validation.
        self.update_current_pin(pin_centering)
        return True

    @pyqtSlot()
    def create_report(self, auto_detection_report_path: bool = False) -> None:
        """
        Slot starts report generation.
        :param auto_detection_report_path: if true, then it is needed to try to determine the path to save the
        generated report automatically. Otherwise, it is needed to ask the user where to save the report.
        In task #92258, the algorithm for determining the directory in which to save the generated report during
        automatic testing with a multiplexer has been changed. If the path to the uzf-file with the measurement plan is
        known, then the report should be saved nearby. Otherwise, it is needed to ask the user for the path.
        """

        if auto_detection_report_path and self._measurement_plan_path.path and \
                os.path.exists(self._measurement_plan_path.path):
            dir_path = os.path.dirname(self._measurement_plan_path.path)
            is_user_defined_path = False
        else:
            dir_path = QFileDialog.getExistingDirectory(
                self, qApp.translate("t", "Выберите папку, в которую будет сохранен отчет"), self.dir_chosen_by_user)
            is_user_defined_path = True

        if dir_path:
            show_report_generation_window(self, self._report_generation_thread, self.measurement_plan, dir_path,
                                          self.tolerance, self.work_mode)
            if is_user_defined_path:
                self.dir_chosen_by_user = dir_path

    def disconnect_measurers(self) -> None:
        """
        Method disconnects the measurers from the application. Before disconnecting, the method checks that all changes
        to the measurement plan have been saved.
        """

        if not self._save_changes_in_measurement_plan(qApp.translate("t", "План тестирования не был сохранен.")):
            return

        self._disconnect_devices()
        self._delete_measurement_plan()
        self._report_measurers_disconnected()

    @pyqtSlot(bool)
    def enable_sound(self, state: bool) -> None:
        """
        :param state: if True then sound will be enabled.
        """

        self._player.set_mute(not state)

    def enable_widgets(self, enabled: bool) -> None:
        """
        :param enabled: if True widgets will be set to enabled state.
        """

        widgets = (self.new_file_action, self.save_file_action, self.save_as_file_action,
                   self.save_screen_action, self.open_window_board_action, self.open_mux_window_action,
                   self.freeze_curve_a_action, self.freeze_curve_b_action, self.hide_curve_a_action,
                   self.hide_curve_b_action, self.search_optimal_action, self.comparing_mode_action,
                   self.writing_mode_action, self.testing_mode_action, self.settings_mode_action,
                   self.next_point_action, self.previous_point_action, self.new_point_action, self.remove_point_action,
                   self.save_point_action, self.add_board_image_action, self.create_report_action,
                   self.pin_index_widget, self.start_or_stop_entire_plan_measurement_action, self.comment_dock,
                   self.score_dock, self.freq_dock, self.current_dock, self.voltage_dock, self.measurers_menu)
        for widget in widgets:
            widget.setEnabled(enabled)
        if enabled and len(self._msystem.measurers) < 2:
            self.freeze_curve_b_action.setEnabled(False)
            self.hide_curve_b_action.setEnabled(False)

    def event(self, event: QEvent) -> bool:
        """
        Method handles events with the main window. When focus is on the main window, method takes measurement using
        the Enter and Return keys.
        :param event: event that occurred in the main window.
        :return: True if the event was recognized and processed.
        """

        if isinstance(event, QMouseEvent):
            self.setFocus()

        return super().event(event)

    @pyqtSlot(int, bool)
    def freeze_curve(self, measurer_id: int, state: bool) -> None:
        """
        :param measurer_id: index of the measurer;
        :param state: if True, then the signature of the given measurer will be frozen, otherwise it will be unfrozen.
        """

        if 0 <= measurer_id < len(self._msystem.measurers):
            if state:
                self._msystem.measurers[measurer_id].freeze()
            else:
                self._msystem.measurers[measurer_id].unfreeze()
                self._skip_curve = True

    def get_default_pin_coordinates(self) -> Tuple[float, float]:
        """
        :return: default pin coordinates.
        """

        if self._measurement_plan.image:
            # Place at the center of current viewpoint by default
            x, y = self._board_window.get_default_pin_xy()
        else:
            x, y = 0, 0
        return x, y

    def get_measurers(self) -> List[IVMeasurerBase]:
        """
        :return: list of measurers.
        """

        return self._msystem.measurers if self._msystem else []

    def get_multiplexer_uri(self) -> Optional[str]:
        """
        :return: multiplexer URI.
        """

        if self._msystem and self._msystem.multiplexers:
            return getattr(self._msystem.multiplexers[0], "_url")
        return None

    def get_settings(self) -> Settings:
        """
        :return: current applied settings in different objects.
        """

        settings = Settings()
        settings.set_measurement_settings(self._msystem.get_settings())
        if self.testing_mode_action.isChecked():
            settings.work_mode = WorkMode.TEST
        elif self.writing_mode_action.isChecked():
            settings.work_mode = WorkMode.WRITE
        else:
            settings.work_mode = WorkMode.COMPARE
        settings.auto_transition = self._auto_settings.auto_transition
        settings.hide_curve_a = bool(self.hide_curve_a_action.isChecked())
        settings.hide_curve_b = bool(self.hide_curve_b_action.isChecked())
        settings.max_optimal_voltage = self._auto_settings.max_optimal_voltage
        settings.pin_shift_warning_info = self._auto_settings.pin_shift_warning_info
        settings.sound_enabled = bool(self.sound_enabled_action.isChecked())
        settings.tolerance = self.tolerance
        return settings

    @pyqtSlot(bool, bool)
    def go_to_left_or_right_pin(self, to_prev: bool, cyclic: bool = True) -> None:
        """
        Slot moves to the next or previous pin in the measurement plan.
        :param to_prev: if True, then there will be a transition to the previous pin in the measurement plan,
        otherwise - to the next pin;
        :param cyclic: if True, then the transition will occur even if you need to move from the last pin to the first
        or vice versa.
        """

        if not cyclic and not self._check_transition_without_break(to_prev):
            return

        try:
            if to_prev:
                self._measurement_plan.go_prev_pin()
            else:
                self._measurement_plan.go_next_pin()
        except BadMultiplexerOutputError:
            if not self._mux_and_plan_window.measurement_plan_runner.is_running:
                ut.show_message(qApp.translate("t", "Ошибка"),
                                qApp.translate("t", "Подключенный мультиплексор имеет другую конфигурацию, выход "
                                                    "точки не был установлен."))
        except Exception as exc:
            logger.error("Error when going to the previous or next pin (%s)", exc)
            self._device_errors_handler.all_ok = False

        self.update_current_pin()
        self._open_board_window_if_needed()

    @pyqtSlot()
    def go_to_pin_selected_in_widget(self, user_pin_index: int = None, pin_centered: bool = True) -> None:
        """
        Slot sets given pin as current.
        :param user_pin_index: user index of a pin to be set as current (start at 1);
        :param pin_centered: if True, then the selected pin will be centered on the board window.
        """

        if user_pin_index is not None:
            self.pin_index_widget.setText(str(user_pin_index))

        pin_index = self.pin_index_widget.get_index()
        if pin_index is None:
            return

        try:
            with self._device_errors_handler:
                self._measurement_plan.go_pin(pin_index)
        except BadMultiplexerOutputError:
            if not self._mux_and_plan_window.measurement_plan_runner.is_running:
                ut.show_message(qApp.translate("t", "Ошибка"),
                                qApp.translate("t", "Подключенный мультиплексор имеет другую конфигурацию, выход точки "
                                                    "не был установлен."))
        except ValueError:
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Точка с таким номером не найдена на данной плате."))
            return

        self.update_current_pin(pin_centered)
        self._open_board_window_if_needed()

    @pyqtSlot(int, bool)
    def go_to_selected_pin(self, pin_index: int, pin_centered: bool = True) -> None:
        """
        Slot sets given pin as current.
        :param pin_index: index of a pin to be set as current (starts at 0);
        :param pin_centered: if True, then the selected pin will be centered on the board window.
        """

        self.go_to_pin_selected_in_widget(pin_index + 1, pin_centered)

    def handle_changing_pin_in_mux(self, index: int) -> None:
        """
        :param index: pin index that became active through the multiplexer widget.
        """

        self.measurement_plan._current_pin_index = index
        self._mux_and_plan_window.measurement_plan_widget.select_row()
        self._comment_widget.select_row()

    @pyqtSlot(bool)
    def handle_connection(self, connected: bool) -> None:
        """
        :param connected: if True, then the devices are connected, otherwise they are disconnected.
        """

        if connected and self._msystem:
            measurer_1_port = ut.get_device_port(self._msystem.measurers, 0)
            measurer_2_port = ut.get_device_port(self._msystem.measurers, 1)
            mux_port = ut.get_device_port(self._msystem.multiplexers, 0)
            product = self._product_name.name
        else:
            measurer_1_port = None
            measurer_2_port = None
            mux_port = None
            product = None
        self._auto_settings.save_connection_params(measurer_1_port, measurer_2_port, mux_port, product)

        if connected:
            self._mux_and_plan_window.set_connection_mode()
            self._connection_checker.stop_check()

    @pyqtSlot(ConnectionData)
    def handle_connection_signal_from_checker(self, connection_data: ConnectionData) -> None:
        """
        :param connection_data: an object with a created measurement system and product name.
        """

        measurement_system, product_name = connection_data
        if measurement_system:
            self._connect_devices(measurement_system, product_name)
        else:
            self._disconnect_devices()
            self._delete_measurement_plan()

    @pyqtSlot(bool)
    def handle_measurement_plan_change(self, there_are_measured_pins: bool) -> None:
        """
        Slot processes the signal after checking the measurement plan for pins with the measured reference signatures.
        If there are no such pins in the measurement plan, then switching to TEST work mode is prohibited.
        See ticket #89690.
        :param there_are_measured_pins: True, if the measurement plan contains a pin with a measured reference
        signature.
        """

        if self.comparing_mode_action.isEnabled():
            self.testing_mode_action.setEnabled(bool(self._msystem and there_are_measured_pins))

    @pyqtSlot(bool)
    def handle_pedal_signal(self, pressed: bool) -> None:
        """
        Slot processes pedal presses. The pedal freezes/unfreezes the measures in comparison mode and causes a
        transition to the next pin in the measurement plan in other modes.
        :param pressed: if True, then the pedal is pressed, otherwise it is released.
        """

        if self.work_mode == WorkMode.COMPARE:
            self._handle_freezing_curves_with_pedal(pressed)
        elif pressed and self.work_mode in (WorkMode.TEST, WorkMode.WRITE) and self.save_point_action.isEnabled():
            self.save_pin_and_go_to_next()

    @pyqtSlot(float)
    def handle_scale_change(self, *args) -> None:
        """
        Slot processes the signal that the screen scale has been changed.
        """

        ut.show_message(qApp.translate("t", "Информация"),
                        qApp.translate("t", "Изменен масштаб экрана. Закройте приложение и откройте снова."),
                        icon=QMessageBox.Information)

    @pyqtSlot(bool)
    def hide_curve(self, state: bool) -> None:
        """
        :param state: if True, then the curve will be hidden, otherwise shown.
        """

        if self.sender() is self.hide_curve_a_action:
            self._hide_current_curve = state
        elif self.sender() is self.hide_curve_b_action:
            self._hide_reference_curve = state

    @pyqtSlot()
    def load_board(self, filename: Optional[str] = None) -> None:
        """
        Slot loads board from a file.
        :param filename: path to the file with the measurement plan that needs to be opened.
        """

        if not self._save_changes_in_measurement_plan():
            return

        board, filename = self._read_measurement_plan(filename)
        if not filename:
            return

        if board:
            if not self._msystem:
                self._create_scroll_areas_for_parameters({EyePointProduct.Parameter.frequency: [],
                                                          EyePointProduct.Parameter.sensitive: [],
                                                          EyePointProduct.Parameter.voltage: []})
                self._iv_window.plot.clear_center_text()
                measurer = None
                multiplexer = None
            else:
                measurer = self._msystem.measurers[0]
                multiplexer = self._msystem.multiplexers[0] if self._msystem.multiplexers else None
            measurement_plan = MeasurementPlan(board, measurer, multiplexer)
            self._check_plan_compatibility(measurement_plan, True, filename)

        if self._measurement_plan:
            # New workspace will be created here
            self._board_window.update_board()
            self._open_board_window_if_needed()
            if self._msystem:
                self._mux_and_plan_window.update_info()
            else:
                self._change_work_mode(WorkMode.READ_PLAN)
            self._comment_widget.update_info()
            self._add_callbacks_to_measurement_plan()
            self._change_menu_items_for_current_pin_change()

            self.update_current_pin()
            self._change_work_mode_for_new_measurement_plan()

    @pyqtSlot()
    def load_board_image(self) -> None:
        """
        Slot loads image for the board from a file.
        """

        filename = QFileDialog.getOpenFileName(self, qApp.translate("t", "Открыть изображение платы"),
                                               filter="Image Files (*.png *.jpg *.bmp)",
                                               directory=self._dir_chosen_by_user)[0]
        if filename:
            epfilemanager.add_image_to_ufiv(filename, self._measurement_plan)
            self._board_window.update_board()
            self.update_current_pin()
            self._open_board_window_if_needed()
            self.dir_chosen_by_user = filename

    @pyqtSlot()
    def open_board_image(self) -> None:
        """
        Slot opens window with image of the board.
        """

        if not self._measurement_plan.image:
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Для данной платы изображение не задано."))
        else:
            self._open_board_window_if_needed()

    @pyqtSlot()
    def open_mux_window(self) -> None:
        """
        Slot shows the window with measurement plan and multiplexer pinout.
        """

        if not self._mux_and_plan_window.isVisible():
            self._mux_and_plan_window.show()
        else:
            self._mux_and_plan_window.activateWindow()

    @pyqtSlot()
    def remove_pin(self) -> None:
        if self._auto_settings.pin_shift_warning_info and self.measurement_plan.check_pin_indices_change():
            pin_index = self.measurement_plan.get_current_index() + 2
            main_text = qApp.translate("t", "Удаление точки приведет к сдвигу нумерации.")
            text = qApp.translate("t", "Номера имеющихся точек, начиная с {}, будут уменьшены на 1.").format(pin_index)
            if self._show_pin_shift_warning(main_text, text) != 0:
                return

        index = self._measurement_plan.get_current_index()
        self._measurement_plan.remove_current_pin()
        if index is None:
            return

        self._board_window.remove_pin_from_board_image(index)
        self._comment_widget.remove_comment(index)
        self._measured_pins_checker.remove_pin(index)
        self.update_current_pin()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Method handles resizing of the main window.
        :param event: resizing event.
        """

        # Determine the critical width of the window for given language and OS
        lang = qApp.instance().property("language")
        if system().lower() == "windows":
            size = self.CRITICAL_WIDTH_FOR_WINDOWS_EN if lang is Language.EN else self.CRITICAL_WIDTH_FOR_WINDOWS_RU
        else:
            size = self.CRITICAL_WIDTH_FOR_LINUX_EN if lang is Language.EN else self.CRITICAL_WIDTH_FOR_LINUX_RU
        # Change style of toolbars
        for tool_bar in (self.toolbar_write, self.toolbar_mode, self.toolbar_auto_search):
            if self.width() < size:
                style = Qt.ToolButtonIconOnly
            else:
                style = Qt.ToolButtonTextBesideIcon
            tool_bar.setToolButtonStyle(style)

        super().resizeEvent(event)

    @pyqtSlot()
    def save_board(self) -> Optional[bool]:
        """
        Slot saves measurement plan to a file.
        :return: True if measurement plan was saved otherwise False.
        """

        if self._measured_pins_checker.check_measurement_plan_for_empty_pins():
            return None

        if not self._measurement_plan_path.path or not os.path.exists(self._measurement_plan_path.path):
            return self.save_board_as()

        self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
        self._measurement_plan_path.path = epfilemanager.save_board_to_ufiv(self._measurement_plan_path.path,
                                                                            self._measurement_plan)
        return True

    @pyqtSlot()
    def save_board_as(self) -> Optional[bool]:
        """
        Slot saves measurement plan to a new file.
        :return: True if measurement plan was saved otherwise False.
        """

        if self._measured_pins_checker.check_measurement_plan_for_empty_pins():
            return None

        default_path = os.path.join(self.dir_chosen_by_user, "board.uzf")
        filename = QFileDialog.getSaveFileName(self, qApp.translate("MainWindow", "Сохранить план тестирования"),
                                               filter="UFIV Archived File (*.uzf)", directory=default_path)[0]
        if filename:
            self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
            self._measurement_plan_path.path = epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            self.dir_chosen_by_user = filename
            return True
        return False

    @pyqtSlot()
    def save_image(self) -> None:
        """
        Slot saves screenshot of the main window.
        """

        filename = "eplab_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        default_name = os.path.join(self.dir_chosen_by_user, filename)
        if system().lower() == "windows":
            filename = QFileDialog.getSaveFileName(self, qApp.translate("MainWindow", "Сохранить скриншот"),
                                                   filter="Image (*.png)", directory=default_name)[0]
        else:
            filename = QFileDialog.getSaveFileName(self, qApp.translate("MainWindow", "Сохранить скриншот"),
                                                   filter="Image (*.png)", directory=default_name,
                                                   options=QFileDialog.DontUseNativeDialog)[0]
        if filename:
            if not filename.endswith(".png"):
                filename += ".png"
            image = self.grab(self.rect())
            image.save(filename)
            self.dir_chosen_by_user = filename

    @pyqtSlot()
    def save_pin(self, pin_centering: bool = True) -> None:
        """
        Slot saves signature to current pin.
        :param pin_centering: if True, then the created pin will be centered on the board window.
        """

        with self._device_errors_handler:
            if self._work_mode == WorkMode.COMPARE:
                self._save_measurement_in_compare_mode()
            elif self._work_mode == WorkMode.TEST:
                self.measurement_plan.save_last_measurement_as_test()
            elif self._work_mode == WorkMode.WRITE:
                self.measurement_plan.save_last_measurement_as_reference(True)

        if self._work_mode in (WorkMode.TEST, WorkMode.WRITE):
            index = self.measurement_plan.get_current_index()
            self.update_current_pin(pin_centering)
            self._comment_widget.save_comment(index)
            self._comment_widget.update_table_for_new_tolerance(index)
            if self.measurement_plan and self.measurement_plan.multiplexer:
                self._mux_and_plan_window.measurement_plan_widget.save_measurement(index)

    @pyqtSlot()
    def save_pin_and_go_to_next(self) -> None:
        """
        Slot saves the measurement to the current pin and moves to the next pin after 300 ms, if available in the
        measurement plan.
        """

        self.save_pin()
        if self.work_mode in (WorkMode.TEST, WorkMode.WRITE):
            self._timer_to_go_to_next_pin.start()

    @pyqtSlot()
    def search_optimal(self) -> None:
        """
        Slot runs an algorithm to find optimal measurement settings.
        """

        with self._device_errors_handler:
            max_voltage = self._auto_settings.max_optimal_voltage
            searcher = Searcher(self._msystem.measurers[0], self._product.get_parameters(), max_voltage, True)
            optimal_settings = searcher.search_optimal_settings()
            self._set_msystem_settings(optimal_settings)
            options = self._product.settings_to_options(optimal_settings)
            self._set_options_to_ui(options)

    @pyqtSlot()
    def select_language(self) -> None:
        """
        Slot shows a dialog window to select language.
        """

        language = show_language_selection_window()
        current_language = get_language()
        if language is not None and language != current_language:
            self._auto_settings.save_language(language)
            text_ru = "Настройки языка сохранены. Чтобы изменения вступили в силу, перезапустите программу."
            text_en = "The language settings have been saved. Restart the program for the changes to take effect."
            if current_language is Language.RU:
                text = text_ru + "<br>" + text_en
            else:
                text = text_en + "<br>" + text_ru
            ut.show_message(qApp.translate("t", "Внимание"), text, icon=QMessageBox.Information)

    @pyqtSlot()
    def select_option(self) -> None:
        """
        Slot handles selection of a new option for parameter of the measuring system.
        """

        self.setFocus()
        settings = self._msystem.get_settings()
        old_settings = copy.deepcopy(settings)
        options = self._get_options_from_ui()
        settings = self._product.options_to_settings(options, settings)
        self._update_scroll_areas_for_parameters(self._product.get_available_options(settings))
        options = self._product.settings_to_options(settings)
        self._set_options_to_ui(options)
        try:
            self._set_msystem_settings(settings)
            self._auto_settings.save_measurement_settings(self._product.settings_to_options(settings))
        except ValueError as exc:
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Ошибка при установке настроек устройства."), detailed_text=str(exc))
            self._update_scroll_areas_for_parameters(self._product.get_available_options(old_settings))
            self._set_msystem_settings(old_settings)
            old_options = self._product.settings_to_options(old_settings)
            self._set_options_to_ui(old_options)

    @pyqtSlot(str)
    def set_dir_chosen_by_user(self, dir_path: str) -> None:
        """
        :param dir_path: path chosen by the user when working with the application.
        """

        self.dir_chosen_by_user = dir_path

    def set_enabled_save_point_action_at_test_mode(self) -> None:
        """
        In TEST work mode you can make measurements only at pins where there are reference IV-curves. See ticket #89690.
        """

        if self._work_mode == WorkMode.TEST and not self._mux_and_plan_window.measurement_plan_runner.is_running:
            self.save_point_action.setEnabled(not self._measured_pins_checker.check_empty_current_pin())

    def set_measurement_settings_and_update_ui(self, settings: MeasurementSettings) -> None:
        """
        :param settings: new measurement settings.
        """

        self._set_msystem_settings(settings)
        options = self._product.settings_to_options(settings)
        self._set_options_to_ui(options)

    @pyqtSlot(IVMeasurerBase, str, bool)
    def show_device_settings(self, selected_measurer: IVMeasurerBase, device_name: str, _: bool) -> None:
        """
        Slot shows a dialog window to select device settings.
        :param selected_measurer: measurer for which device settings should be displayed;
        :param device_name: name of the measurer;
        :param _: not used.
        """

        for measurer in self._msystem.measurers:
            if measurer == selected_measurer:
                show_measurer_settings_window(self, measurer, device_name)
                return

    @pyqtSlot()
    def show_settings_window(self) -> None:
        """
        Slot shows settings window.
        """

        settings_window = SettingsWindow(self, self.get_settings(), self.dir_chosen_by_user)
        settings_window.apply_settings_signal.connect(self.apply_settings)
        settings_window.exec()
        self._auto_settings.write()
        self.dir_chosen_by_user = settings_window.settings_directory
        self._check_break_signatures_for_auto_transition()
        # Break signatures are only saved when debugging the application
        # self._break_signature_saver.save_break_signatures_if_necessary()

    def update_current_pin(self, pin_centering: bool = True) -> None:
        """
        Call this method when current pin index changed.
        :param pin_centering: if True, then the selected pin will be centered on the board window.
        """

        index = self._measurement_plan.get_current_index()
        self.pin_index_widget.set_index(index)
        self._board_window.select_pin_on_scene(index, pin_centering)

        pin = self._measurement_plan.get_current_pin()
        ref_curve, test_curve, settings = pin.get_reference_and_test_measurements() if pin else (None, None, None)
        if self._work_mode in (WorkMode.TEST, WorkMode.WRITE):
            self._update_signatures_and_settings_in_test_and_write_mode(ref_curve, test_curve, settings)
        elif self._work_mode == WorkMode.READ_PLAN:
            self._update_signatures_and_settings_in_plan_reading_mode(ref_curve, test_curve, settings)

        self._mux_and_plan_window.select_current_pin()
        self._comment_widget.select_row()
