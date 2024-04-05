"""
File with a dialog box class for selecting devices to connect.
"""

import logging
from typing import List, Optional
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtWidgets import QDialog, QGroupBox, QHBoxLayout, QLayout, QPushButton, QVBoxLayout
import connection_window.utils as ut
from connection_window.measurertypewidget import MeasurerTypeWidget
from connection_window.measureruriswidget import MeasurerURIsWidget
from connection_window.muxwidget import MuxWidget
from connection_window.productname import ProductName
from window.scaler import update_scale_of_class


logger = logging.getLogger("eplab")


@update_scale_of_class
class ConnectionWindow(QDialog):
    """
    Dialog box class for selecting devices to connect.
    """

    connect_measurers_signal: pyqtSignal = pyqtSignal(dict)
    disconnect_measurers_signal: pyqtSignal = pyqtSignal()

    def __init__(self, main_window, initial_uris: List[str], initial_mux_uri: Optional[str],
                 initial_product_name: ProductName) -> None:
        """
        :param main_window: main window of application;
        :param initial_uris: ports of devices connected to the application when the dialog box opens;
        :param initial_mux_uri: multiplexer URI;
        :param initial_product_name: name of product with which application was working.
        """

        super().__init__(main_window, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._initial_mux_uri: str = initial_mux_uri
        self._initial_ports: List[str] = initial_uris
        self._initial_product_name: ProductName = initial_product_name
        self._urls: list = None
        self._init_ui()
        self.handle_connection(bool(initial_product_name))

    def _init_ui(self) -> None:
        """
        Method initializes widgets in the dialog window.
        """

        self.setWindowTitle(qApp.translate("connection_window", "Настройка подключения"))
        self.setFocusPolicy(Qt.ClickFocus)

        self.widget_measurer_type: MeasurerTypeWidget = MeasurerTypeWidget(self._initial_product_name)
        self.widget_measurer_uris: MeasurerURIsWidget = MeasurerURIsWidget(self._initial_ports)
        self.widget_measurer_type.measurer_type_changed.connect(self.widget_measurer_uris.set_measurer_type)
        self.widget_measurer_type.send_initial_values()

        v_box_layout = QVBoxLayout()
        v_box_layout.addWidget(self.widget_measurer_type)
        v_box_layout.addWidget(self.widget_measurer_uris)
        self.group_box_measurers: QGroupBox = QGroupBox(qApp.translate("connection_window", "Измерители"))
        self.group_box_measurers.setFocusPolicy(Qt.ClickFocus)
        self.group_box_measurers.setLayout(v_box_layout)
        self.widget_mux: MuxWidget = MuxWidget(self._initial_mux_uri)

        h_box_layout = QHBoxLayout()
        h_box_layout.addWidget(self.group_box_measurers)
        h_box_layout.addWidget(self.widget_mux)

        self.button_connect: QPushButton = QPushButton(qApp.translate("connection_window", "Подключить"))
        self.button_connect.setDefault(True)
        self.button_connect.clicked.connect(self.connect_measurers)
        self.button_disconnect: QPushButton = QPushButton(qApp.translate("connection_window", "Отключить"))
        self.button_disconnect.clicked.connect(self.disconnect_measurers)

        layout = QHBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self.button_connect)
        layout.addWidget(self.button_disconnect)
        layout.addStretch(1)
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

        if not self.widget_measurer_uris.validate():
            return

        measurer_uris = self.widget_measurer_uris.get_selected_uris()
        data = {"uri_1": measurer_uris[0],
                "uri_2": measurer_uris[1],
                "product_name": self.widget_measurer_type.get_product_name(),
                "mux_uri": self.widget_mux.get_uri() or None}
        self.connect_measurers_signal.emit(data)

    @pyqtSlot()
    def disconnect_measurers(self) -> None:
        """
        Slot sends signal to disconnect all measurers.
        """

        self.disconnect_measurers_signal.emit()

    def handle_connection(self, connected: bool) -> None:
        """
        :param connected: if True, then devices are connected, otherwise devices are disconnected.
        """

        self.button_connect.setEnabled(not connected)
        self.button_disconnect.setEnabled(connected)
        if connected:
            self.close()


def show_connection_window(main_window, product_name: ProductName) -> None:
    """
    :param main_window: main window of application;
    :param product_name: name of product with which application was working.
    """

    window = ConnectionWindow(main_window, ut.get_current_measurers_uris(main_window),
                              main_window.get_multiplexer_uri(), product_name)
    window.connect_measurers_signal.connect(lambda data: main_window.connect_measurers(**data))
    window.disconnect_measurers_signal.connect(main_window.disconnect_measurers)
    main_window.measurers_connected.connect(window.handle_connection)
    window.exec()
