"""
File with a dialog box class for selecting devices to connect.
"""

import logging
from typing import List
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtWidgets import QDialog, QGroupBox, QHBoxLayout, QLayout, QPushButton, QVBoxLayout
import connection_window.utils as ut
from connection_window.measurer_widget import MeasurerTypeWidget, MeasurerURLsWidget
from connection_window.mux_widget import MuxWidget


logger = logging.getLogger("eplab")


class ConnectionWindow(QDialog):
    """
    Dialog box class for selecting devices to connect.
    """

    connect_measurers_signal: pyqtSignal = pyqtSignal(dict)
    disconnect_measurers_signal: pyqtSignal = pyqtSignal()

    def __init__(self, main_window, initial_ports: List[str], initial_product_name: ut.ProductNames) -> None:
        """
        :param main_window: main window of application;
        :param initial_ports:
        :param initial_product_name: name of product with which application was working.
        """

        super().__init__(main_window, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._initial_ports: List[str] = initial_ports
        self._initial_product_name: ut.ProductNames = initial_product_name
        self._urls: list = None
        self._init_ui()
        self.handle_connection(bool(initial_product_name))

    def _init_ui(self) -> None:
        """
        Method initializes widgets in the dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "Настройка подключения"))

        self.widget_measurer_type: MeasurerTypeWidget = MeasurerTypeWidget(self._initial_product_name)
        self.widget_measurer_urls: MeasurerURLsWidget = MeasurerURLsWidget(self._initial_ports)
        self.widget_measurer_type.measurer_type_changed.connect(self.widget_measurer_urls.set_measurer_type)
        self.widget_measurer_type.send_initial_values()

        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self.widget_measurer_type)
        v_box_layout.addWidget(self.widget_measurer_urls)
        group_box_measurers = QGroupBox(qApp.translate("t", "Измерители"))
        group_box_measurers.setLayout(v_box_layout)
        self.widget_mux: MuxWidget = MuxWidget()

        h_box_layout = QHBoxLayout()
        h_box_layout.addWidget(group_box_measurers)
        h_box_layout.addWidget(self.widget_mux)

        self.button_connect: QPushButton = QPushButton(qApp.translate("t", "Подключить"))
        self.button_connect.setDefault(True)
        self.button_connect.clicked.connect(self.connect_measurers)
        self.button_disconnect: QPushButton = QPushButton(qApp.translate("t", "Отключить"))
        self.button_disconnect.clicked.connect(self.disconnect_measurers)
        self.button_cancel: QPushButton = QPushButton(qApp.translate("t", "Отмена"))
        self.button_cancel.clicked.connect(self.close)

        layout = QHBoxLayout()
        layout.addWidget(self.button_connect)
        layout.addWidget(self.button_disconnect)
        layout.addWidget(self.button_cancel)
        v_box_layout = QVBoxLayout(self)
        v_box_layout.addLayout(h_box_layout)
        v_box_layout.addLayout(layout)
        v_box_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(v_box_layout)
        self.adjustSize()

    @pyqtSlot()
    def connect_measurers(self) -> None:
        """
        Slot sends signal to connect new measurers.
        """

        if not self.widget_measurer_urls.validate():
            self.widget_measurer_urls.show_help()
            return

        measurer_ports = self.widget_measurer_urls.get_selected_ports()
        measurer_ports = ut.get_different_ports(measurer_ports)
        while len(measurer_ports) < 2:
            measurer_ports.append(None)
        selected_product_name = self.widget_measurer_type.get_product_name()
        for index, port in enumerate(measurer_ports):
            if (port == "virtual" and
                    ut.ProductNames.get_measurer_type_by_product_name(selected_product_name) == ut.MeasurerType.ASA):
                measurer_ports[index] = "virtualasa"
        data = {"port_1": measurer_ports[0],
                "port_2": measurer_ports[1],
                "product_name": selected_product_name,
                "mux_port": self.widget_mux.get_com_port() or None}
        self.connect_measurers_signal.emit(data)

    @pyqtSlot()
    def disconnect_measurers(self) -> None:
        """
        Slot sends signal to disconnect all measurers.
        """

        self.disconnect_measurers_signal.emit()

    def handle_connection(self, connected: bool) -> None:
        """
        :param connected:
        """

        self.button_connect.setEnabled(not connected)
        self.button_disconnect.setEnabled(connected)
