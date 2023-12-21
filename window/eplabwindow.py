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
from typing import Any, Dict, List, Optional, Tuple, Union
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QCoreApplication as qApp, QEvent, QObject, QPoint, Qt, QTimer,
                          QTranslator)
from PyQt5.QtGui import QCloseEvent, QColor, QFocusEvent, QIcon, QKeyEvent, QKeySequence, QMouseEvent, QResizeEvent
from PyQt5.QtWidgets import QAction, QFileDialog, QHBoxLayout, QMainWindow, QMenu, QMessageBox, QVBoxLayout, QWidget
from PyQt5.uic import loadUi
import epcore.filemanager as epfilemanager
from epcore.analogmultiplexer import BadMultiplexerOutputError
from epcore.elements import Board, Element, IVCurve, MeasurementSettings, Pin
from epcore.ivmeasurer import IVMeasurerASA, IVMeasurerBase, IVMeasurerIVM10, IVMeasurerVirtual, IVMeasurerVirtualASA
from epcore.measurementmanager import IVCComparator, MeasurementPlan, MeasurementSystem, Searcher
from epcore.product import EyePointProduct, MeasurementParameterOption
from ivviewer import Viewer as IVViewer
from ivviewer.ivcviewer import PlotCurve
import connection_window as cw
from dialogs import (ReportGenerationThread, show_keymap_info, show_language_selection_window,
                     show_measurer_settings_window, show_product_info, show_report_generation_window)
