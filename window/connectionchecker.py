import logging
import os
import sys
from collections import namedtuple
from typing import List, Optional, Tuple, Union
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QCoreApplication as qApp, QTimer
from epcore.analogmultiplexer import AnalogMultiplexer, AnalogMultiplexerBase, AnalogMultiplexerVirtual
from epcore.ivmeasurer import IVMeasurerASA, IVMeasurerBase, IVMeasurerIVM10, IVMeasurerVirtual, IVMeasurerVirtualASA
from epcore.ivmeasurer.safe_opener import BadFirmwareVersion
from epcore.measurementmanager import MeasurementSystem
import connection_window as cw
from settings.autosettings import AutoSettings
from window import utils as ut


logger = logging.getLogger("eplab")
ConnectionData = namedtuple("ConnectionData", ["measurement_system", "product"])


class ConnectionChecker(QObject):
    """
    Class checks whether IV-measurers and multiplexer can be connected to the given ports.
    """

    TIMEOUT: int = 10
    connect_signal: pyqtSignal = pyqtSignal(ConnectionData)

    def __init__(self, auto_settings: AutoSettings) -> None:
        """
        :param auto_settings: an object with main application settings that are saved from launch to launch.
        """

        super().__init__()
        self._auto_settings: AutoSettings = auto_settings
        self._measurer_1_port: str = None
        self._measurer_2_port: str = None
        self._mux_port: str = None
        self._product_name: cw.ProductName = None
        self._timer: QTimer = QTimer()
        self._timer.timeout.connect(self.check_connection)
        self._timer.setInterval(ConnectionChecker.TIMEOUT)
        self._timer.setSingleShot(True)

    def _check_connection(self) -> bool:
        """
        :return: True if connection is possible.
        """

        measurers, bad_measurer_ports = create_measurers_by_force(self._measurer_1_port, self._measurer_2_port)
        mux, bad_mux_ports = create_multiplexer(self._mux_port)
        self._print_errors(*bad_measurer_ports, *bad_mux_ports)

        if not bad_measurer_ports:
            if len(measurers) > 1:
                # Reorder measurers according to their addresses in USB hubs tree
                measurers = ut.sort_devices_by_usb_numbers(measurers)
            if len(measurers) > 0:
                measurement_system = create_measurement_system(measurers, mux)
            else:
                measurement_system = None
            self.connect_signal.emit(ConnectionData(measurement_system, self._product_name))
            return True

        close_devices(*measurers, mux)
        return False

    def _get_connection_params(self) -> None:
        """
        Method gets connection parameters to IV-measurers and multiplexer from auto settings.
        """

        def get_port(port_str: Optional[str] = None) -> Optional[str]:
            return None if not port_str else port_str

        connection_params = self._auto_settings.get_connection_params()
        self._product_name = cw.ProductName.get_product_name_by_string(connection_params.get("product_name", ""))
        port = connection_params.get("measurer_1_port", None)
        self._measurer_1_port = get_port(port)
        port = connection_params.get("measurer_2_port", None)
        self._measurer_2_port = get_port(port)
        port = connection_params.get("mux_port", None)
        self._mux_port = get_port(port)

    @staticmethod
    def _print_errors(*bad_ports: str) -> None:
        """
        :param bad_ports: list of ports that could not be connected to.
        """

        if len(bad_ports) == 0:
            return

        if len(bad_ports) == 1:
            text = qApp.translate("t", "Не удалось подключиться к {0}. Убедитесь, что {0} - это устройство "
                                       "EyePoint, а не какое-то другое устройство.")
        else:
            text = qApp.translate("t", "Не удалось подключиться к {0}. Убедитесь, что {0} - это устройства "
                                       "EyePoint, а не какие-то другие устройства.")
        ut.show_message(qApp.translate("t", "Ошибка подключения"), text.format(", ".join(bad_ports)))

    @pyqtSlot()
    def check_connection(self) -> None:
        if not self._check_connection():
            self._timer.start()

    def run(self) -> None:
        self._get_connection_params()
        self._timer.start()


def close_devices(*devices: Union[IVMeasurerBase, AnalogMultiplexerBase]) -> None:
    """
    :param devices: list of devices to close.
    """

    for device in devices:
        if device is not None:
            try:
                device.close_device()
            except:
                pass


