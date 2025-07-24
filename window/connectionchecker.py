import logging
import os
from collections import namedtuple
from distutils.version import StrictVersion
from typing import Generator, List, Optional, Tuple, Union
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QCoreApplication as qApp, QTimer
from epcore.analogmultiplexer import AnalogMultiplexer, AnalogMultiplexerBase, AnalogMultiplexerVirtual
from epcore.ivmeasurer import IVMeasurerASA, IVMeasurerBase, IVMeasurerIVM, IVMeasurerVirtual, IVMeasurerVirtualASA
from epcore.ivmeasurer.safe_opener import BadFirmwareVersion, get_major_and_minor_version_parts
from epcore.measurementmanager import MeasurementSystem
import connection_window as cw
from settings.autosettings import AutoSettings
from . import utils as ut
from .language import get_link_in_set_language


logger = logging.getLogger("eplab")
FIRST_FIRMWARE_WITH_BUTTONS = StrictVersion("2.4")
ConnectionData = namedtuple("ConnectionData", ["measurement_system", "product"])


class ConnectionChecker(QObject):
    """
    Class checks whether IV-measurers and multiplexer can be connected to the given ports.
    """

    TIMEOUT_MS: int = 300
    connect_signal: pyqtSignal = pyqtSignal(ConnectionData)

    def __init__(self, auto_settings: AutoSettings) -> None:
        """
        :param auto_settings: an object with main application settings that are saved from launch to launch.
        """

        super().__init__()
        self._auto_settings: AutoSettings = auto_settings
        self._force_open: Optional[bool] = None
        self._measurer_1_uri: Optional[str] = None
        self._measurer_2_uri: Optional[str] = None
        self._mux_uri: Optional[str] = None
        self._product_name: Optional[cw.ProductName] = None
        self._timer: QTimer = QTimer()
        self._timer.timeout.connect(self.check_connection)
        self._timer.setInterval(ConnectionChecker.TIMEOUT_MS)
        self._timer.setSingleShot(True)

    def _connect_devices(self, measurer_1_uri: Optional[str], measurer_2_uri: Optional[str], mux_uri: Optional[str],
                         product_name: Optional[cw.ProductName], error_report_required: Optional[bool] = False
                         ) -> ConnectionData:
        """
        :param measurer_1_uri: URI for the first IV-measurer;
        :param measurer_2_uri: URI for the second IV-measurer;
        :param mux_uri: URI for multiplexer;
        :param product_name: name of product to work with application.
        :param error_report_required: if True, then connection errors must be reported, otherwise errors are ignored.
        :return: an object with a created measurement system and product name.
        """

        measurers, bad_measurer_uris, bad_firmwares = self._create_measurers_by_force(measurer_1_uri, measurer_2_uri)
        mux, bad_mux_uris = create_multiplexer(mux_uri)

        if error_report_required:
            print_errors(*bad_measurer_uris, *bad_mux_uris)

        if not bad_measurer_uris and not bad_mux_uris and not bad_firmwares:
            if len(measurers) > 1:
                # Reorder measurers according to their addresses in USB hubs tree
                measurers = ut.sort_devices_by_usb_numbers(measurers)

            if len(measurers) > 0:
                for measurer, name in zip(measurers, ("test", "ref")):
                    measurer.name = name
                measurement_system = create_measurement_system(measurers, mux)
            else:
                measurement_system = None
            return ConnectionData(measurement_system, product_name)

        close_devices(*measurers, mux)
        return ConnectionData(None, product_name)

    def _connect_devices_in_background(self) -> bool:
        """
        :return: True if IV-measurers and multiplexer have been created to connect.
        """

        if not self._measurer_1_uri and not self._measurer_2_uri and not self._mux_uri:
            logger.debug("Checking the connection: no devices were connected to the application")
            return True

        connection_data = self._connect_devices(self._measurer_1_uri, self._measurer_2_uri, self._mux_uri,
                                                self._product_name)
        if connection_data.measurement_system:
            logger.debug("Checking the connection: device connection restored")
            self.connect_signal.emit(connection_data)
            return True

        logger.debug("Checking the connection: device connection not restored")
        return False

    def _create_measurers_by_force(self, *uris: str) -> Tuple[Optional[List[IVMeasurerBase]], List[str], bool]:
        """
        Method creates IV-measurers for the given list of URIs. If during creation it turns out that the IV-measurer
        has the wrong firmware, then you can create the IV-measurer anyway.
        :param uris: URIs for which to create IV-measurers.
        :return: list of IV-measurers created for a given list of URIs and list of URIs for which IV-measurers could
        not be created.
        """

        measurers, bad_uris, bad_firmwares_uris = create_measurers(*uris)
        if bad_firmwares_uris:
            if self._force_open is None:
                # In task #120535 it was decided to prohibit opening controllers with incompatible firmware
                for error_message in analyze_bad_firmwares(bad_firmwares_uris):
                    ut.show_message(qApp.translate("t", "Ошибка"), error_message)
                self._force_open = False

        return list(filter(lambda x: x is not None, measurers)), bad_uris, bool(bad_firmwares_uris)

    def _get_connection_params(self) -> None:
        """
        Method gets URI of the IV-measurers and multiplexer from auto settings.
        """

        def get_uri(uri_str: Optional[str] = None) -> Optional[str]:
            return None if not uri_str else uri_str

        connection_params = self._auto_settings.get_connection_params()
        product_name = cw.ProductName.get_product_name_by_string(connection_params.get("product_name", ""))
        uri_1 = get_uri(connection_params.get("measurer_1_port", None))
        uri_2 = get_uri(connection_params.get("measurer_2_port", None))
        (self._measurer_1_uri, self._measurer_2_uri), self._product_name = analyze_connection_params([uri_1, uri_2],
                                                                                                     product_name)
        self._mux_uri = get_uri(connection_params.get("mux_port", None))

    @pyqtSlot()
    def check_connection(self) -> None:
        if not self._connect_devices_in_background():
            self._timer.start()

    def connect_devices_by_user(self, measurer_1_uri: Optional[str], measurer_2_uri: Optional[str],
                                mux_uri: Optional[str], product_name: Optional[cw.ProductName]) -> ConnectionData:
        """
        :param measurer_1_uri: URI for the first IV-measurer;
        :param measurer_2_uri: URI for the second IV-measurer;
        :param mux_uri: URI for multiplexer;
        :param product_name: name of product to work with application.
        :return: an object with a created measurement system and product name.
        """

        self._force_open = None
        return self._connect_devices(measurer_1_uri, measurer_2_uri, mux_uri, product_name, True)

    def run_check(self) -> None:
        """
        Method starts checking the connection of IV-measurers and multiplexer.
        """

        self._get_connection_params()
        self._timer.start()

    def stop_check(self) -> None:
        """
        Method stops checking the connection of IV-measurers and multiplexer.
        """

        self._timer.stop()


