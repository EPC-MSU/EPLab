"""
File with class for dialog window with settings of measurer.
"""

import logging
from inspect import getmembers, ismethod
from typing import Any, Callable, Dict, Optional, Union
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QCloseEvent, QRegExpValidator, QTextCursor
from epcore.ivmeasurer.base import IVMeasurerBase
from language import Language


def get_converter(data: Dict) -> Callable:
    """
    Function returns suitable converter function.
    :param data: dictionary with type name for converter.
    :return: converter.
    """

    value_type = data.get("value_type")
    if value_type == "int":
        return int
    if value_type == "float":
        return float
    return str


class LoggerHandler(logging.Handler):
    """
    Class to intercept messages from required logger.
    """

    def __init__(self, parent):
        super().__init__()
        self.parent: MeasurerSettingsWindow = parent

    def emit(self, record: logging.LogRecord):
        self.parent.show_message(self.format(record))


class MeasurerSettingsWindow(qt.QDialog):
    """
    Class for dialog window with settings of measurer.
    """

    def __init__(self, parent=None, settings: Dict = None, measurer: IVMeasurerBase = None, device_name: str = None):
        """
        :param parent: parent window;
        :param settings: dictionary with all settings of measurer;
        :param measurer: specific measurer for which settings will be intended;
        :param device_name: name of measurer.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._function_to_stop: Callable = None
        self._handler: LoggerHandler = None
        self._measurer: IVMeasurerBase = measurer
        self._parent = parent
        self._widgets: Dict = dict()
        self.text_edit_logs: qt.QTextEdit = None
        lang = qApp.instance().property("language")
        self.lang: str = "ru" if lang == Language.RU else "en"
        self._init_ui(settings, device_name)
        parent.stop_periodic_task()

    def _create_button(self, data: Dict) -> Optional[qt.QWidget]:
        """
        Method creates button that will call method of measurer for execution.
        :param data: information about created button.
        :return: created button.
        """

        label = data.get(f"label_{self.lang}")
        if not label:
            return None
        button = qt.QPushButton(label)
        if data.get(f"tooltip_{self.lang}"):
            button.setToolTip(data.get(f"tooltip_{self.lang}"))
        if data.get("logger_name") and self._handler is None:
            self.text_edit_logs = qt.QTextEdit()
            self.text_edit_logs.setReadOnly(True)
            logger = logging.getLogger(data["logger_name"])
            self._handler = LoggerHandler(self)
            logger.addHandler(self._handler)
        if data.get("func_to_stop"):
            for member_name, member in getmembers(self._measurer):
                if member_name == data["func_to_stop"] and ismethod(member):
                    self._function_to_stop = member
        for member_name, member in getmembers(self._measurer):
            if member_name == data.get("func", None) and ismethod(member):
                button.clicked.connect(member)
                return button
        return None

    def _create_combobox(self, data: Dict, current_value: Any) -> Optional[qt.QWidget]:
        """
        Method creates combobox to select one of several available values of
        parameter of measurer.
        :param data: information about created combobox;
        :param current_value: current value of parameter for which combobox is created.
        :return: created combobox.
        """

        label = data.get(f"parameter_name_{self.lang}")
        labels = [item[f"label_{self.lang}"] for item in data.get("values", [])]
        parameter = data.get("parameter")
        if not label or not labels or not parameter:
            return None
        combo = qt.QComboBox()
        combo.addItems(labels)
        # Find index of current value of parameter in list of available values
        converter = get_converter(data)
        for index, item in enumerate(data.get("values", [])):
            if converter(item["value"]) == current_value:
                combo.setCurrentIndex(index)
                break
        h_box = qt.QHBoxLayout()
        h_box.addWidget(qt.QLabel(label))
        h_box.addWidget(combo)
        widget = qt.QWidget()
        widget.setLayout(h_box)
        data["widget"] = combo
        self._widgets[parameter] = data
        if data.get(f"tooltip_{self.lang}"):
            widget.setToolTip(data.get(f"tooltip_{self.lang}"))
        return widget

    def _create_line_edit(self, data: Dict, current_value: Any) -> Optional[qt.QWidget]:
        """
        Method creates line edit to input value of parameter of measurer.
        :param data: information about created line edit;
        :param current_value: current value of parameter for which line edit is created.
        :return: created line edit.
        """

        label = data.get(f"parameter_name_{self.lang}")
        parameter = data.get("parameter")
        if not label or not parameter:
            return None
        line_edit = qt.QLineEdit()
        if data.get("value_type") == "float":
            validator = QRegExpValidator(QRegExp(r"^\d*\.\d*$"))
            line_edit.setValidator(validator)
        elif data.get("value_type") == "int":
            validator = QRegExpValidator(QRegExp(r"^\d+$"))
            line_edit.setValidator(validator)
        # Set current value
        line_edit.setText(str(current_value))
        h_box = qt.QHBoxLayout()
        h_box.addWidget(qt.QLabel(label))
        h_box.addWidget(line_edit)
        widget = qt.QWidget()
        widget.setLayout(h_box)
        data["widget"] = line_edit
        self._widgets[parameter] = data
        if data.get(f"tooltip_{self.lang}"):
            widget.setToolTip(data.get(f"tooltip_{self.lang}"))
        return widget

    def _create_radio_button(self, data: Dict, current_value: Any) -> Optional[qt.QWidget]:
        """
        Method creates radio buttons to select one of several available values
        of parameter of measurer.
        :param data: information about created radio buttons;
        :param current_value: current value of parameter for which radio buttons are created.
        :return: created radio buttons.
        """

        label = data.get(f"parameter_name_{self.lang}")
        parameter = data.get("parameter")
        values = data.get("values", [])
        if not label or not parameter or not values:
            return None
        v_box = qt.QVBoxLayout()
        radios = []
        converter = get_converter(data)
        for item in values:
            if not item.get(f"label_{self.lang}") or item.get("value") is None:
                continue
            radio = qt.QRadioButton(item[f"label_{self.lang}"])
            v_box.addWidget(radio)
            radios.append(radio)
            if converter(item["value"]) == current_value:
                radio.setChecked(True)
        if not radios:
            return None
        group = qt.QGroupBox(label)
        group.setLayout(v_box)
        data["widget"] = radios
        self._widgets[parameter] = data
        if data.get(f"tooltip_{self.lang}"):
            group.setToolTip(data.get(f"tooltip_{self.lang}"))
        return group

    @staticmethod
    def _create_title(device_name: Optional[str] = None) -> str:
        """
        Method creates title for dialog window.
        :param device_name: name of measurer.
        """

        title = qApp.translate("t", "Настройки. ")
        if device_name is None:
            device_name = qApp.translate("t", "Неизвестный измеритель")
        return title + device_name

    @staticmethod
    def _get_value_from_combo(data: Dict) -> Union[float, int, str]:
        """
        Method gets value from combobox.
        :param data: dictionary with combobox widget and available values.
        :return: selected value.
        """

        widget = data["widget"]
        index = widget.currentIndex()
        return data["values"][index]["value"]

    def _get_value_from_line_edit(self, data: Dict) -> Optional[float]:
        """
        Method gets value from line edit.
        :param data: dictionary with line edit.
        :return: value.
        """

        widget = data["widget"]
        text = widget.text()
        return self._process_line_edit(data, text)

    @staticmethod
    def _get_value_from_radio(data) -> Optional[Union[float, int, str]]:
        """
        Method gets value from group of radio buttons.
        :param data: dictionary with radio buttons and available values.
        :return: selected value.
        """

        widgets = data["widget"]
        for index, widget in enumerate(widgets):
            if widget.isChecked():
                return data["values"][index]["value"]
        return None

    def _init_ui(self, settings: Optional[Dict] = None, device_name: Optional[str] = None):
        """
        Method initializes widgets in dialog window.
        :param settings: dictionary with all settings of measurer;
        :param device_name: name of measurer.
        """

        self.setWindowTitle(self._create_title(device_name))
        self.setMinimumWidth(300)
        self.setMaximumSize(400, 500)
        v_box = qt.QVBoxLayout()
        if isinstance(settings, dict) and settings.get("elements"):
            for element in settings.get("elements", []):
                widget = None
                if "parameter" in element:
                    current_value = self._measurer.get_current_value_of_parameter(element["parameter"])
                if element["type"] == "button":
                    widget = self._create_button(element)
                elif element["type"] == "radio_button":
                    widget = self._create_radio_button(element, current_value)
                elif element["type"] == "combobox":
                    widget = self._create_combobox(element, current_value)
                elif element["type"] == "line_edit":
                    widget = self._create_line_edit(element, current_value)
                if widget is not None:
                    v_box.addWidget(widget)
            if self.text_edit_logs:
                v_box.addWidget(self.text_edit_logs)
            self.buttonBox = qt.QDialogButtonBox(qt.QDialogButtonBox.Ok | qt.QDialogButtonBox.Cancel)
            self.buttonBox.accepted.connect(self.accept)
            self.buttonBox.rejected.connect(self.reject)
            v_box.addStretch(1)
            v_box.addWidget(self.buttonBox)
        else:
            v_box.addWidget(qt.QLabel(qApp.translate("t", "Нет настроек")), alignment=Qt.AlignHCenter)
        self.setLayout(v_box)

    @staticmethod
    def _process_line_edit(data: Dict, text: str) -> Optional[float]:
        """
        Method processes the text in the line edit.
        :param data: data for parameter for which line edit is assigned;
        :param text: text in line edit.
        :return: number in line edit.
        """

        if not text:
            return None
        converter = get_converter(data)
        min_value = converter(data["min"])
        max_value = converter(data["max"])
        try:
            value = converter(text)
        except ValueError:
            return None
        if min_value > value:
            value = min_value
        elif max_value < value:
            value = max_value
        return value

    def closeEvent(self, event: QCloseEvent):
        """
        Method handles event to close dialog window.
        :param event: event to close dialog window.
        """

        self._parent.start_periodic_task()
        if self._function_to_stop:
            self._function_to_stop()
        super().closeEvent(event)

    def set_parameters(self):
        """
        Method sets values from dialog window to parameters of measurer.
        """

        for parameter_name, data in self._widgets.items():
            value = None
            converter = get_converter(data)
            if data["type"] == "combo":
                value = self._get_value_from_combo(data)
            elif data["type"] == "line_edit":
                value = self._get_value_from_line_edit(data)
            elif data["type"] == "radio_button":
                value = self._get_value_from_radio(data)
            if value:
                value = converter(value)
                self._measurer.set_value_to_parameter(parameter_name, value)
        self._measurer.set_settings()

    def show_message(self, message: str):
        """
        Slot shows message from measurer.
        :param message: log.
        """

        self.text_edit_logs.append(message)
        self.text_edit_logs.moveCursor(QTextCursor.End)
