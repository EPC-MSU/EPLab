from typing import Optional
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QTimer
import connection_window as cw
from settings.autosettings import AutoSettings


class ConnectionChecker(QObject):

    TIMEOUT: int = 10
    connect_signal: pyqtSignal = pyqtSignal()
    disconnect_signal: pyqtSignal = pyqtSignal()

    def __init__(self, auto_settings: AutoSettings, port_1: Optional[str] = None, port_2: Optional[str] = None) -> None:
        """
        :param auto_settings:
        :param port_1:
        :param port_2:
        """

        super().__init__()
        self._auto_settings: AutoSettings = auto_settings
        self._timer: QTimer = QTimer()
        self._timer.timeout.connect(self.check_connection)
        self._timer.setInterval(ConnectionChecker.TIMEOUT)
        self._timer.setSingleShot(True)

    def _check_connection(self) -> None:
        pass

    def connect_measurers(self, port_1: Optional[str], port_2: Optional[str]) -> None:
        """
        :param port_1: port for first IV-measurer;
        :param port_2: port for second IV-measurer;
        :param product_name: name of product to work with application;
        :param mux_port: port for multiplexer.
        """

        good_com_ports, bad_com_ports = cw.utils.check_com_ports([port_1, port_2, None])

        self._msystem, bad_com_ports = ut.create_measurement_system(*good_com_ports)
        if bad_com_ports:
            if len(bad_com_ports) == 1:
                text = qApp.translate("t", "Не удалось подключиться к {0}. Убедитесь, что {0} - это устройство "
                                           "EyePoint, а не какое-то другое устройство.")
            else:
                text = qApp.translate("t", "Не удалось подключиться к {0}. Убедитесь, что {0} - это устройства "
                                           "EyePoint, а не какие-то другие устройства.")
            ut.show_message(qApp.translate("t", "Ошибка подключения"), text.format(", ".join(bad_com_ports)))

    @pyqtSlot()
    def check_connection(self) -> None:
        self._check_connection()
        self._timer.start()

    def run(self) -> None:
        self._timer.start()