def analyze_bad_firmwares(bad_firmwares_uris: List[Tuple[int, str, BadFirmwareVersion]]
                          ) -> Generator[str, None, None]:
    """
    :param bad_firmwares_uris:
    :return:
    """

    outdates_firmwares = []
    future_firmwares = []
    for _, uri, exc in bad_firmwares_uris:
        bad_firmware = get_major_and_minor_version_parts(exc.args[2])
        if bad_firmware < FIRST_FIRMWARE_WITH_BUTTONS:
            outdates_firmwares.append((uri, exc))
        elif FIRST_FIRMWARE_WITH_BUTTONS < bad_firmware:
            future_firmwares.append((uri, exc))

    if outdates_firmwares:
        yield create_text_for_outdated_firmwares(outdates_firmwares)

    if future_firmwares:
        yield create_text_for_future_firmwares(future_firmwares)


def analyze_connection_params(uris: List[Optional[str]], product_name: Optional[cw.ProductName] = None
                              ) -> Tuple[List[str], Optional[cw.ProductName]]:
    """
    :param uris: list of URIs for connecting measurers;
    :param product_name: suggested product name.
    :return: product name.
    """

    not_empty_uris = cw.utils.get_unique_uris(list(filter(bool, uris)))
    try:
        default_product_names = cw.ProductName.get_default_product_name_for_uris(not_empty_uris)
    except ValueError:
        default_product_names = []

    if default_product_names and product_name:
        for default_product_name in default_product_names:
            if cw.ProductName.check_replaceability(default_product_name, product_name):
                correct_product_name = product_name
                break
        else:
            correct_product_name = default_product_names[0]
    elif default_product_names and not product_name:
        correct_product_name = default_product_names[0]
    else:
        correct_product_name = None
        not_empty_uris = []

    while len(not_empty_uris) < 2:
        not_empty_uris.append(None)

    not_empty_uris = change_virtual_to_virtualasa_for_h10(not_empty_uris, correct_product_name)
    return not_empty_uris, correct_product_name


def change_virtual_to_virtualasa_for_h10(uris: List[Optional[str]], product_name: Optional[cw.ProductName]
                                         ) -> List[Optional[str]]:
    """
    :param uris: list of URIs for connecting measurers;
    :param product_name: product name for measurers.
    :return: corrected list of URIs.
    """

    if product_name == cw.ProductName.EYEPOINT_H10:
        for i, uri in enumerate(uris):
            if uri and uri.lower() == "virtual":
                uris[i] = "virtualasa"
    return uris


