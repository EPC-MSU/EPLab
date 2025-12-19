"""
File with class for dialog window with settings of measurer.
"""

import logging
from functools import partial
from inspect import getmembers, ismethod
from typing import Any, Callable, Dict, List, Optional
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt, QTimer
from PyQt5.QtWidgets import (QDialog, QGroupBox, QHBoxLayout, QLabel, QLayout, QLineEdit, QPushButton, QTextBrowser,
                             QVBoxLayout, QWidget)
from epcore.ivmeasurer.base import IVMeasurerBase
from window import utils as ut
from window.language import get_language, Language
from window.scaler import update_scale_of_class


logger = logging.getLogger("eplab")


def get_converter(data: Dict[str, Any]) -> Callable[[Any], Any]:
    """
    Function returns suitable converter function.
    :param data: dictionary with type name for converter.
    :return: converter.
    """

    value_type = data.get("value_type")
    if value_type == "int":
        return int

    if value_type == "float":
        return lambda s: float(s.replace(",", "."))

    return str


@update_scale_of_class
class MeasurerSettingsWindow(QDialog):
    """
    Class for dialog window with settings of measurer.
    """

    MAX_HEIGHT: int = 500
    MAX_WIDTH: int = 400
    MIN_WIDTH: int = 300
    TIME_TO_FIX_SIZE_MS: int = 50

    def __init__(self, parent=None, settings: Dict[str, Any] = None, measurer: IVMeasurerBase = None,
                 device_name: str = None) -> None:
        """
        :param parent: main window of application;
        :param settings: dictionary with all settings of measurer;
        :param measurer: specific measurer for which settings will be intended;
        :param device_name: name of measurer.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._measurer: IVMeasurerBase = measurer
        self._all_widgets: List[QWidget] = []
        self._lang: str = "ru" if get_language() == Language.RU else "en"
        self._parameters_data: Dict[str, Dict[str, Any]] = dict()
        self._init_ui(settings, device_name)
        QTimer.singleShot(self.TIME_TO_FIX_SIZE_MS, self._fix_size)

    @property
    def all_widgets(self) -> List[QWidget]:
        """
        :return: list of all widgets that need to be scaled.
        """

        return self._all_widgets

    def _create_button(self, data: Dict[str, Any]) -> Optional[QWidget]:
        """
        Method creates button that will call method of measurer for execution.
        :param data: information about created button.
        :return: created button.
        """

        button_name = data.get(f"label_{self._lang}")
        if not button_name:
            return None

        button = QPushButton(button_name)
        self._all_widgets.append(button)
        tool_tip = data.get(f"tooltip_{self._lang}")
        if tool_tip:
            button.setToolTip(tool_tip)

        for member_name, member in getmembers(self._measurer):
            if member_name == data.get("func", None) and ismethod(member):
                button.clicked.connect(partial(self._run_command, member, member_name, data))
                return button

        return None

    def _create_line_edit(self, data: Dict[str, Any], current_value: Any, is_child_widget: bool = False
                          ) -> Optional[QWidget]:
        """
        Method creates line edit to input value of parameter of measurer.
        :param data: information about the parameter for which the widget is created;
        :param current_value: current value of parameter for which line edit is created;
        :param is_child_widget: if True, the widget is a child of the group box widget.
        :return: created line edit.
        """

        label = data.get(f"label_{self._lang}")
        parameter = data.get("parameter")
        if not label or not parameter:
            return None

        line_edit = QLineEdit()
        if isinstance(data.get("multiplier"), (int, float)) and isinstance(current_value, (int, float)):
            current_value = current_value / data["multiplier"]
        line_edit.setText(str(current_value))

        label_widget = QLabel(label)
        h_layout = QHBoxLayout()
        h_layout.addWidget(label_widget)
        h_layout.addWidget(line_edit)
        self._all_widgets.extend([label_widget, line_edit])

        widget = QWidget()
        widget.setLayout(h_layout)
        data["widget"] = line_edit
        if not is_child_widget:
            self._parameters_data[parameter] = data

        if data.get(f"tooltip_{self._lang}"):
            widget.setToolTip(data.get(f"tooltip_{self._lang}"))
        return widget

    def _create_selectable_group_box(self, data: Dict[str, Any], checked: bool) -> Optional[QGroupBox]:
        """
        :param data: information about the parameter for which the widget is created;
        :param checked: if True, then group box checked.
        :return: created group box.
        """

        label = data.get(f"label_{self._lang}")
        value = data.get("value")
        if not label or not value:
            return None

        v_layout = QVBoxLayout()
        for child_parameter_data in data.get("child_parameters", []):
            child_parameter = child_parameter_data.get("parameter")
            if not child_parameter or child_parameter_data.get("type") != "line_edit":
                continue

            if checked:
                current_value = self._measurer.get_current_value_of_parameter(child_parameter)
            else:
                current_value = child_parameter_data.get("default_value")
            child_parameter_widget = self._create_line_edit(child_parameter_data, current_value, True)
            v_layout.addWidget(child_parameter_widget)

        group_box = QGroupBox(label)
        group_box.setCheckable(True)
        group_box.setChecked(checked)
        group_box.setLayout(v_layout)
        return group_box

    def _create_selectable_group_boxes(self, data: Dict[str, Any], current_value: Any) -> Optional[QWidget]:
        """
        :param data: information about the parameter for which the widget is created;
        :param current_value: current parameter value.
        :return: a widget with created linked group boxes that can be selected.
        """

        parameter = data.get("parameter")
        values = data.get("values", [])
        if not parameter or not values:
            return None

        v_layout = QVBoxLayout()
        group_boxes = []
        for item in values:
            group_box = self._create_selectable_group_box(item, current_value == item.get("value"))
            if not group_box:
                continue

            self._all_widgets.append(group_box)
            group_box.clicked.connect(partial(self._handle_selection_one_of_group_boxes, data, item))
            v_layout.addWidget(group_box)
            item["widget"] = group_box
            group_boxes.append(group_box)

        if not group_boxes:
            return None

        self._parameters_data[parameter] = data
        widget = QWidget()
        widget.setLayout(v_layout)
        return widget

    def _create_text_browser(self, data: Dict[str, Any]) -> Optional[QWidget]:
        """
        Method creates text browser widget with some info about measurer.
        :param data: information about the parameter for which the widget is created.
        :return: created text browser widget.
        """

        info = data.get(f"label_{self._lang}", "")
        if not info:
            return None

        text_browser = QTextBrowser()
        text_browser.setReadOnly(True)
        text_browser.setText(info)
        text_browser.adjustSize()
        self._all_widgets.append(text_browser)
        return text_browser

    @staticmethod
    def _create_title(device_name: Optional[str] = None) -> str:
        """
        Method creates title for dialog window.
        :param device_name: name of measurer.
        """

        title = qApp.translate("MainWindow", "Настройки")
        if device_name is None:
            device_name = qApp.translate("t", "Неизвестный измеритель")
        return "{}. {}".format(title, device_name)

    @pyqtSlot()
    def _fix_size(self) -> None:
        layout = self.layout()
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.adjustSize()
        if self.width() < self.MIN_WIDTH:
            self.setFixedWidth(self.MIN_WIDTH)

    def _handle_selection_one_of_group_boxes(self, data: Dict[str, Any], selected_data: Dict[str, Any]) -> None:
        """
        :param data: dictionary with data of all group boxes;
        :param selected_data: data of the selected group box.
        """

        for item in data.get("values", []):
            group_box = item.get("widget")
            if group_box:
                group_box.setChecked(item is selected_data)

    def _init_ui(self, settings: Optional[Dict[str, Any]] = None, device_name: Optional[str] = None):
        """
        Method initializes widgets in dialog window.
        :param settings: dictionary with all settings of measurer;
        :param device_name: name of measurer.
        """

        self.setWindowTitle(self._create_title(device_name))
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumSize(self.MAX_WIDTH, self.MAX_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        v_layout = QVBoxLayout()
        if isinstance(settings, dict) and settings.get("elements"):
            for element in settings.get("elements", []):
                if "parameter" in element:
                    current_value = self._measurer.get_current_value_of_parameter(element["parameter"])
                else:
                    current_value = None

                element_type = element.get("type")
                if element_type == "button":
                    widget = self._create_button(element)
                elif element_type == "line_edit":
                    widget = self._create_line_edit(element, current_value)
                elif element_type == "text_browser":
                    widget = self._create_text_browser(element)
                elif element_type == "selectable_group_boxes":
                    widget = self._create_selectable_group_boxes(element, current_value)
                else:
                    widget = None

                if widget is not None:
                    v_layout.addWidget(widget)

            self.button_ok: QPushButton = QPushButton("OK")
            self.button_ok.clicked.connect(self.set_parameters)
            self.button_cancel: QPushButton = QPushButton(qApp.translate("t", "Отмена"))
            self.button_cancel.clicked.connect(self.close)

            h_layout = QHBoxLayout()
            h_layout.addStretch(1)
            h_layout.addWidget(self.button_ok)
            h_layout.addWidget(self.button_cancel)
            v_layout.addStretch(1)
            v_layout.addLayout(h_layout)
        else:
            self.label: QLabel = QLabel(qApp.translate("dialogs", "Нет настроек"))
            v_layout.addWidget(self.label, alignment=Qt.AlignHCenter)
        self.setLayout(v_layout)

    def _run_command(self, command_to_run: Callable[[], Any], command_name: str, data: Dict[str, Any]) -> None:
        """
        Method runs special commands for IV-measurers connected to buttons.
        :param command_to_run: command to run;
        :param command_name: name of command to run;
        :param data: dictionary with data for the command to be executed for the IV-measurer.
        """

        friendly_name = data.get(f"label_{self._lang}")
        default_error_message = data.get(f"error_message_{self._lang}",
                                         qApp.translate("dialogs", 'Команда "{}" завершилась неудачно.').format(
                                             friendly_name))
        try:
            result = command_to_run()
            if "required_result" in data and result != data["required_result"]:
                for bad_results_info in data.get("bad_results", []):
                    if bad_results_info.get("value") == result:
                        text = bad_results_info.get(f"error_message_{self._lang}", default_error_message)
                        break
                else:
                    text = default_error_message
                ut.show_message(qApp.translate("t", "Ошибка"), text)
        except Exception:
            logger.error("Failed to execute command '%s' for measurer '%s'", command_name, self._measurer.name)
            text = qApp.translate("dialogs", 'Не удалось выполнить команду "{}".').format(friendly_name)
            ut.show_message(qApp.translate("t", "Ошибка"), text)

    def _set_parameter_from_line_edit(self, parameter_name: str, data: Dict[str, Any]) -> Optional[str]:
        """
        :param parameter_name: the name of the parameter for which you want to set the value in the measurer;
        :param data: dictionary with parameter data.
        :return: error setting parameter value.
        """

        value = None
        try:
            converter = get_converter(data)
            value = data["widget"].text()
            converted_value = converter(value)
        except ValueError:
            error = qApp.translate("dialogs", 'Неверное значение для "{}". Не удалось конвертировать "{}" в "{}".'
                                   ).format(data.get(f"label_{self._lang}"), value, data.get("value_type"))
            return error

        if isinstance(data.get("multiplier"), (int, float)) and isinstance(converted_value, (int, float)):
            converted_value *= data["multiplier"]

        if data.get("min") is not None and data["min"] > converted_value:
            converted_value = data["min"]

        if data.get("max") is not None and data["max"] < converted_value:
            converted_value = data["max"]

        self._measurer.set_value_to_parameter(parameter_name, converted_value)

        if isinstance(data.get("multiplier"), (int, float)) and isinstance(converted_value, (int, float)):
            converted_value = converted_value / data["multiplier"]

        data["widget"].setText(str(converted_value))
        return None

    def _set_parameters_from_selected_group_box(self, data: Dict[str, Any]) -> List[str]:
        """
        :param data: dictionary with parameter data.
        :return: list of errors when setting the parameter value.
        """

        errors = []
        for value in data["values"]:
            group_box = value.get("widget")
            if group_box is None or not group_box.isChecked():
                continue

            current_param_errors = []
            for child_parameter_data in value.get("child_parameters", []):
                child_parameter = child_parameter_data.get("parameter")
                if not child_parameter or child_parameter_data.get("type") != "line_edit":
                    continue

                current_param_errors.append(self._set_parameter_from_line_edit(child_parameter, child_parameter_data))

            current_param_errors = list(filter(None, current_param_errors))
            if current_param_errors:
                errors.extend(current_param_errors)
                continue

            parameter_name = value["parameter"]
            parameter_value = value["value"]
            self._measurer.set_value_to_parameter(parameter_name, parameter_value)
        return errors

    @pyqtSlot()
    def set_parameters(self) -> None:
        """
        Method sets values from dialog window to parameters of measurer.
        """

        errors = []
        for parameter_name, data in self._parameters_data.items():
            if data["type"] == "line_edit":
                errors.append(self._set_parameter_from_line_edit(parameter_name, data))
            elif data["type"] == "selectable_group_boxes":
                errors.extend(self._set_parameters_from_selected_group_box(data))

        errors = list(filter(None, errors))
        if errors:
            ut.show_message(qApp.translate("t", "Ошибка"), "<br>".join(errors))
            return

        try:
            self._measurer.set_settings()
            self.close()
        except Exception:
            logger.error("Failed to set settings in measurer '%s'", self._measurer.name)
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("dialogs", "Не удалось задать настройки для измерителя."))


def show_measurer_settings_window(main_window, measurer: IVMeasurerBase, device_name: str) -> None:
    """
    :param main_window: main window of application;
    :param measurer: specific measurer for which settings will be intended;
    :param device_name: name of measurer.
    """

    all_settings = measurer.get_all_settings()
    window = MeasurerSettingsWindow(main_window, all_settings, measurer, device_name)
    main_window.measurers_disconnected.connect(window.close)
    window.exec_()
