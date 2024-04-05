"""
File with class for widget to select multiplexer.
"""

import os
from typing import Optional
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QEvent, QObject, Qt
from PyQt5.QtGui import QFocusEvent, QIcon, QPixmap
from PyQt5.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout
import connection_window.utils as ut
from connection_window.urichecker import URIChecker
from window.scaler import update_scale_of_class
from window.utils import DIR_MEDIA, show_message


@update_scale_of_class
class MuxWidget(QGroupBox):
    """
    Class for widget to show list of COM-ports for multiplexer.
    """

    BUTTON_HELP_WIDTH: int = 20
    BUTTON_UPDATE_WIDTH: int = 25
    COMBO_BOX_MIN_WIDTH: int = 200
    IMAGE_SIZE: int = 200

    def __init__(self, initial_mux_uri: Optional[str]) -> None:
        """
        :param initial_mux_uri: multiplexer URI.
        """

        super().__init__()
        self._initial_uri: str = "none" if initial_mux_uri is None else initial_mux_uri
        self._uri_checker: URIChecker = URIChecker(True)
        self._init_ui()

    def _init_combo_box(self) -> QComboBox:
        """
        :return: combo box widget for COM-ports of multiplexer.
        """

        combo_box = QComboBox()
        combo_box.setEditable(True)
        combo_box.setMinimumWidth(MuxWidget.COMBO_BOX_MIN_WIDTH)
        placeholder = "com:///dev/ttyx" if ut.get_platform() == "debian" else "com:\\\\.\\COMx"
        combo_box.lineEdit().setPlaceholderText(placeholder)
        combo_box.installEventFilter(self)
        return combo_box

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget for multiplexer.
        """

        self.setTitle(qApp.translate("connection_window", "Мультиплексор"))
        self.setFocusPolicy(Qt.ClickFocus)

        mux_image = QPixmap(os.path.join(DIR_MEDIA, "mux.png"))
        label = QLabel("")
        label.setPixmap(mux_image.scaled(MuxWidget.IMAGE_SIZE, MuxWidget.IMAGE_SIZE, Qt.KeepAspectRatio))
        self.combo_boxes: QComboBox = self._init_combo_box()
        self.update_uris()
        self.button_update: QPushButton = QPushButton()
        self.button_update.setFixedWidth(MuxWidget.BUTTON_UPDATE_WIDTH)
        self.button_update.setIcon(QIcon(os.path.join(DIR_MEDIA, "update.png")))
        self.button_update.setToolTip(qApp.translate("connection_window", "Обновить"))
        self.button_update.clicked.connect(self.update_uris)
        self.button_show_help: QPushButton = QPushButton()
        self.button_show_help.setIcon(QIcon(os.path.join(DIR_MEDIA, "info.png")))
        self.button_show_help.setToolTip(qApp.translate("connection_window", "Помощь"))
        self.button_show_help.setFixedWidth(MuxWidget.BUTTON_HELP_WIDTH)
        self.button_show_help.clicked.connect(show_help)

        h_box_layout = QHBoxLayout()
        h_box_layout.addWidget(self.combo_boxes)
        h_box_layout.addWidget(self.button_update)
        h_box_layout.addWidget(self.button_show_help)
        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(label, alignment=Qt.AlignHCenter)
        v_box_layout.addLayout(h_box_layout)
        v_box_layout.addStretch(1)
        self.setLayout(v_box_layout)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        :param obj: the object with which the event occurred;
        :param event: event.
        :return: to filter the event out, i.e. stop it being handled further, return True, otherwise return False.
        """

        if isinstance(event, QFocusEvent) and obj == self.combo_boxes:
            self._uri_checker.color_widget(obj, QFocusEvent(event))
        return False

    def get_uri(self) -> Optional[str]:
        """
        :return: selected URI of multiplexer.
        """

        if self._uri_checker.check_uri_for_correctness(self.combo_boxes):
            if self.combo_boxes.currentText().lower() == "none":
                return None
            return self.combo_boxes.currentText()
        return None

    @pyqtSlot()
    def update_uris(self) -> None:
        """
        Slot updates list of URIs.
        """

        self.combo_boxes.clear()
        ports = ut.find_urpc_ports("epmux")
        ports.extend(["none", "virtual"])
        self.combo_boxes.addItems(ports)
        self.combo_boxes.setCurrentText(self._initial_uri)

        self._uri_checker.color_widgets(self.combo_boxes)


def show_help() -> None:
    """
    Function shows help information how to enter URI.
    """

    port_format = "com:///dev/ttyx" if ut.get_platform() == "debian" else "com:\\\\.\\COMx"
    info = qApp.translate("connection_window", "Введите значение последовательного порта в формате {}."
                          ).format(port_format)
    show_message(qApp.translate("connection_window", "Помощь"), info, icon=QMessageBox.Information)
