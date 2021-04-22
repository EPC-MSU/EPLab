"""
File with class for dialog window with settings of measurer.
"""

from functools import partial
from inspect import getmembers, ismethod
from typing import Any, Callable, Dict
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from epcore.ivmeasurer.base import IVMeasurerBase

__all__ = ["MeasurerSettingsWindow"]


def get_convertor(data: Dict) -> Callable:
    """
    Function returns suitable convertor.
    :param data: dictionary with type name for converter.
    :return: convertor.
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

    def __init__(self, parent=None, settings: Dict = None,
                 measurer: IVMeasurerBase = None):
        """
        :param parent: parent window;
        :param settings: dictionary with all settings of measurer;
        :param measurer: specific measurer for which settings will be intended.
        """

        super().__init__(parent=parent)
        self._measurer = measurer
        self._widgets = dict()
        self._init_ui(settings)

    def _create_button(self, data: Dict) -> qt.QWidget:
        """
        Method creates button that will call method of measurer for execution.
        :param data: information about created button.
        :return: created button.
        """

        button = qt.QPushButton(data["title"])
        for member_name, member in getmembers(self._measurer):
            if member_name == data["func"] and ismethod(member):
                button.clicked.connect(member)
                break
        return button

    def _create_combobox(self, data: Dict, current_value: Any) -> qt.QWidget:
        """
        Method creates combobox to select one of several available values of
        parameter of measurer.
        :param data: information about created combobox;
        :param current_value: current value of parameter for which combobox is
        created.
        :return: created combobox.
        """

        label = qt.QLabel(data["parameter_name"])
        combo = qt.QComboBox()
        labels = [item["label"] for item in data["values"]]
        combo.addItems(labels)
        # Find index of current value of parameter in list of available values
        convertor = get_convertor(data)
        for index, item in enumerate(data["values"]):
            if convertor(item["value"]) == current_value:
                combo.setCurrentIndex(index)
                break
        h_box = qt.QHBoxLayout()
        h_box.addWidget(label)
        h_box.addWidget(combo)
        widget = qt.QWidget()
        widget.setLayout(h_box)
        data["widget"] = combo
        self._widgets[data["parameter"]] = data
        return widget

    def _create_line_edit(self, data: Dict, current_value: Any) -> qt.QWidget:
        """
        Method creates line edit to input value of parameter of measurer.
        :param data: information about created line edit;
        :param current_value: current value of parameter for which line edit is
        created.
        :return: created line edit.
        """

        label = qt.QLabel(data["parameter_name"])
        line_edit = qt.QLineEdit()
        if data["value_type"] == "float":
            validator = QRegExpValidator(QRegExp(r"^\d*\.\d*$"))
            line_edit.setValidator(validator)
        elif data["value_type"] == "int":
            validator = QRegExpValidator(QRegExp(r"^\d+$"))
            line_edit.setValidator(validator)
        if "max" in data and "min" in data:
            line_edit.textChanged.connect(
                partial(self._process_line_edit, data, line_edit))
        # Set current value
        line_edit.setText(str(current_value))
        h_box = qt.QHBoxLayout()
        h_box.addWidget(label)
        h_box.addWidget(line_edit)
        widget = qt.QWidget()
        widget.setLayout(h_box)
        data["widget"] = line_edit
        self._widgets[data["parameter"]] = data
        return widget

    def _create_radio_button(self, data: Dict,
                             current_value: Any) -> qt.QWidget:
        """
        Method creates radio buttons to select one of several available values
        of parameter of measurer.
        :param data: information about created radio buttons;
        :param current_value: current value of parameter for which radio
        buttons are created.
        :return: created radio buttons.
        """

        v_box = qt.QVBoxLayout()
        radios = []
        convertor = get_convertor(data)
        for item in data["values"]:
            radio = qt.QRadioButton(item["label"])
            v_box.addWidget(radio)
            radios.append(radio)
            if convertor(item["value"]) == current_value:
                radio.setChecked(True)
        group = qt.QGroupBox(data["parameter_name"])
        group.setLayout(v_box)
        data["widget"] = radios
        self._widgets[data["parameter"]] = data
        return group

    @staticmethod
    def _get_value_from_combo(data: Dict):
        """
        Method gets value from combobox.
        :param data: dictionary with combobox widget and available values.
        :return: selected value.
        """

        widget = data["widget"]
        index = widget.currentIndex()
        return data["values"][index]["value"]

    @staticmethod
    def _get_value_from_line_edit(data: Dict):
        """
        Method gets value from line edit.
        :param data: dictionary with line edit.
        :return: value.
        """

        widget = data["widget"]
        return widget.text()

    @staticmethod
    def _get_value_from_radio(data):
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

    def _init_ui(self, settings: Dict):
        """
        Method initializes widgets in dialog window.
        :param settings: dictionary with all settings of measurer.
        """

        v_box = qt.QVBoxLayout()
        if settings:
            device_name = self._measurer.get_identity_information().device_name
            self.setWindowTitle(f"Настройки для {device_name}")
            for element in settings["elements"]:
                if "parameter" in element:
                    current_value = self._measurer.get_current_value_of_parameter(
                        element["parameter"])
                if element["type"] == "button":
                    widget = self._create_button(element)
                elif element["type"] == "radio_button":
                    widget = self._create_radio_button(element, current_value)
                elif element["type"] == "combobox":
                    widget = self._create_combobox(element, current_value)
                elif element["type"] == "line_edit":
                    widget = self._create_line_edit(element, current_value)
                v_box.addWidget(widget)
            btns = qt.QDialogButtonBox.Ok | qt.QDialogButtonBox.Cancel
            self.buttonBox = qt.QDialogButtonBox(btns)
            self.buttonBox.accepted.connect(self.accept)
            self.buttonBox.rejected.connect(self.reject)
            v_box.addWidget(self.buttonBox)
        else:
            v_box.addWidget(qt.QLabel("Нет настроек"))
        self.adjustSize()
        self.setLayout(v_box)

    @staticmethod
    def _process_line_edit(data: Dict, line_edit: qt.QLineEdit,
                           text: str):
        """
        Method processes changing the text in the line edit.
        :param data: data for parameter for which line edit is assigned.
        :param line_edit: line edit;
        :param text: text in line edit.
        """

        if not text:
            return
        convertor = get_convertor(data)
        min_value = convertor(data["min"])
        max_value = convertor(data["max"])
        value = convertor(text)
        if min_value > value:
            line_edit.setText(str(min_value))
        elif max_value < value:
            line_edit.setText(str(max_value))

    def set_parameters(self):
        """
        Method sets values from dialog window to parameters of measurer.
        """

        for parameter_name, data in self._widgets.items():
            value = None
            convertor = get_convertor(data)
            if data["type"] == "combo":
                value = self._get_value_from_combo(data)
            elif data["type"] == "line_edit":
                value = self._get_value_from_line_edit(data)
            elif data["type"] == "radio_button":
                value = self._get_value_from_radio(data)
            if value:
                value = convertor(value)
                self._measurer.set_value_to_parameter(parameter_name, value)
        self._measurer.set_settings()