def close_devices(*devices: Union[IVMeasurerBase, AnalogMultiplexerBase]) -> None:
    """
    :param devices: list of devices to close.
    """

    for device in devices:
        if device is not None:
            try:
                device.close_device()
            except Exception as exc:
                logger.error("Error when closing device (%s)", exc)


def create_measurement_system(measurers: List[Optional[IVMeasurerBase]], mux: Optional[AnalogMultiplexerBase]
                              ) -> MeasurementSystem:
    """
    :param measurers: list of IV-measurers for the measurement system;
    :param mux: multiplexer for the measurement system.
    :return: created measurement system.
    """

    measurers_without_none = [measurer for measurer in measurers if measurer]
    multiplexers = [mux_ for mux_ in (mux, ) if mux_]
    return MeasurementSystem(measurers_without_none, multiplexers)


def create_measurer(uri: str, force_open: Optional[bool] = False, virtual_was: Optional[bool] = False
                    ) -> Optional[IVMeasurerBase]:
    """
    :param uri: URI to connect IV-measurer;
    :param force_open: if True, then the IV-measurer must be created even if the IV-measurer firmware is incorrect;
    :param virtual_was: if True, then the virtual IV-measurer has already been created earlier.
    :return: created IV-measurer.
    """

    uri_lower = uri.lower() if uri else uri
    if uri_lower == "virtual":
        measurer = IVMeasurerVirtual(uri_lower)
        if virtual_was:
            measurer.nominal = 1000
        return measurer

    if uri_lower == "virtualasa":
        return IVMeasurerVirtualASA(uri_lower, defer_open=True)

    if uri is not None and ("com:" in uri):
        dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(dir_name, "cur.ini")
        return IVMeasurerIVM(uri, config=config_file, defer_open=True, force_open=force_open)

    if uri is not None and "xmlrpc:" in uri:
        return IVMeasurerASA(uri, defer_open=True)

    return None


def create_measurers(*uris: str, force_open: Optional[bool] = False
                     ) -> Tuple[List[IVMeasurerBase], List[str], List[Tuple[int, str, BadFirmwareVersion]]]:
    """
    :param uris: URIs for which to create IV-measurers;
    :param force_open: if True, then the IV-measurer must be created even if the IV-measurer firmware is incorrect.
    :return: list of IV-measurers created for a given list of URIs, list of URIs for which IV-measurers could not be
    created and list of IV-measurer URIs with incorrect firmware.
    """

    measurers = []
    virtual_was = False
    bad_firmwares_uris = []
    bad_uris = []
    for i, uri in enumerate(uris):
        try:
            measurer = create_measurer(uri, force_open, virtual_was)
            if isinstance(measurer, IVMeasurerVirtual):
                virtual_was = True
        except BadFirmwareVersion as exc:
            logger.error("%s firmware version %s is not compatible with this version of EPLab", exc.args[0],
                         exc.args[2])
            bad_firmwares_uris.append((i, uri, exc))
            measurer = None
        except Exception as exc:
            logger.error("An error occurred when connecting the IV-measurer to the URI '%s': %s", uri, exc)
            bad_uris.append(uri)
            measurer = None

        measurers.append(measurer)
    return measurers, bad_uris, bad_firmwares_uris


def create_multiplexer(uri: Optional[str] = None) -> Tuple[Optional[AnalogMultiplexerBase], List[str]]:
    """
    :param uri: URI for multiplexer.
    :return: created multiplexer and list with bad URIs.
    """

    try:
        if uri == "virtual":
            return AnalogMultiplexerVirtual(uri, defer_open=True), []

        if uri is not None and "com:" in uri:
            mux = AnalogMultiplexer(uri)
            mux.close_device()
            return mux, []
    except Exception as exc:
        logger.error("Error when creating multiplexer (%s)", exc)
        return None, [uri]

    return None, []


def create_text_for_future_firmwares(firmwares: List[Tuple[str, BadFirmwareVersion]]) -> str:
    """
    :param firmwares: list with URI and BadFirmwareVersion errors when opening devices.
    :return: error message for firmware versions greater than 2.4.
    """

    future_firmwares_text = create_text_with_future_firmwares_list(firmwares)

    page_address = "https://eyepoint.physlab.ru/"
    link = get_link_in_set_language(page_address)
    hyper_link = f'<a href="{link}">{page_address}</a>'
    text = qApp.translate("t", "Скорее всего, вам нужно обновить программу EPLab. Свежую версию можно скачать на сайте "
                               "{link}.<br>\n"
                               "Если вы не хотите обновлять EPLab, вы можете установить на устройство более старую "
                               "прошивку. Для работы с данной версией EPLab подходят прошивки ivm 2.4.x, которые можно "
                               "скачать на сайте {link}.").format(link=hyper_link)
    firmware_update_text = get_firmware_update_info(hyper_link)

    return f"{future_firmwares_text}{text}<br>{firmware_update_text}"


