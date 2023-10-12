from typing import Dict, List
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, QEvent, QObject, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QRadioButton, QScrollArea, QVBoxLayout, QWidget
from epcore.product import EyePointProduct
from dialogs.language import Language


class ParameterWidget(QScrollArea):

    option_changed: pyqtSignal = pyqtSignal()

    def __init__(self, param_name: EyePointProduct.Parameter, available_options: List) -> None:
        """
        :param param_name: name of parameter;
        :param available_options: available options for parameter.
        """

        super().__init__()
        self._option_buttons: Dict[str, QRadioButton] = {}
        self._param_name: EyePointProduct.Parameter = param_name
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setWidget(self._create_radio_buttons_for_parameter(available_options))

    def _create_radio_buttons_for_parameter(self, available_options: List) -> QWidget:
        """
        Method creates radio buttons for options of given parameter and puts them on widget.
        :param available_options: available options for parameter.
        :return: widget with radio buttons.
        """

        lang = qApp.instance().property("language")
        layout = QVBoxLayout()
        self._option_buttons = {}
        for option in available_options:
            button = QRadioButton()
            button.installEventFilter(self)
            layout.addWidget(button)
            button.setText(option.label_ru if lang is Language.RU else option.label_en)
            button.clicked.connect(self.select_option)
            self._option_buttons[option.name] = button
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def enable_buttons(self, enable: bool) -> None:
        """
        Method enables or disables radio buttons on widget.
        :param enable: if True, then radio buttons will be enabled.
        """

        for button in self._option_buttons.values():
            button.setEnabled(enable)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj in self._option_buttons.values() and isinstance(event, QKeyEvent):
            return True
        return super().eventFilter(obj, event)

    def get_checked_option(self) -> str:
        """
        :return: name of checked option.
        """

        for option_name, button in self._option_buttons.items():
            if button.isChecked():
                return option_name

    def get_checked_option_label(self) -> str:
        """
        :return: label of checked option.
        """

        for button in self._option_buttons.values():
            if button.isChecked():
                return button.text()

    @pyqtSlot(bool)
    def select_option(self, checked: bool) -> None:
        """
        Slot handles selection of new option for parameter of measuring system.
        :param checked: if True radio button corresponding to option was selected.
        """

        if checked:
            self.option_changed.emit()

    def set_checked_option(self, option_name: str) -> None:
        """
        :param option_name: name of option to set checked.
        """

        self._option_buttons[option_name].setChecked(True)

    def update_options(self, available_options: List) -> None:
        old_widget = self.takeWidget()
        del old_widget
        self.setWidget(self._create_radio_buttons_for_parameter(available_options))
