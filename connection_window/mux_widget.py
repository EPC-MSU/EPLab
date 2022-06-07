"""
File with class for widget to select multiplexer.
"""

import os
from typing import Optional
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRegExp, Qt
from PyQt5.QtGui import QIcon, QPixmap, QRegExpValidator
import connection_window.utils as ut


class MuxWidget(qt.QGroupBox):
    """
    Class for widget to show list of COM-ports for multiplexer.
    """

    BUTTON_HELP_WIDTH: int = 20
    BUTTON_UPDATE_WIDTH: int = 25
    COMBO_BOX_MIN_WIDTH: int = 200
    IMAGE_SIZE: int = 200

    def __init__(self):
        super().__init__()
        self.button_show_help: qt.QPushButton = None
        self.button_update: qt.QPushButton = None
        self.combo_box_com_ports: qt.QComboBox = None
        self._init_ui()

    def _init_combo_box(self) -> qt.QComboBox:
        """
        Method initializes combo box widget for COM-ports.
        :return: combo box widget created for multiplexer.
        """

        combo_box = qt.QComboBox()
        combo_box.setEditable(True)
        combo_box.setMinimumWidth(self.COMBO_BOX_MIN_WIDTH)
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

    def _init_ui(self):
        """
        Method initializes widgets on main widget for multiplexer.
        """

        self.setTitle(qApp.translate("t", "Мультиплексор"))
        mux_image = QPixmap(os.path.join(ut.DIR_MEDIA, "mux.png"))
        label = qt.QLabel("")
        label.setPixmap(mux_image.scaled(self.IMAGE_SIZE, self.IMAGE_SIZE, Qt.KeepAspectRatio))
        label.setToolTip(qApp.translate("t", "Мультиплексор"))
        self.combo_box_com_ports = self._init_combo_box()
        self.update_com_ports()
        self.button_update = qt.QPushButton()
        self.button_update.setFixedWidth(self.BUTTON_UPDATE_WIDTH)
        self.button_update.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "update.png")))
        self.button_update.setToolTip(qApp.translate("t", "Обновить"))
        self.button_update.clicked.connect(self.update_com_ports)
        self.button_show_help = qt.QPushButton()
        self.button_show_help.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "info.png")))
        self.button_show_help.setToolTip(qApp.translate("t", "Помощь"))
        self.button_show_help.setFixedWidth(self.BUTTON_HELP_WIDTH)
        self.button_show_help.clicked.connect(self.show_help)
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addWidget(self.combo_box_com_ports)
        h_box_layout.addWidget(self.button_update)
        h_box_layout.addWidget(self.button_show_help)
        v_box_layout = qt.QVBoxLayout()
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
    def show_help(self):
        """
        Slot shows help information how to enter COM-port.
        """

        msg_box = qt.QMessageBox()
        msg_box.setIcon(qt.QMessageBox.Information)
        msg_box.setWindowTitle(qApp.translate("t", "Помощь"))
        msg_box.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "ico.png")))
        if "win" in ut.get_platform():
            info = qApp.translate("t", "Введите значение последовательного порта в формате com:\\\\.\\COMx.")
        else:
            info = qApp.translate("t", "Введите значение последовательного порта в формате com:///dev/ttyACMx.")
        msg_box.setText(info)
        msg_box.exec_()

    @pyqtSlot()
    def update_com_ports(self):
        """
        Method updates list of COM-ports.
        """

        self.combo_box_com_ports.clear()
        ports = ut.find_urpc_ports("epmux")
        ports.extend(["none", "virtual"])
        self.combo_box_com_ports.addItems(ports)
        self.combo_box_com_ports.setCurrentText(ports[0])