def create_text_for_outdated_firmwares(firmwares: List[Tuple[str, BadFirmwareVersion]]) -> str:
    """
    :param firmwares: list with URI and BadFirmwareVersion errors when opening devices.
    :return: error message for firmware versions less than 2.4.
    """

    outdated_firmwares_text = create_text_with_outdated_firmwares_list(firmwares)

    page_address = "https://eyepoint.physlab.ru/"
    link = get_link_in_set_language(page_address)
    hyper_link = f'<a href="{link}">{link}</a>'
    text = qApp.translate("t", "Для работы с данной версией EPLab требуется прошивка ivm 2.4.x. Актуальную версию "
                               "прошивки можно скачать на сайте {link}.<br>\n"
                               "Если вы не хотите обновлять прошивку, воспользуйтесь более старой версией EPLab "
                               "(1.4.7), которую можно скачать с сайта {link}.").format(link=hyper_link)
    firmware_update_text = get_firmware_update_info(hyper_link)

    return f"{outdated_firmwares_text}{text}<br>{firmware_update_text}"


def create_text_with_firmwares_list_with_template(firmwares: List[Tuple[str, BadFirmwareVersion]], template: str
                                                  ) -> str:
    """
    :param firmwares: list with URI and BadFirmwareVersion errors when opening devices;
    :param template: template to create text with information about bad firmware.
    :return: text with a list of bad firmwares.
    """

    texts = []
    for uri, exc in firmwares:
        controller_name, _, firmware_version, serial_number, _ = exc.args
        text = template.format(uri=uri, name=controller_name, firmware=firmware_version, serial=serial_number)

        if len(firmwares) > 1:
            text = f"<li>{text}</li>"

        texts.append(text)

    if len(texts) == 1:
        return f"{texts[0]}<br>"

    return f"<ul>{''.join(texts)}</ul>"


def create_text_with_future_firmwares_list(firmwares: List[Tuple[str, BadFirmwareVersion]]) -> str:
    """
    :param firmwares: list with URI and BadFirmwareVersion errors when opening devices.
    :return: text with a list of bad firmwares that are older than 2.4.
    """

    template = qApp.translate("t", "На устройстве '{uri}' используется прошивка {firmware} измерителя {name}"
                                   " SN {serial}, которая является слишком новой для этой версии EPLab.")
    return create_text_with_firmwares_list_with_template(firmwares, template)


def create_text_with_outdated_firmwares_list(firmwares: List[Tuple[str, BadFirmwareVersion]]) -> str:
    """
    :param firmwares: list with URI and BadFirmwareVersion errors when opening devices.
    :return: text with a list of bad firmwares that are less than 2.4.
    """

    template = qApp.translate("t", "На устройстве '{uri}' используется устаревшая прошивка {firmware} измерителя {name}"
                                   " SN {serial}, которая несовместима с данной версией EPLab.")
    return create_text_with_firmwares_list_with_template(firmwares, template)


def get_firmware_update_info(link: str) -> str:
    """
    :param link: link to page.
    :return: text with information on how to update the firmware.
    """

    return qApp.translate("t", "Для обновления прошивки нужно воспользоваться программой epcboot_gui или epcboot. Их "
                               "также можно скачать с сайта {link} или найти на флешке, которая передавалась в "
                               "комплекте с устройством.<br>\n"
                               "Если используется двухканальное устройство, то в нем находится два измерителя. "
                               "Обновить прошивку нужно на обоих измерителях.").format(link=link)


def print_errors(*bad_uris: str) -> None:
    """
    :param bad_uris: list of URIs that could not be connected to.
    """

    if len(bad_uris) == 0:
        return

    if len(bad_uris) == 1:
        text = qApp.translate("t", "Не удалось подключиться к {}.\n<ul>\n"
                                   "<li>Проверьте, что устройство подключено к компьютеру и не удерживается другой "
                                   "программой.</li>\n"
                                   "<li>Убедитесь, что это устройство EyePoint, а не какое-то другое устройство.</li>\n"
                                   "</ul>")
    else:
        text = qApp.translate("t", "Не удалось подключиться к {}.\n<ul>\n"
                                   "<li>Проверьте, что устройства подключены к компьютеру и не удерживаются другой "
                                   "программой.</li>\n"
                                   "<li>Убедитесь, что это устройства EyePoint, а не какие-то другие устройства.</li>\n"
                                   "</ul>")
    ut.show_message(qApp.translate("t", "Ошибка подключения"), text.format(", ".join(bad_uris)))