from multiplexer import MuxAndPlanWindow
from window import utils as ut
from window.actionwithdisabledhotkeys import ActionWithDisabledHotkeys
from window.boardwidget import BoardWidget
from window.common import DeviceErrorsHandler, WorkMode
from window.curvestates import CurveStates
from window.dirwatcher import DirWatcher
from window.language import Language, Translator
from window.measuredpinschecker import MeasuredPinsChecker
from window.measurementplanpath import MeasurementPlanPath
from window.parameterwidget import ParameterWidget
from window.pedalhandler import add_pedal_handler
from window.pinindexwidget import PinIndexWidget
from window.scaler import update_scale_of_class
from window.scorewrapper import ScoreWrapper
from window.soundplayer import SoundPlayer
from settings import AutoSettings, LowSettingsPanel, Settings, SettingsWindow
from version import Version


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
    CRITICAL_WIDTH_FOR_LINUX_EN: int = 1420
    CRITICAL_WIDTH_FOR_LINUX_RU: int = 1620
    CRITICAL_WIDTH_FOR_WINDOWS_EN: int = 1180
    CRITICAL_WIDTH_FOR_WINDOWS_RU: int = 1350
    DEFAULT_COMPARATOR_MIN_CURRENT: float = 0.002
    DEFAULT_COMPARATOR_MIN_VOLTAGE: float = 0.6
    DEFAULT_PATH: str = os.path.join(ut.get_dir_name(), "EPLab-Files")
    DEFAULT_POS_X: int = 50
    DEFAULT_POS_Y: int = 50
    FILENAME_FOR_AUTO_SETTINGS: str = os.path.join(ut.get_dir_name(), "eplab_settings_for_auto_save_and_read.ini")
    MIN_WIDTH_IN_LINUX: int = 700
    MIN_WIDTH_IN_WINDOWS: int = 650
    measurers_connected: pyqtSignal = pyqtSignal(bool)
    measurers_disconnected: pyqtSignal = pyqtSignal()
    work_mode_changed: pyqtSignal = pyqtSignal(WorkMode)

    def __init__(self, product: EyePointProduct, port_1: Optional[str] = None, port_2: Optional[str] = None,
                 english: Optional[bool] = None, path: str = None) -> None:
        """
        :param product: product;
        :param port_1: port for the first measurer;
        :param port_2: port for the second measurer;
        :param english: if True then interface language will be English;
        :param path: path to the test plan to be opened.
        """

        super().__init__()
        self._auto_settings: AutoSettings = AutoSettings(path=EPLabWindow.FILENAME_FOR_AUTO_SETTINGS)
        self._comparator: IVCComparator = IVCComparator()
        self._device_errors_handler: DeviceErrorsHandler = DeviceErrorsHandler()
        self._dir_chosen_by_user: str = ut.get_dir_name()
        self._dir_watcher: DirWatcher = DirWatcher(ut.get_dir_name())
        self._hide_reference_curve: bool = False
        self._hide_current_curve: bool = False
        self._last_saved_measurement_plan_data: Dict[str, Any] = None
        self._measurement_plan: MeasurementPlan = None
        self._measured_pins_checker: MeasuredPinsChecker = MeasuredPinsChecker(self)
        self._measured_pins_checker.measured_pin_in_plan_signal.connect(self.handle_measurement_plan_change)
        self._measurement_plan_path: MeasurementPlanPath = MeasurementPlanPath(self)
        self._measurement_plan_path.name_changed.connect(self.change_window_title)
        self._msystem: MeasurementSystem = None
        self._product: EyePointProduct = product
        self._product_name: cw.ProductName = None
        self._report_generation_thread: ReportGenerationThread = ReportGenerationThread(self)
        self._report_generation_thread.start()
        self._skip_curve: bool = False  # set to True to skip next measured curves
        self._timer: QTimer = QTimer()
        self._timer.setInterval(10)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._handle_periodic_task)
        self._work_mode: WorkMode = None

        self._load_translation(english)
        self._init_ui()
        self._connect_scale_change_signal()

        if port_1 is None and port_2 is None:
            self.disconnect_measurers()
        else:
            self.connect_measurers(port_1, port_2)

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

        return self._dir_chosen_by_user

    @dir_chosen_by_user.setter
    def dir_chosen_by_user(self, path: str) -> None:
        """
        :param path: path chosen by the user when working with the application.
        """

        if os.path.exists(path):
            self._dir_chosen_by_user = os.path.dirname(path) if not os.path.isdir(path) else path

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
    def measurement_plan(self) -> MeasurementPlan:
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
        :return: tolerance value for comparing IV curves.
        """

        return self._score_wrapper.tolerance

    @property
    def work_mode(self) -> Optional[WorkMode]:
        """
        :return: current operating mode.
        """

        return self._work_mode

    def _adjust_plot_params(self, settings: MeasurementSettings) -> None:
        """
        :param settings: measurement settings for which plot parameters to adjust.
        """

        scale = ut.calculate_scales(settings)
        self._iv_window.plot.set_scale(*scale)
        self._iv_window.plot.set_min_borders(*scale)

    def _calculate_score(self, curve_1: IVCurve, curve_2: IVCurve, settings: MeasurementSettings) -> float:
        """
        :param curve_1: first IV-curve;
        :param curve_2: second IV-curve;
        :param settings: measurement settings.
        :return: score for given IV-curves and measurement settings.
        """

        # It is very important to set relevant noise levels
        self._comparator.set_min_ivc(*self._get_noise_amplitude(settings))
        return self._comparator.compare_ivc(curve_1, curve_2)

    def _change_work_mode(self, mode: WorkMode) -> None:
        """
        Method sets window settings for given work mode.
        :param mode: new work mode.
        """

        if mode == WorkMode.READ_PLAN:
            self.open_window_board_action.setEnabled(True)
        enable = bool(self._measurement_plan and self._measurement_plan.multiplexer is not None)
        self.open_mux_window_action.setEnabled(enable)
        self.comparing_mode_action.setChecked(mode is WorkMode.COMPARE)
        self.writing_mode_action.setChecked(mode is WorkMode.WRITE)
        self.testing_mode_action.setChecked(mode is WorkMode.TEST)
        self.next_point_action.setEnabled(mode is not WorkMode.COMPARE)
        self.previous_point_action.setEnabled(mode is not WorkMode.COMPARE)
        self.pin_index_widget.setEnabled(mode is not WorkMode.COMPARE)
        self.new_point_action.setEnabled(mode is WorkMode.WRITE)
        self.save_point_action.setEnabled(mode not in (WorkMode.COMPARE, WorkMode.READ_PLAN))
        self.add_board_image_action.setEnabled(mode is WorkMode.WRITE)
        self.create_report_action.setEnabled(mode not in (WorkMode.COMPARE, WorkMode.READ_PLAN))
        enable = bool(mode is not WorkMode.COMPARE and self._measurement_plan and
                      self._measurement_plan.multiplexer is not None)
        self.start_or_stop_entire_plan_measurement_action.setEnabled(enable)

        self._player.set_work_mode(mode)
        # Comment is only for test and write mode
        self.line_comment_pin.setEnabled(mode in (WorkMode.TEST, WorkMode.WRITE))
        self.save_comment_push_button.setEnabled(mode in (WorkMode.TEST, WorkMode.WRITE))
        self.search_optimal_action.setEnabled(mode in (WorkMode.COMPARE, WorkMode.WRITE))
        if mode is WorkMode.COMPARE and len(self._msystem.measurers) < 2:
            # Remove reference curve in case we have only one IVMeasurer in compare mode
            self._remove_ref_curve()
        # Drag allowed only in write mode
        self._board_window.allow_drag(mode is WorkMode.WRITE)
        # Disable settings in test mode
        for scroll_area in self._parameters_widgets.values():
            scroll_area.enable_buttons(mode in (WorkMode.COMPARE, WorkMode.WRITE))
        self._work_mode = mode

    def _change_work_mode_for_new_measurement_plan(self) -> None:
        """
        Method changes the work mode of the main window when a new measurement plan is initialized. If the new plan
        does not contain pins with measured reference IV-curves, and the current work mode is TEST, then you need to
        change the work mode to COMPARE (see ticket #89690).
        """

        if self._work_mode == WorkMode.TEST and not self._measured_pins_checker.is_measured_pin:
            self._change_work_mode(WorkMode.COMPARE)

    def _check_board_for_compatibility(self, board: Union[Board, MeasurementPlan], error_message: str
                                       ) -> Optional[Union[Board, MeasurementPlan]]:
        """
        :param board: board to check for compatibility with measurement system;
        :param error_message: message to display if the board is not compatible.
        :return: verified board or None if the board did not pass the test.
        """

        if self._msystem and not ut.check_compatibility(self._product, board):
            ut.show_message(qApp.translate("t", "Ошибка"), error_message)
            board = None
        return board

    def _clear_widgets(self) -> None:
        """
        Method clears widgets on the main window.
        """

        self._comparator.set_min_ivc(*self._get_noise_amplitude())

        for widget in (self.freq_dock_widget, self.current_dock_widget, self.voltage_dock_widget):
            layout = widget.layout()
            ut.clear_layout(layout)

        for action in (self.comparing_mode_action, self.writing_mode_action, self.testing_mode_action):
            action.setChecked(False)

        self.line_comment_pin.clear()
        self.low_settings_panel.clear_panel()
        self.measurers_menu.clear()
        self.pin_index_widget.clear()
        self._iv_window.plot.remove_all_cursors()
        self._mux_and_plan_window.close()
        self._score_wrapper.set_dummy_score()

        self._settings_update_next_cycle = None
        self._skip_curve = False
        self._work_mode = None
        self._hide_current_curve = False
        self._hide_reference_curve = False
        self._current_curve = None
        self._reference_curve = None
        self._test_curve = None

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
            self.measurers_menu.addAction(action)

    def _create_scroll_areas_for_parameters(self, available: Dict[EyePointProduct.Parameter,
                                                                  List[MeasurementParameterOption]]) -> None:
        """
        Method creates scroll areas for different parameters of the measuring system. Scroll areas have radio buttons
        to choose options of parameters.
        :param available: dictionary with available options for parameters.
        """

        self._parameters_widgets = {}
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

    def _disable_optimal_parameter_searcher(self) -> None:
        """
        Method disables searcher of the optimal parameters. Searcher can work only for IVMeasurerIVM10.
        """

        for measurer in self._msystem.measurers:
            if not isinstance(measurer, (IVMeasurerIVM10, IVMeasurerVirtual)):
                self.search_optimal_action.setEnabled(False)
                return

    def _get_curves_for_legend(self) -> Dict[str, bool]:
        """
        :return: a dictionary containing the curves displayed in the application window.
        """

        return {"current": bool(self.current_curve_plot.curve),
                "reference": bool(self.reference_curve_plot.curve),
                "test": bool(self.test_curve_plot.curve)}

    def _get_noise_amplitude(self, settings: Optional[MeasurementSettings] = None) -> Tuple[float, float]:
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

    def _handle_freezing_curves_with_pedal(self, pressed: bool) -> None:
        """
        Method freezes the measurers curves using a pedal. If at least one curve is not frozen, then all curves are
        frozen by pedal. If all curves are frozen, unfreeze all curves.
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

    def _handle_key_press_event(self, event: QKeyEvent) -> bool:
        """
        Method handles key press events on the main window. The Enter and Return keys saves the measurement at the pin.
        :param event: key press event.
        :return: handling result.
        """

        key = event.key()
        key_type = event.type()
        if self.save_point_action.isEnabled() and ((key == Qt.Key_Enter and key_type == QEvent.ShortcutOverride) or
                                                   (key == Qt.Key_Return and key_type == QEvent.KeyPress)):
            self.save_pin()
            return True

        return super().event(event)

    @pyqtSlot()
    def _handle_periodic_task(self) -> None:
        if self._device_errors_handler.all_ok:
            with self._device_errors_handler:
                self._read_curves_periodic_task()
            self._mux_and_plan_window.measurement_plan_runner.save_pin()
        else:
            self._reconnect_periodic_task()
        # Add this task to event loop
        self._timer.start()

    def _init_tolerance(self) -> None:
        """
        Method initializes the initial value of the tolerance.
        """

        self._update_tolerance(self._score_wrapper.tolerance)

    def _init_ui(self) -> None:
        loadUi(os.path.join(os.path.dirname(ut.DIR_MEDIA), "gui", "mainwindow.ui"), self)
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
        self.setWindowTitle(self.windowTitle() + " " + Version.full)
        if system().lower() == "windows":
            self.setMinimumWidth(EPLabWindow.MIN_WIDTH_IN_WINDOWS)
        else:
            self.setMinimumWidth(EPLabWindow.MIN_WIDTH_IN_LINUX)
        self.move(EPLabWindow.DEFAULT_POS_X, EPLabWindow.DEFAULT_POS_Y)

        self._board_window: BoardWidget = BoardWidget(self)
        self._parameters_widgets: Dict[EyePointProduct.Parameter, ParameterWidget] = {}
        self._player: SoundPlayer = SoundPlayer()
        self._player.set_mute(not self.sound_enabled_action.isChecked())
        self._score_wrapper: ScoreWrapper = ScoreWrapper(self.score_label)

        self.low_settings_panel: LowSettingsPanel = LowSettingsPanel()
        self.main_widget: QWidget = QWidget(self)
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self._iv_window: IVViewer = IVViewer(grid_color=QColor(255, 255, 255), back_color=QColor(0, 0, 0),
                                             solid_axis_enabled=False, axis_label_enabled=False)
        self._iv_window.layout().setContentsMargins(0, 0, 0, 0)
        self._iv_window.plot.set_path_to_directory(self._dir_watcher.screenshot)
        self._iv_window.plot.localize_widget(add_cursor=qApp.translate("t", "Добавить метку"),
                                             export_ivc=qApp.translate("t", "Экспортировать сигнатуры в файл"),
                                             remove_all_cursors=qApp.translate("t", "Удалить все метки"),
                                             remove_cursor=qApp.translate("t", "Удалить метку"),
                                             save_screenshot=qApp.translate("t", "Сохранить изображение"))
        self.current_curve_plot: PlotCurve = self._iv_window.plot.add_curve()
        self.current_curve_plot.set_curve_params(EPLabWindow.COLOR_FOR_CURRENT)
        self.reference_curve_plot: PlotCurve = self._iv_window.plot.add_curve()
        self.reference_curve_plot.set_curve_params(EPLabWindow.COLOR_FOR_REFERENCE)
        self.test_curve_plot: PlotCurve = self._iv_window.plot.add_curve()
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
        self.pin_index_widget.installEventFilter(self)
        self.toolbar_test.insertWidget(self.next_point_action, self.pin_index_widget)
        self.pin_index_widget.returnPressed.connect(self.go_to_pin_selected_in_widget)
        self.next_point_action.triggered.connect(lambda: self.go_to_left_or_right_pin(False))
        self.new_point_action.triggered.connect(self.create_new_pin)
        self._replace_save_point_action()
        self.add_board_image_action.triggered.connect(self.load_board_image)
        self.create_report_action.triggered.connect(self.create_report)
        self.about_action.triggered.connect(show_product_info)
        self.action_keymap.triggered.connect(show_keymap_info)
        self.save_comment_push_button.clicked.connect(self.save_comment)
        self.line_comment_pin.installEventFilter(self)
        self.line_comment_pin.returnPressed.connect(self.save_comment)
        self.sound_enabled_action.toggled.connect(self.enable_sound)
        self.freeze_curve_a_action.toggled.connect(partial(self.freeze_curve, 0))
        self.freeze_curve_b_action.toggled.connect(partial(self.freeze_curve, 1))
        self._curves_states: CurveStates = CurveStates(self.freeze_curve_a_action, self.freeze_curve_b_action)
        self.hide_curve_a_action.toggled.connect(self.hide_curve)
        self.hide_curve_b_action.toggled.connect(self.hide_curve)
        self.add_cursor_action.toggled.connect(self.set_add_cursor_state)
        self.remove_cursor_action.setCheckable(False)
        self.remove_cursor_action.triggered.connect(self.show_context_menu_for_cursor_deletion)
        self.save_screen_action.triggered.connect(self.save_image)
        self.select_language_action.triggered.connect(self.select_language)

        self.comparing_mode_action.triggered.connect(lambda: self._switch_work_mode(WorkMode.COMPARE))
        self.writing_mode_action.triggered.connect(lambda: self._switch_work_mode(WorkMode.WRITE))
        self.testing_mode_action.triggered.connect(lambda: self._switch_work_mode(WorkMode.TEST))
        self.settings_mode_action.triggered.connect(self.show_settings_window)

        # Update plot settings at next measurement cycle (place settings here or None)
        self._settings_update_next_cycle: MeasurementSettings = None
        self._current_curve: IVCurve = None
        self._reference_curve: IVCurve = None
        self._test_curve: IVCurve = None
        self._mux_and_plan_window: MuxAndPlanWindow = MuxAndPlanWindow(self)
        self.work_mode_changed.connect(self._mux_and_plan_window.change_work_mode)
        self.start_or_stop_entire_plan_measurement_action.triggered.connect(
            self._mux_and_plan_window.start_or_stop_plan_measurement)

    def _load_translation(self, english: Optional[bool] = None) -> None:
        """
        :param english: if True then the interface language will be English.
        """

        if english:
            language = Language.EN
        else:
            language = self._auto_settings.get_language()
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
                                                   directory=self._dir_watcher.reference,
                                                   filter="Board Files (*.json *.uzf)")[0]
        board = None
        if filename:
            try:
                board = epfilemanager.load_board_from_ufiv(filename, auto_convert_p10=True)
            except Exception as exc:
                ut.show_message(qApp.translate("t", "Ошибка"), qApp.translate("t", "Формат файла не подходит."),
                                str(exc))
        return board, filename

    def _read_curves_periodic_task(self) -> None:
        if self._msystem.measurements_are_ready():
            if self._skip_curve:
                self._skip_curve = False
            else:
                # Get curves from devices
                curves = dict()
                curves["current"] = self._msystem.measurers[0].get_last_cached_iv_curve()
                if self._work_mode is WorkMode.COMPARE and len(self._msystem.measurers) > 1:
                    # Display two current curves
                    curves["reference"] = self._msystem.measurers[1].get_last_cached_iv_curve()
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

    def _reconnect_periodic_task(self) -> None:
        """
        Method try to reconnect measurer devices to app.
        """

        self.measurers_disconnected.emit()
        self._mux_and_plan_window.set_disconnection_mode()

        # Draw empty curves
        self.enable_widgets(False)
        self._current_curve = None
        if self._work_mode is WorkMode.COMPARE:
            self._reference_curve = None
        self._update_curves()
        for plot in (self.current_curve_plot, self.reference_curve_plot, self.test_curve_plot):
            plot.set_curve(None)
        # Draw text
        self._iv_window.plot.set_center_text(qApp.translate("t", "НЕТ ПОДКЛЮЧЕНИЯ"))

        if self._msystem.reconnect():
            # Reconnection success!
            self.enable_widgets(True)
            self._mux_and_plan_window.set_connection_mode()
            self._device_errors_handler.reset_error()
            self._iv_window.plot.clear_center_text()
            with self._device_errors_handler:
                # Update current settings to reconnected device
                options = self._get_options_from_ui()
                settings = self._product.options_to_settings(options, MeasurementSettings(-1, -1, -1, -1))
                self._set_msystem_settings(settings)
                self._msystem.trigger_measurements()

    def _remove_ref_curve(self) -> None:
        self._reference_curve = None

    def _replace_save_point_action(self) -> None:
        """
        Method replaces the menu item that is responsible for saving the measurement at a point.
        """

        action_icon = self.save_point_action.icon()
        action_name = self.save_point_action.text()
        self.test_plan_menu_action.removeAction(self.save_point_action)
        self.toolbar_write.removeAction(self.save_point_action)
        self.save_point_action: ActionWithDisabledHotkeys = ActionWithDisabledHotkeys(action_icon, action_name)
        self.save_point_action.setShortcut(QKeySequence("Enter"))
        self.save_point_action.triggered.connect(self.save_pin)
        self.test_plan_menu_action.insertAction(self.add_board_image_action, self.save_point_action)
        self.toolbar_write.addAction(self.save_point_action)

    def _reset_board(self) -> None:
        """
        Method sets the measurement plan to the default empty board with 1 pin.
        """

        self._measurement_plan = MeasurementPlan(
            Board(elements=[Element(pins=[Pin(0, 0, measurements=[])])]), measurer=self._msystem.measurers[0],
            multiplexer=(None if not self._msystem.multiplexers else self._msystem.multiplexers[0]))
        self._measured_pins_checker.set_new_plan()
        self._last_saved_measurement_plan_data = self._measurement_plan.to_json()

    def _save_changes_in_measurement_plan(self, additional_info: str = None) -> bool:
        """
        :param additional_info: additional text to the question.
        :return:
        """

        result = 0
        if self._measurement_plan and self._last_saved_measurement_plan_data != self._measurement_plan.to_json():
            main_text = qApp.translate("t", "Сохранить изменения в файл?")
            text = f"{additional_info} {main_text}" if additional_info else main_text
            result = ut.show_message(qApp.translate("t", "Внимание"), text, icon=QMessageBox.Information,
                                     yes_button=True, no_button=True, cancel_button=True)
            if result == 0:
                # You need to save the changes to an existing file
                if self.save_board() is None:
                    result = 2
        return result in (0, 1)

    def _save_last_curves(self, curves: Dict[str, Optional[IVCurve]] = None) -> None:
        """
        :param curves: dictionary with new curves.
        """

        curves_dict = {"current": "_current_curve",
                       "reference": "_reference_curve",
                       "test": "_test_curve"}
        if isinstance(curves, dict):
            for curve_name, attr_name in curves_dict.items():
                if curve_name in curves:
                    setattr(self, attr_name, curves[curve_name])

    def _set_msystem_settings(self, settings: MeasurementSettings) -> None:
        """
        :param settings: measurement settings to set.
        """

        self._msystem.set_settings(settings)
        # Skip next measurement because it still have old settings
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
        self._current_curve = None
        self._reference_curve = None
        self._test_curve = None

        for action in (self.freeze_curve_a_action, self.freeze_curve_b_action, self.hide_curve_a_action,
                       self.hide_curve_b_action):
            action.setChecked(False)

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
        self._switch_work_mode(WorkMode.COMPARE)
        self._init_tolerance()
        with self._device_errors_handler:
            self._msystem.trigger_measurements()

    def _skip_empty_pins(self) -> None:
        """
        In TEST work mode you can make measurements only at pins where there are reference IV-curves. See ticket #89690.
        """

        if self._work_mode == WorkMode.TEST:
            self.save_point_action.setEnabled(not self._measured_pins_checker.check_empty_current_pin())

    @pyqtSlot(WorkMode)
    def _switch_work_mode(self, mode: WorkMode) -> None:
        """
        :param mode: work mode to set.
        """

        self._change_work_mode(mode)
        self._skip_empty_pins()

        self.update_current_pin()
        self.work_mode_changed.emit(mode)
        if mode in (WorkMode.TEST, WorkMode.WRITE) and self._measurement_plan.multiplexer:
            self.open_mux_window()

    def _update_current_pin_in_read_plan_mode(self) -> None:

        def round_value(value: float) -> float:
            """
            Function rounds a real number to two decimal places.
            :param value: value to round.
            :return: rounded value.
            """

            return round(value, 2)

        current_pin = self._measurement_plan.get_current_pin()
        self.line_comment_pin.setText(current_pin.comment or "")
        ref_for_plan, test_for_plan, settings = current_pin.get_reference_and_test_measurements()
        with self._device_errors_handler:
            if settings:
                available = {
                    EyePointProduct.Parameter.frequency: [
                        MeasurementParameterOption(name=f"{settings.probe_signal_frequency}",
                                                   value=settings.probe_signal_frequency,
                                                   label_ru=f"{round_value(settings.probe_signal_frequency)} Гц",
                                                   label_en=f"{round_value(settings.probe_signal_frequency)} Hz")],
                    EyePointProduct.Parameter.sensitive: [
                        MeasurementParameterOption(name=f"{settings.internal_resistance}",
                                                   value=settings.internal_resistance,
                                                   label_ru=f"{round_value(settings.internal_resistance)} Ом",
                                                   label_en=f"{round_value(settings.internal_resistance)} Ohm")],
                    EyePointProduct.Parameter.voltage: [
                        MeasurementParameterOption(name=f"{settings.max_voltage}",
                                                   value=settings.max_voltage,
                                                   label_ru=f"{round_value(settings.max_voltage)} В",
                                                   label_en=f"{round_value(settings.max_voltage)} V")]
                }
                self._update_scroll_areas_for_parameters(available)
                options = {
                    EyePointProduct.Parameter.frequency: f"{settings.probe_signal_frequency}",
                    EyePointProduct.Parameter.sensitive: f"{settings.internal_resistance}",
                    EyePointProduct.Parameter.voltage: f"{settings.max_voltage}"
                }
                self._set_options_to_ui(options)
                self._adjust_plot_params(settings)

                curves = {"reference": None if not ref_for_plan else ref_for_plan.ivc,
                          "test": None if not test_for_plan else test_for_plan.ivc}
                self._update_curves(curves, settings)
            else:
                for plot in (self.reference_curve_plot, self.current_curve_plot, self.test_curve_plot):
                    plot.set_curve(None)
                pin_index = self.pin_index_widget.text()
                self._clear_widgets()
                self.pin_index_widget.setText(pin_index)

    def _update_current_pin_in_test_and_write_mode(self) -> None:
        current_pin = self._measurement_plan.get_current_pin()
        self.line_comment_pin.setText(current_pin.comment or "")
        ref_for_plan, test_for_plan, settings = current_pin.get_reference_and_test_measurements()
        with self._device_errors_handler:
            if settings:
                curves = {"reference": None if not ref_for_plan else ref_for_plan.ivc,
                          "test": None if not test_for_plan else test_for_plan.ivc}
                self._set_msystem_settings(settings)
                options = self._product.settings_to_options(settings)
                self._set_options_to_ui(options)
            else:
                curves = {"reference": None,
                          "test": None}
            self._update_curves(curves, self._msystem.measurers[0].get_settings())

    def _update_curves(self, curves: Dict[str, Optional[IVCurve]] = None, settings: MeasurementSettings = None) -> None:
        """
        Method updates curves and calculates (if required) score.
        :param curves: dictionary with new curves;
        :param settings: measurement settings.
        """

        self._save_last_curves(curves)

        # Update plots
        for hide, plot, curve in zip((self._hide_reference_curve, self._hide_current_curve,
                                      self._work_mode == WorkMode.COMPARE),
                                     (self.reference_curve_plot, self.current_curve_plot, self.test_curve_plot),
                                     (self._reference_curve, self._current_curve, self._test_curve)):
            if not hide:
                plot.set_curve(curve)
            else:
                plot.set_curve(None)

        # Update score
        if self._reference_curve and self._current_curve and self._work_mode != WorkMode.WRITE:
            assert settings is not None
            score = self._calculate_score(self._reference_curve, self._current_curve, settings)
            self._score_wrapper.set_score(score)
            self._player.score_updated(score)
        else:
            self._score_wrapper.set_dummy_score()
        if settings is not None:
            self._set_plot_parameters_to_low_settings_panel(settings)

    def _update_scroll_areas_for_parameters(self, available: Dict[EyePointProduct.Parameter,
                                                                  List[MeasurementParameterOption]]) -> None:
        """
        Method updates the scroll areas for different parameters of the measuring system.
        :param available: dictionary with available options for parameters.
        """

        for parameter, scroll_area in self._parameters_widgets.items():
            scroll_area.update_options(available[parameter])

    def _update_tolerance(self, tolerance: float) -> None:
        """
        Method updates tolerance value in _score_wrapper and _player.
        :param tolerance: new tolerance value.
        """

        self._score_wrapper.set_tolerance(tolerance)
        self._player.set_tolerance(tolerance)

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

    def connect_measurers(self, port_1: Optional[str], port_2: Optional[str],
                          product_name: Optional[cw.ProductName] = None, mux_port: str = None) -> None:
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
            ut.show_message(qApp.translate("t", "Ошибка подключения"), text.format(", ".join(bad_com_ports)))

        self._msystem, bad_com_ports = ut.create_measurement_system(*good_com_ports)
        if bad_com_ports:
            if len(bad_com_ports) == 1:
                text = qApp.translate("t", "Не удалось подключиться к {0}. Убедитесь, что {0} - это устройство "
                                           "EyePoint, а не какое-то другое устройство.")
            else:
                text = qApp.translate("t", "Не удалось подключиться к {0}. Убедитесь, что {0} - это устройства "
                                           "EyePoint, а не какие-то другие устройства.")
            ut.show_message(qApp.translate("t", "Ошибка подключения"), text.format(", ".join(bad_com_ports)))

        if not self._msystem:
            self.disconnect_measurers()
            return

        self._clear_widgets()
        self._iv_window.plot.clear_center_text()
        options_data = self._read_options_from_json()
        self._product.change_options(options_data)
        if product_name is None:
            self._product_name = cw.ProductName.get_default_product_name_for_measurers(self._msystem.measurers)
        else:
            self._product_name = product_name
        self.enable_widgets(True)

        if self._measurement_plan:
            error_message = qApp.translate("t", "План тестирования {}не соответствует режиму работы EPLab и будет "
                                                "закрыт.")
            board_filename = self._measurement_plan_path.path
            error_message = error_message.format(f"'{board_filename}' " if board_filename else "")
            self._measurement_plan = self._check_board_for_compatibility(self._measurement_plan, error_message)
            self._measured_pins_checker.set_new_plan()

        if self._measurement_plan:
            self._measurement_plan.measurer = self._msystem.measurers[0]
            self._measurement_plan.multiplexer = self._msystem.multiplexers[0] if self._msystem.multiplexers else None
        else:
            self._reset_board()
            self._measurement_plan_path.path = None
        self._set_widgets_to_init_state()
        self.measurers_connected.emit(True)
        self._timer.start()

    @pyqtSlot()
    def connect_or_disconnect(self) -> None:
        """
        Slot shows dialog window to select measurers for connection.
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

        default_path = os.path.join(self._dir_watcher.reference, "board.uzf")
        filename = QFileDialog.getSaveFileName(self, qApp.translate("MainWindow", "Создать план тестирования"),
                                               filter="UFIV Archived File (*.uzf)", directory=default_path)[0]
        if filename:
            self._reset_board()
            self._measurement_plan_path.path = filename
            epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            self._board_window.update_board()
            self.update_current_pin()
            self._mux_and_plan_window.update_info()
            self._change_work_mode_for_new_measurement_plan()

    @pyqtSlot()
    def create_new_pin(self, multiplexer_output=None) -> None:
        """
        :param multiplexer_output: multiplexer output for new pin.
        """

        if self._measurement_plan.image:
            # Place at the center of current viewpoint by default
            point = self._board_window.get_default_pin_xy()
            pin = Pin(point.x(), point.y(), measurements=[], multiplexer_output=multiplexer_output)
        else:
            pin = Pin(0, 0, measurements=[], multiplexer_output=multiplexer_output)
        self._measurement_plan.append_pin(pin)
        self._board_window.add_pin(pin.x, pin.y, self._measurement_plan.get_current_index())
        self.line_comment_pin.setText(pin.comment or "")

        # It is important to initialize pin with real measurement. Otherwise user can create several empty points and
        # they will not be unique. This will cause some errors during ufiv validation.
        self.update_current_pin()

    @pyqtSlot()
    def create_report(self, default_path: bool = False) -> None:
        """
        Slot shows a dialog window to create report for the board.
        :param default_path: if True, then the report should be created in the default directory.
        """

        dir_path = self._dir_watcher.reports
        if not default_path:
            dir_path = QFileDialog.getExistingDirectory(self, qApp.translate("t", "Выбрать папку"), dir_path)
        if dir_path:
            show_report_generation_window(self, self._report_generation_thread, self.measurement_plan, dir_path,
                                          self.tolerance, self.work_mode)

    def disconnect_measurers(self) -> None:
        self._timer.stop()
        if self.start_or_stop_entire_plan_measurement_action.isChecked():
            self.start_or_stop_entire_plan_measurement_action.setChecked(False)
        if self._msystem:
            for measurer in self._msystem.measurers:
                measurer.close_device()
            for multiplexer in self._msystem.multiplexers:
                multiplexer.close_device()
        self._last_saved_measurement_plan_data = None
        self._measurement_plan = None
        self._measured_pins_checker.set_new_plan()
        self._measurement_plan_path.path = None
        self._msystem = None
        self._iv_window.plot.set_center_text(qApp.translate("t", "НЕТ ПОДКЛЮЧЕНИЯ"))
        self.enable_widgets(False)
        self._clear_widgets()
        self._board_window.close()
        self._product_name = None
        self.measurers_connected.emit(False)

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
                   self.next_point_action, self.previous_point_action, self.new_point_action, self.save_point_action,
                   self.add_board_image_action, self.create_report_action, self.pin_index_widget,
                   self.start_or_stop_entire_plan_measurement_action, self.add_cursor_action, self.remove_cursor_action,
                   self.score_dock, self.freq_dock, self.current_dock, self.voltage_dock, self.comment_dock,
                   self.measurers_menu)
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

        if self.measurement_plan and isinstance(event, QKeyEvent) and \
                not getattr(self.pin_index_widget, "is_focused", False) and \
                not getattr(self.line_comment_pin, "is_focused", False):
            key_event = QKeyEvent(event)
            if key_event.type() in (QEvent.KeyPress, QEvent.ShortcutOverride):
                return self._handle_key_press_event(key_event)

        if isinstance(event, QMouseEvent):
            self.setFocus()

        return super().event(event)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        Method handles events with line edit widgets with the point number and comment for the pin. When focus is on
        the line edit children, method performs standard actions for those widgets. Since Enter is the hotkey for
        saving a measurement to a pin, the method handles the Enter and Return keys presses in line edit widgets
        (when the focus is in these line edit widgets and the Enter or Return keys are pressed, the measurement was not
        saved).
        :param obj: object for which event occurred;
        :param event: event.
        :return: True if event should be filtered out, otherwise - False.
        """

        if obj in (self.pin_index_widget, self.line_comment_pin):
            if isinstance(event, QKeyEvent):
                key_event = QKeyEvent(event)
                key = key_event.key()
                if key in (Qt.Key_Enter, Qt.Key_Return):
                    event_type = key_event.type()
                    if (key == Qt.Key_Enter and event_type == QKeyEvent.ShortcutOverride) or \
                            (key == Qt.Key_Return and event_type == QKeyEvent.KeyPress):
                        obj.keyPressEvent(event)
                    return True
                return False

            if isinstance(event, QFocusEvent):
                filter_event = QFocusEvent(event)
                if filter_event.type() == QFocusEvent.FocusIn:
                    setattr(obj, "is_focused", True)
                elif filter_event.type() == QFocusEvent.FocusOut:
                    setattr(obj, "is_focused", False)

        return super().eventFilter(obj, event)

    @pyqtSlot(int, bool)
    def freeze_curve(self, measurer_id: int, state: bool) -> None:
        """
        :param measurer_id: index of the measurer;
        :param state: if True, then the curve of the given measurer will be frozen, otherwise it will be unfrozen.
        """

        if 0 <= measurer_id < len(self._msystem.measurers):
            if state:
                self._msystem.measurers[measurer_id].freeze()
            else:
                self._msystem.measurers[measurer_id].unfreeze()
                self._skip_curve = True

    def get_measurers(self) -> List[IVMeasurerBase]:
        """
        :return: list of measurers.
        """

        return self._msystem.measurers if self._msystem else []

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
        settings.tolerance = self.tolerance
        settings.hide_curve_a = bool(self.hide_curve_a_action.isChecked())
        settings.hide_curve_b = bool(self.hide_curve_b_action.isChecked())
        settings.sound_enabled = bool(self.sound_enabled_action.isChecked())
        return settings

    @pyqtSlot(bool)
    def go_to_left_or_right_pin(self, to_prev: bool) -> None:
        """
        Slot moves to the next or previous pin in measurement plan.
        :param to_prev: if True, then there will be a transition to the previous pin in measurement plan, otherwise -
        to the next pin.
        """

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
        except Exception:
            self._device_errors_handler.all_ok = False

        self._skip_empty_pins()
        self.update_current_pin()
        self._open_board_window_if_needed()

    @pyqtSlot()
    def go_to_pin_selected_in_widget(self, user_pin_index: int = None) -> None:
        """
        Slot sets given pin as current.
        :param user_pin_index: user index of a pin to be set as current (start at 1).
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
                                qApp.translate("t", "Подключенный мультиплексор имеет другую конфигурацию, выход "
                                                    "точки не был установлен."))
        except ValueError:
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Точка с таким номером не найдена на данной плате."))
            return

        self._skip_empty_pins()
        self.update_current_pin()
        self._open_board_window_if_needed()

    def go_to_selected_pin(self, pin_index: int = None) -> None:
        """
        Slot sets given pin as current.
        :param pin_index: index of a pin to be set as current (starts at 0).
        """

        self.go_to_pin_selected_in_widget(pin_index + 1)

    @pyqtSlot(bool)
    def handle_measurement_plan_change(self, there_are_measured_pins: bool) -> None:
        """
        Slot processes the signal after checking the measurement plan for pins with the measured reference IV-curves.
        If there are no such pins in the measurement plan, then switching to TEST work mode is prohibited.
        See ticket #89690.
        :param there_are_measured_pins: True, if the measurement plan contains a pin with a measured reference IV-curve.
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
            self.save_pin()

    @pyqtSlot(float)
    def handle_scale_change(self, new_scale: float) -> None:
        """
        Slot processes the signal that the screen scale has been changed.
        :param new_scale: new screen scale.
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
        if board:
            error_message = qApp.translate("t", "План тестирования {}нельзя загрузить, поскольку он не соответствует "
                                                "режиму работы EPLab.")
            error_message = error_message.format(f"'{filename}' " if filename else "")
            board = self._check_board_for_compatibility(board, error_message)

        if board:
            if not self._msystem:
                self._create_scroll_areas_for_parameters({EyePointProduct.Parameter.frequency: [],
                                                          EyePointProduct.Parameter.sensitive: [],
                                                          EyePointProduct.Parameter.voltage: []})
                self._change_work_mode(WorkMode.READ_PLAN)
                self._iv_window.plot.clear_center_text()
                measurer = None
                multiplexer = None
            else:
                measurer = self._msystem.measurers[0]
                multiplexer = self._msystem.multiplexers[0] if self._msystem.multiplexers else None
            self._measurement_plan = MeasurementPlan(board, measurer, multiplexer)
            self._measured_pins_checker.set_new_plan()
            self._measurement_plan_path.path = filename
            self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
            # New workspace will be created here
            self._board_window.update_board()
            self.update_current_pin()
            self._open_board_window_if_needed()
            if self._msystem:
                self._mux_and_plan_window.update_info()
            self._change_work_mode_for_new_measurement_plan()

    @pyqtSlot()
    def load_board_image(self) -> None:
        """
        Slot loads image for the board from a file.
        """

        filename = QFileDialog.getOpenFileName(self, qApp.translate("t", "Открыть изображение платы"),
                                               filter="Image Files (*.png *.jpg *.bmp)")[0]
        if filename:
            epfilemanager.add_image_to_ufiv(filename, self._measurement_plan)
            self._board_window.update_board()
            self.update_current_pin()
            self._open_board_window_if_needed()

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
    def remove_all_cursors(self) -> None:
        """
        Slot removes all cursors from the plot.
        """

        self._iv_window.plot.remove_all_cursors()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Method handles resizing of the main window.
        :param event: resizing event.
        """

        # Determine the critical width of the window for given language and OS
        lang = qApp.instance().property("language")
        if system().lower() == "windows":
            size = EPLabWindow.CRITICAL_WIDTH_FOR_WINDOWS_EN if lang is Language.EN else \
                EPLabWindow.CRITICAL_WIDTH_FOR_WINDOWS_RU
        else:
            size = EPLabWindow.CRITICAL_WIDTH_FOR_LINUX_EN if lang is Language.EN else \
                EPLabWindow.CRITICAL_WIDTH_FOR_LINUX_RU
        # Change style of toolbars
        tool_bars = self.toolbar_write, self.toolbar_mode, self.toolbar_auto_search
        for tool_bar in tool_bars:
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

        if not self._measurement_plan_path.path:
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

        default_path = os.path.join(self._dir_watcher.reference, "board.uzf")
        filename = QFileDialog.getSaveFileName(self, qApp.translate("MainWindow", "Сохранить план тестирования"),
                                               filter="UFIV Archived File (*.uzf)", directory=default_path)[0]
        if filename:
            self._last_saved_measurement_plan_data = self._measurement_plan.to_json()
            self._measurement_plan_path.path = epfilemanager.save_board_to_ufiv(filename, self._measurement_plan)
            return True
        return False

    @pyqtSlot()
    def save_comment(self) -> None:
        """
        Slot saves comment for pin.
        """

        pin_index = self._measurement_plan.get_current_index()
        self._measurement_plan.save_comment_to_pin_with_index(pin_index, self.line_comment_pin.text())

    @pyqtSlot()
    def save_image(self) -> None:
        """
        Slot saves screenshot of the main window.
        """

        filename = "eplab_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        default_name = os.path.join(self._dir_watcher.screenshot, filename)
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
        self.save_comment()
        self.update_current_pin()

    @pyqtSlot()
    def search_optimal(self) -> None:
        """
        Slot runs an algorithm to find optimal measurement settings.
        """

        with self._device_errors_handler:
            searcher = Searcher(self._msystem.measurers[0], self._product.get_parameters())
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
        if language is not None and language != qApp.instance().property("language"):
            self._auto_settings.save_language(Translator.get_language_name(language))
            text_ru = "Настройки языка сохранены. Чтобы изменения вступили в силу, перезапустите программу."
            text_en = "The language settings are saved. Restart the program for the changes to take effect."
            if qApp.instance().property("language") is Language.RU:
                text = text_ru + "<br>" + text_en
            else:
                text = text_en + "<br>" + text_ru
            ut.show_message(qApp.translate("t", "Внимание"), text, icon=QMessageBox.Information)

    @pyqtSlot()
    def select_option(self) -> None:
        """
        Slot handles selection of a new option for parameter of the measuring system.
        """

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
                            qApp.translate("t", "Ошибка при установке настроек устройства."), str(exc))
            self._update_scroll_areas_for_parameters(self._product.get_available_options(old_settings))
            self._set_msystem_settings(old_settings)
            old_options = self._product.settings_to_options(old_settings)
            self._set_options_to_ui(old_options)

    @pyqtSlot(bool)
    def set_add_cursor_state(self, state: bool) -> None:
        """
        :param state: if True, then cursors can be placed on the widget with curves.
        """

        if state:
            self.remove_cursor_action.setChecked(False)
        self._iv_window.plot.set_state_adding_cursor(state)

    @pyqtSlot()
    def set_remove_cursor_state(self) -> None:
        """
        Slot sets cursor deletion mode when one cursor at a time can be deleted.
        """

        self.remove_cursor_action.setCheckable(True)
        self.remove_cursor_action.setChecked(True)
        self.add_cursor_action.setChecked(False)
        self._iv_window.plot.set_state_removing_cursor(True)

    @pyqtSlot()
    def show_context_menu_for_cursor_deletion(self) -> None:
        """
        Slot shows context menu for choosing to delete cursors one at a time or all at once.
        """

        if self.remove_cursor_action.isCheckable():
            self.remove_cursor_action.setCheckable(False)
            self.remove_cursor_action.setChecked(False)
            self._iv_window.plot.set_state_removing_cursor(False)
            return

        widget = self.toolbar_compare.widgetForAction(self.remove_cursor_action)
        menu = QMenu(widget)
        icon = QIcon(os.path.join(ut.DIR_MEDIA, "delete_cursor.png"))
        action_remove_cursor = QAction(icon, qApp.translate("t", "Удалить метку"), menu)
        action_remove_cursor.triggered.connect(self.set_remove_cursor_state)
        menu.addAction(action_remove_cursor)
        icon = QIcon(os.path.join(ut.DIR_MEDIA, "delete_all.png"))
        action_remove_all_cursors = QAction(icon, qApp.translate("t", "Удалить все метки"), menu)
        action_remove_all_cursors.triggered.connect(self.remove_all_cursors)
        menu.addAction(action_remove_all_cursors)
        position = widget.geometry()
        menu.popup(self.toolbar_compare.mapToGlobal(QPoint(position.x(), position.y())))

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
        self.dir_chosen_by_user = settings_window.settings_directory

    def update_current_pin(self, pin_centering: bool = True) -> None:
        """
        Call this method when current pin index changed.
        :param pin_centering: if True, then the selected pin will be centered on the board window.
        """

        index = self._measurement_plan.get_current_index()
        self.pin_index_widget.set_index(index)
        self._board_window.select_pin_on_scene(index, pin_centering)
        if self._work_mode in (WorkMode.TEST, WorkMode.WRITE):
            self._update_current_pin_in_test_and_write_mode()
        elif self._work_mode == WorkMode.READ_PLAN:
            self._update_current_pin_in_read_plan_mode()

        if self._mux_and_plan_window:
            self._mux_and_plan_window.select_current_pin()