def create_measurement_system(measurers: List[Optional[IVMeasurerBase]], mux: Optional[AnalogMultiplexerBase]
                              ) -> MeasurementSystem:
    """
    :param measurers: list of IV-measurers for the measurement system;
    :param mux: multiplexer for measurement system.
    :return: created measurement system.
    """

    measurers_ = []
    for i, measurer in enumerate(measurers):
        if measurer:
            measurers_.append(measurer)

    multiplexers = []
    if mux:
        multiplexers.append(mux)

    return MeasurementSystem(measurers_, multiplexers)


def create_measurer(port: str, force_open: Optional[bool] = False, virtual_was: Optional[bool] = False
                    ) -> Optional[IVMeasurerBase]:
    """
    :param port: port where to connect IV-measurer;
    :param force_open: if True, then the IV-measurer must be created even if the IV-measurer firmware is incorrect;
    :param virtual_was: if True, then the virtual IV-measurer has already been created earlier.
    :return: created IV-measurer.
    """

    if port == "virtual":
        measurer = IVMeasurerVirtual(port)
        if virtual_was:
            measurer.nominal = 1000
        return measurer

    if port == "virtualasa":
        return IVMeasurerVirtualASA(port, defer_open=True)

    if port is not None and ("com:" in port or "xi-net:" in port):
        dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(dir_name, "cur.ini")
        return IVMeasurerIVM10(port, config=config_file, defer_open=True, force_open=force_open)

    if port is not None and "xmlrpc:" in port:
        return IVMeasurerASA(port, defer_open=True)

    return None


def create_measurers(*ports: str, force_open: Optional[bool] = False
                     ) -> Tuple[List[IVMeasurerBase], List[str], str, List[Tuple[int, str]]]:
    """
    :param ports: ports for which to create IV-measurers;
    :param force_open: if True, then the IV-measurer must be created even if the IV-measurer firmware is incorrect.
    :return:
    """

    measurers = []
    virtual_was = False
    bad_firmwares = []
    bad_firmwares_ports = []
    bad_ports = []
    for i, port in enumerate(ports):
        try:
            measurer = create_measurer(port, force_open, virtual_was)
            if isinstance(measurer, IVMeasurerVirtual):
                virtual_was = True
        except BadFirmwareVersion as exc:
            logger.error("%s firmware version %s is not compatible with this version of EPLab", exc.args[0],
                         exc.args[2])
            text = qApp.translate("utils", "{}: версия прошивки {} {} несовместима с данной версией EPLab."
                                  ).format(port, exc.args[0], exc.args[2])
            bad_firmwares.append(text)
            bad_firmwares_ports.append((i, port))
            measurer = None
        except Exception:
            logger.error("An error occurred when connecting the IV-measurer to the port '%s'", port,
                         exc_info=sys.exc_info())
            bad_ports.append(port)
            measurer = None
        measurers.append(measurer)
    return measurers, bad_ports, "\n".join(bad_firmwares), bad_firmwares_ports


def create_measurers_by_force(*ports: str) -> Tuple[Optional[List[IVMeasurerBase]], List[str]]:
    """
    :param ports: ports for which to create IV-measurers.
    :return:
    """

    measurers, bad_ports, bad_firmwares, bad_firmwares_ports = create_measurers(*ports)
    if bad_firmwares and ut.request_opening_by_force(bad_firmwares):
        for i, port in bad_firmwares_ports:
            new_measurers, new_bad_ports, _, _ = create_measurers(port, force_open=True)
            if new_measurers:
                measurers[i] = new_measurers[0]
            else:
                bad_ports.extend(new_bad_ports)
    return [measurer for measurer in measurers if measurer is not None], bad_ports


def create_multiplexer(port: Optional[str] = None) -> Tuple[Optional[AnalogMultiplexerBase], List[str]]:
    """
    :param port: port for multiplexer.
    :return: created multiplexer and list with bad ports.
    """

    try:
        if port == "virtual":
            return AnalogMultiplexerVirtual(port, defer_open=True), []

        if port is not None and "com:" in port:
            mux = AnalogMultiplexer(port)
            mux.close_device()
            return mux, []
    except Exception:
        return None, [port]

    return None, []
