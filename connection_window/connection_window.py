"""
File with class for dialog window to select devices for connection.
"""

import logging
import os
from typing import List, Optional
import PyQt5.QtWidgets as qt
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from epcore.ivmeasurer import IVMeasurerVirtual, IVMeasurerVirtualASA
import connection_window.utils as ut
from connection_window.measurer_widget import MeasurerTypeWidget, MeasurerURLsWidget
from connection_window.mux_widget import MuxWidget

logger = logging.getLogger("eplab")


class ConnectionWindow(qt.QDialog):
    """
    Class for dialog window to select devices for connection.
    """

    BUTTON_WIDTH: int = 25

    def __init__(self, parent=None, initial_product_name: Optional[ut.ProductNames] = None):
        """
        :param parent: parent window;
        :param initial_product_name: name of product with which application was working.
        """

        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.parent = parent
        self.button_connect: qt.QPushButton = None
        self.button_cancel: qt.QPushButton = None
        self.button_disconnect: qt.QPushButton = None
        self.button_update: qt.QPushButton = None
        self.widget_measurer_type: MeasurerTypeWidget = None
        self.widget_measurer_urls: MeasurerURLsWidget = None
        self.widget_mux: MuxWidget = None
        self._initial_ports: List[str] = self._get_current_measurers_ports()
        self._initial_product_name: ut.ProductNames = initial_product_name
        self._urls: list = None
        self._init_ui()

    def _get_current_measurers_ports(self) -> List[str]:
        """
        Method returns ports of measurers connected to app.
        :return: ports of measurers.
        """

        ports = [None, None]
        for i_measurer, measurer in enumerate(self.parent.get_measurers()):
            if measurer.url:
                ports[i_measurer] = measurer.url
            elif isinstance(measurer, IVMeasurerVirtualASA):
                ports[i_measurer] = ut.MeasurerType.ASA_VIRTUAL.value
            elif isinstance(measurer, IVMeasurerVirtual):
                ports[i_measurer] = ut.MeasurerType.IVM10_VIRTUAL.value
        return ports

    def _init_ui(self):
        """
        Method initializes widgets in dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "Настройка подключения"))
        self.setToolTip(qApp.translate("t", "Настройка подключения"))
        self.widget_measurer_type = MeasurerTypeWidget(self._initial_product_name)
        self.widget_measurer_urls = MeasurerURLsWidget(self._initial_ports)
        self.widget_measurer_type.measurer_type_changed.connect(self.widget_measurer_urls.set_measurer_type)
        self.widget_measurer_type.send_initial_values()
        v_box_layout = qt.QVBoxLayout()
        v_box_layout.addWidget(self.widget_measurer_type)
        v_box_layout.addWidget(self.widget_measurer_urls)
        group_box_measurers = qt.QGroupBox(qApp.translate("t", "Измерители"))
        group_box_measurers.setLayout(v_box_layout)
        self.widget_mux: MuxWidget = MuxWidget()
        h_box_layout = qt.QHBoxLayout()
        h_box_layout.addWidget(group_box_measurers)
        h_box_layout.addWidget(self.widget_mux)
        self.button_connect = qt.QPushButton(qApp.translate("t", "Подключить"))
        self.button_connect.setToolTip(qApp.translate("t", "Подключить"))
        self.button_connect.setDefault(True)
        self.button_connect.clicked.connect(self.connect)
        self.button_disconnect = qt.QPushButton(qApp.translate("t", "Отключить"))
        self.button_disconnect.setToolTip(qApp.translate("t", "Отключить"))
        self.button_disconnect.clicked.connect(self.disconnect)
        self.button_cancel = qt.QPushButton(qApp.translate("t", "Отмена"))
        self.button_cancel.setToolTip(qApp.translate("t", "Отмена"))
        self.button_cancel.clicked.connect(self.close)
        self.button_update = qt.QPushButton()
        self.button_update.setFixedWidth(self.BUTTON_WIDTH)
        self.button_update.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "update.png")))
        self.button_update.setToolTip(qApp.translate("t", "Обновить"))
        self.button_update.clicked.connect(self.widget_mux.update_com_ports)
        self.button_update.clicked.connect(self.widget_measurer_urls.update_ports)
        layout = qt.QHBoxLayout()
        layout.addWidget(self.button_connect)
        layout.addWidget(self.button_disconnect)
        layout.addWidget(self.button_cancel)
        layout.addWidget(self.button_update)
        v_box_layout = qt.QVBoxLayout(self)
        v_box_layout.addLayout(h_box_layout)
        v_box_layout.addLayout(layout)
        v_box_layout.setSizeConstraint(qt.QLayout.SetFixedSize)
        self.setLayout(v_box_layout)
        self.adjustSize()

    @pyqtSlot()
    def connect(self):
        """
        Slot connects new measurers.
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
        self.parent.connect_devices(*measurer_ports, selected_product_name, self.widget_mux.get_com_port() or None)
        self.close()

    @pyqtSlot()
    def disconnect(self):
        """
        Slot disconnects all measurers.
        """

        self.parent.disconnect_devices()
        self.close()
