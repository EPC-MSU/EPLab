"""
File with class for widget to select multiplexer.
"""

import os
from typing import Optional
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QEvent, QObject, Qt
from PyQt5.QtGui import QFocusEvent, QIcon, QPixmap
from PyQt5.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout
import connection_window.utils as ut
from connection_window.urlchecker import URLChecker
from window.utils import DIR_MEDIA, show_message


class MuxWidget(QGroupBox):
    """
    Class for widget to show list of COM-ports for multiplexer.
    """

    BUTTON_HELP_WIDTH: int = 20
    BUTTON_UPDATE_WIDTH: int = 25
    COMBO_BOX_MIN_WIDTH: int = 200
    IMAGE_SIZE: int = 200

    def __init__(self):
        super().__init__()
        self._url_checker: URLChecker = URLChecker(True)
        self._init_ui()

    def _init_combo_box(self) -> QComboBox:
        """
        Method initializes combo box widget for COM-ports.
        :return: combo box widget created for multiplexer.
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
        self.combo_box_com_ports: QComboBox = self._init_combo_box()
        self.update_com_ports()
        self.button_update: QPushButton = QPushButton()
        self.button_update.setFixedWidth(MuxWidget.BUTTON_UPDATE_WIDTH)
        self.button_update.setIcon(QIcon(os.path.join(DIR_MEDIA, "update.png")))
        self.button_update.setToolTip(qApp.translate("connection_window", "Обновить"))
        self.button_update.clicked.connect(self.update_com_ports)
        self.button_show_help: QPushButton = QPushButton()
        self.button_show_help.setIcon(QIcon(os.path.join(DIR_MEDIA, "info.png")))
        self.button_show_help.setToolTip(qApp.translate("connection_window", "Помощь"))
        self.button_show_help.setFixedWidth(MuxWidget.BUTTON_HELP_WIDTH)
        self.button_show_help.clicked.connect(self.show_help)

        h_box_layout = QHBoxLayout()
        h_box_layout.addWidget(self.combo_box_com_ports)
        h_box_layout.addWidget(self.button_update)
        h_box_layout.addWidget(self.button_show_help)
        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(label, alignment=Qt.AlignHCenter)
        v_box_layout.addLayout(h_box_layout)
        v_box_layout.addStretch(1)
        self.setLayout(v_box_layout)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        :param obj:
        :param event:
        :return:
        """

        if isinstance(event, QFocusEvent) and obj == self.combo_box_com_ports:
            self._url_checker.color_widget(obj, QFocusEvent(event))
        return False

    def get_com_port(self) -> Optional[str]:
        """
        Method returns selected COM-port of multiplexer.
        :return: selected COM-port of multiplexer.
        """

        if self._url_checker.check_url_for_correctness(self.combo_box_com_ports):
            if self.combo_box_com_ports.currentText().lower() == "none":
                return None
            return self.combo_box_com_ports.currentText()
        return None

    @pyqtSlot()
    def show_help(self) -> None:
        """
        Slot shows help information how to enter COM-port.
        """

        port_format = "com:///dev/ttyx" if ut.get_platform() == "debian" else "com:\\\\.\\COMx"
        info = qApp.translate("connection_window", "Введите значение последовательного порта в формате {}."
                              ).format(port_format)
        show_message(qApp.translate("connection_window", "Помощь"), info, icon=QMessageBox.Information)

    @pyqtSlot()
    def update_com_ports(self) -> None:
        """
        Method updates list of COM-ports.
        """

        self.combo_box_com_ports.clear()
        ports = ut.find_urpc_ports("epmux")
        ports.extend(["none", "virtual"])
        self.combo_box_com_ports.addItems(ports)
        self.combo_box_com_ports.setCurrentText(ports[0])

        self._url_checker.color_widgets(self.combo_box_com_ports)
