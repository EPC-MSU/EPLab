"""
File with class for widget to select multiplexer.
"""

import os
from typing import Optional
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QIcon, QPixmap, QRegExpValidator
from PyQt5.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout
import connection_window.utils as ut
from utils import DIR_MEDIA, show_message


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
        self.button_show_help: QPushButton = None
        self.button_update: QPushButton = None
        self.combo_box_com_ports: QComboBox = None
        self._init_ui()

    def _init_combo_box(self) -> QComboBox:
        """
        Method initializes combo box widget for COM-ports.
        :return: combo box widget created for multiplexer.
        """

        combo_box = QComboBox()
        combo_box.setEditable(True)
        combo_box.setMinimumWidth(MuxWidget.COMBO_BOX_MIN_WIDTH)
        if ut.get_platform() == "debian":
            reg_exp = r"^(com:///dev/ttyACM\d+|virtual|none)$"
            placeholder = "com:///dev/ttyACMx"
        else:
            reg_exp = r"^(com:\\\\\.\\COM\d+|virtual|none)$"
            placeholder = "com:\\\\.\\COMx"
        combo_box.lineEdit().setValidator(QRegExpValidator(QRegExp(reg_exp), self))
        combo_box.lineEdit().setPlaceholderText(placeholder)
        combo_box.setToolTip(placeholder)
        return combo_box

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget for multiplexer.
        """

        self.setTitle(qApp.translate("connection_window", "Мультиплексор"))
        mux_image = QPixmap(os.path.join(DIR_MEDIA, "mux.png"))
        label = QLabel("")
        label.setPixmap(mux_image.scaled(MuxWidget.IMAGE_SIZE, MuxWidget.IMAGE_SIZE, Qt.KeepAspectRatio))
        self.combo_box_com_ports = self._init_combo_box()
        self.update_com_ports()
        self.button_update = QPushButton()
        self.button_update.setFixedWidth(MuxWidget.BUTTON_UPDATE_WIDTH)
        self.button_update.setIcon(QIcon(os.path.join(DIR_MEDIA, "update.png")))
        self.button_update.setToolTip(qApp.translate("connection_window", "Обновить"))
        self.button_update.clicked.connect(self.update_com_ports)
        self.button_show_help = QPushButton()
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

    def get_com_port(self) -> Optional[str]:
        """
        Method returns selected COM-port of multiplexer.
        :return: selected COM-port of multiplexer.
        """

        if self.combo_box_com_ports.lineEdit().hasAcceptableInput():
            if self.combo_box_com_ports.currentText() == "none":
                return None
            return self.combo_box_com_ports.currentText()
        return None

    @pyqtSlot()
    def show_help(self) -> None:
        """
        Slot shows help information how to enter COM-port.
        """

        if "win" in ut.get_platform():
            info = qApp.translate("connection_window", "Введите значение последовательного порта в формате "
                                                       "com:\\\\.\\COMx.")
        else:
            info = qApp.translate("connection_window", "Введите значение последовательного порта в формате "
                                                       "com:///dev/ttyACMx.")
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
