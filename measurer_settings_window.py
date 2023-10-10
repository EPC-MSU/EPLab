"""
File with class for dialog window with settings of measurer.
"""

import logging
from inspect import getmembers, ismethod
from typing import Any, Callable, Dict, Optional, Union
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator
from epcore.ivmeasurer.base import IVMeasurerBase
import utils as ut
from language import Language


logger = logging.getLogger("eplab")


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


class MeasurerSettingsWindow(qt.QDialog):
    """
    Class for dialog window with settings of measurer.
    """

    MAX_HEIGHT: int = 500
    MAX_WIDTH: int = 400
    MIN_WIDTH: int = 300

    def __init__(self, parent=None, settings: Dict = None, measurer: IVMeasurerBase = None, device_name: str = None):
        """
        :param parent: parent window;
        :param settings: dictionary with all settings of measurer;
        :param measurer: specific measurer for which settings will be intended;
        :param device_name: name of measurer.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._measurer: IVMeasurerBase = measurer
        self._widgets: Dict = dict()
        self.button_cancel: qt.QPushButton = None
        self.button_ok: qt.QPushButton = None
        lang = qApp.instance().property("language")
        self.lang: str = "ru" if lang == Language.RU else "en"
        self._init_ui(settings, device_name)

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
        for member_name, member in getmembers(self._measurer):
            if member_name == data.get("func", None) and ismethod(member):
                button.clicked.connect(lambda: self.run_command(member, member_name, data.get(f"label_{self.lang}")))
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

    def _create_text_browser(self, data: Dict) -> Optional[qt.QWidget]:
        """
        Method creates text browser widget with some info about measurer.
        :param data: information about created label.
        :return: created text browser widget.
        """

        info = data.get(f"label_{self.lang}", "")
        if not info:
            return
        text_browser = qt.QTextBrowser()
        text_browser.setReadOnly(True)
        text_browser.setText(info)
        text_browser.adjustSize()
        return text_browser

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
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumSize(self.MAX_WIDTH, self.MAX_HEIGHT)
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
                elif element["type"] == "text_browser":
                    widget = self._create_text_browser(element)
                if widget is not None:
                    v_box.addWidget(widget)
            self.button_ok = qt.QPushButton("OK")
            self.button_ok.clicked.connect(self.accept)
            self.button_cancel = qt.QPushButton(qApp.translate("t", "Отмена"))
            self.button_cancel.clicked.connect(self.reject)
            h_layout = qt.QHBoxLayout()
            h_layout.addStretch(1)
            h_layout.addWidget(self.button_ok)
            h_layout.addWidget(self.button_cancel)
            v_box.addStretch(1)
            v_box.addLayout(h_layout)
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

    @pyqtSlot()
    def run_command(self, command_to_run: Callable, command_name: str, user_readable_command_name: str):
        """
        Slot runs special commands for IV-measurers connected to buttons.
        :param command_to_run: command to run;
        :param command_name: name of command to run;
        :param user_readable_command_name: user readable name of command to run.
        """

        try:
            command_to_run()
        except Exception:
            logger.error("Failed to execute command %s for measurer %s", command_name, self._measurer.name)
            text = qApp.translate("t", "Не удалось выполнить команду '{}'")
            ut.show_message(qApp.translate("t", "Ошибка"), text.format(user_readable_command_name))

    def set_parameters(self):
        """
        Method sets values from dialog window to parameters of measurer.
        """

        try:
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
        except Exception:
            logger.error("Failed to set settings in measurer %s", self._measurer.name)
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Не удалось задать настройки для измерителя"))
