"""
File with useful functions.
"""

import configparser
import logging
import os
import re
import select
import socket
import struct
from datetime import datetime, timedelta
from enum import Enum
from platform import system
from typing import List, Optional, Tuple
import psutil
import serial.tools.list_ports
import serial.tools.list_ports_common
from epcore.ivmeasurer import IVMeasurerASA, IVMeasurerIVM10, IVMeasurerVirtual, IVMeasurerVirtualASA

logger = logging.getLogger("eplab")
DIR_MEDIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
EXCLUSIVE_COM_PORT = {
    "linux": "com:///dev/ttyACMx",
    "win32": "com:\\\\.\\COMx",
    "win64": "com:\\\\.\\COMx"}
COM_PATTERN = {
    "linux": re.compile(r"^com:///dev/ttyACM\d+$"),
    "win32": re.compile(r"^com:\\\\\.\\COM\d+$"),
    "win64": re.compile(r"^com:\\\\\.\\COM\d+$")}
IVM10_PATTERN = {
    "linux": re.compile(r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:///dev/ttyACM\d+|virtual)$"),
    "win32": re.compile(r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:\\\\\.\\COM\d+|virtual)$"),
    "win64": re.compile(r"^(xi-net://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+|com:\\\\\.\\COM\d+|virtual)$")}
IVMASA_PATTERN = {
    "linux": re.compile(r"^(xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|virtual(asa)?)$"),
    "win32": re.compile(r"^(xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|virtual(asa)?)$"),
    "win64": re.compile(r"^(xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|virtual(asa)?)$")}
MUX_PATTERN = {
    "linux": re.compile(r"^(com:///dev/ttyACM\d+|virtual)$"),
    "win32": re.compile(r"^(com:\\\\\.\\COM\d+|virtual)$"),
    "win64": re.compile(r"^(com:\\\\\.\\COM\d+|virtual)$")}


class ProductNames(Enum):
    """
    Class with names of available products for application.
    """

    EYEPOINT_A2 = "EyePoint a2"
    EYEPOINT_H10 = "EyePoint H10"
    EYEPOINT_S2 = "EyePoint S2"
    EYEPOINT_U21 = "EyePoint u21"
    EYEPOINT_U22 = "EyePoint u22"

    @classmethod
    def get_default_product_name_for_measurers(cls, measurers: List) -> Optional["ProductNames"]:
        """
        Method returns default name of product for given measurers.
        :param measurers: measurers.
        :return: name of product.
        """

        product_name = None
        for measurer in measurers:
            if isinstance(measurer, (IVMeasurerASA, IVMeasurerVirtualASA)) and product_name in (None, cls.EYEPOINT_H10):
                product_name = cls.EYEPOINT_H10
            elif (isinstance(measurer, (IVMeasurerIVM10, IVMeasurerVirtual)) and
                  product_name in (None, cls.EYEPOINT_A2)):
                product_name = cls.EYEPOINT_A2
            else:
                raise ValueError("Unknown default name of product")
        return product_name

    @classmethod
    def get_measurer_type_by_product_name(cls, product_name: "ProductNames") -> Optional["MeasurerType"]:
        """
        Method returns type of measurer by name of product.
        :param product_name: name of product.
        :return: type of measurer.
        """

        if product_name == cls.EYEPOINT_H10:
            return MeasurerType.ASA
        if product_name in (cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_U22, cls.EYEPOINT_S2):
            return MeasurerType.IVM10
        return None

    @classmethod
    def get_product_names_for_platform(cls) -> List["ProductNames"]:
        """
        Method returns names of products for platform of system.
        :return: names of products.
        """

        products = [cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_U22, cls.EYEPOINT_S2]
        if get_platform() != "win64":
            products.append(cls.EYEPOINT_H10)
        return products

    @classmethod
    def get_single_channel_products(cls) -> Tuple:
        """
        Method returns names of products with single channel (measurer).
        :return: names of products.
        """

        return cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_H10


class MeasurerType(Enum):
    """
    Class with types of measurers.
    """

    ASA = "ASA"
    ASA_VIRTUAL = "virtualasa"
    IVM10 = "IVM10"
    IVM10_VIRTUAL = "virtual"


def check_com_port(com_port: str) -> bool:
    """
    Function checks that given COM-port can be used for IV-measurer.
    :param com_port: COM-port to check.
    :return: True if COM-port can be used.
    """

    available_ports_in_required_format = [create_uri_name(port.device) for port in serial.tools.list_ports.comports()]
    if com_port not in available_ports_in_required_format:
        raise ValueError(f"COM-port {com_port} was not found in system")
    return True


def check_com_ports(com_ports: List[str]) -> Tuple[List[str], List[str]]:
    """
    Function checks that given COM-ports can be used for IV-measurer.
    :param com_ports: list of COM-ports.
    :return: list of good COM-ports that can be used for IV-measurers and
    list of bad COM-ports.
    """

    bad_com_ports = []
    good_com_ports = []
    for com_port in com_ports:
        if not check_port_name(com_port):
            bad_com_ports.append(com_port)
            good_com_ports.append(None)
        elif com_port is not None and COM_PATTERN[get_platform()].match(com_port) and com_port != "virtual":
            try:
                check_com_port(com_port)
                good_com_ports.append(com_port)
            except ValueError:
                bad_com_ports.append(com_port)
                good_com_ports.append(None)
        else:
            good_com_ports.append(com_port)
    while True:
        try:
            bad_com_ports.remove(EXCLUSIVE_COM_PORT[get_platform()])
            logger.info("Wildcard name com:\\\\.\\COMx passed that is not a real device. If you need to open a real "
                        "device, then instead of com:\\\\.\\COMx you need to enter the real port name")
        except ValueError:
            break
    return good_com_ports, bad_com_ports


def check_port_name(port: str) -> bool:
    """
    Function checks that port name is correct.
    :param port: port name.
    :return: True if port name is correct.
    """

    platform_name = get_platform()
    if port is None:
        return True
    if IVM10_PATTERN[platform_name].match(port) or IVMASA_PATTERN[platform_name].match(port) or\
            MUX_PATTERN[platform_name].match(port):
        return True
    return False


def create_uri_name(com_port: str) -> str:
    """
    Function returns URI for port.
    :param com_port: COM-port.
    :return: URI.
    """

    os_name = get_platform()
    if "win" in os_name:
        return f"com:\\\\.\\{com_port}"
    if os_name == "linux":
        return f"com://{com_port}"
    raise RuntimeError("Unexpected OS")


def filter_ports_by_vid_and_pid(com_ports: List[serial.tools.list_ports_common.ListPortInfo], vid: int, pid: int
                                ) -> List[serial.tools.list_ports_common.ListPortInfo]:
    """
    Function returns list of COM-ports with specified VID and PID from given list.
    :param com_ports: list of serial ports;
    :param vid: desired VID;
    :param pid: desired PID.
    :return: list of ports.
    """

    filtered_ports = []
    for com_port in com_ports:
        if com_port.vid == vid and com_port.pid == pid:
            filtered_ports.append(com_port)
        else:
            # Hardware COM-port (not USB) without metainformation. It is not our device
            pass
    return filtered_ports


def find_urpc_ports(device_type: str) -> List[str]:
    """
    Function returns available COM-ports to connect.
    :param device_type: type of device that is connected to port.
    :return: list of available COM-ports.
    """

    os_name = get_platform()
    dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_file = os.path.join(dir_name, "resources", os_name, f"{device_type}_config.ini")
    config = configparser.ConfigParser()
    try:
        config.read(config_file)
    except Exception as exc:
        logger.error("Cannot open '%s': %s", config_file, exc)
        raise
    try:
        vid = int(config["Global"]["vid"], base=16)
        pid = int(config["Global"]["pid"], base=16)
    except Exception as exc:
        logger.error("Cannot read 'VID' and 'PID' fields from '%s': %s", config_file, exc)
        raise
    serial_ports = serial.tools.list_ports.comports()
    serial_ports = filter_ports_by_vid_and_pid(serial_ports, vid, pid)
    return sorted([create_uri_name(serial_port.device) for serial_port in serial_ports])


def get_different_ports(ports: List[str]) -> List[str]:
    """
    Function returns only different real ports in list of ports.
    :param ports: initial list of ports.
    :return: ports.
    """

    different_ports = []
    for port in ports:
        if port == "virtual" or port not in different_ports:
            different_ports.append(port)
    return different_ports


def get_platform() -> Optional[str]:
    """
    Function returns name of OS.
    :return: name of OS.
    """

    os_kind = system().lower()
    if os_kind == "windows":
        if 8 * struct.calcsize("P") == 32:
            return "win32"
        return "win64"
    if os_kind == "linux":
        return "linux"
    raise RuntimeError("Unexpected OS")


def reveal_asa(timeout: float = None) -> List[str]:
    """
    Function detects ASA in the local network.
    :param timeout: max waiting time for responses from ASA.
    :return: list of IP addresses.
    """

    waiting_time = 0.1
    if timeout is None:
        timeout = waiting_time
    timeout = timedelta(seconds=timeout)
    ifaces = psutil.net_if_addrs()
    ip_addresses = []
    for iface_name, iface in ifaces.items():
        iface_name = iface_name.encode(errors="replace").decode(errors="replace")
        for address in iface:
            if address.family != socket.AF_INET:
                continue
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.bind((address.address, 0))
                    sock.sendto(("DISCOVER_CUBIELORD_REQUEST " + str(sock.getsockname()[1])).encode(),
                                ("255.255.255.255", 8008))
                    sock.setblocking(0)
                    time_end = datetime.utcnow() + timeout
                    while True:
                        time_now = datetime.utcnow()
                        time_left = (time_end - time_now).total_seconds()
                        if time_left < 0:
                            break
                        ready = select.select([sock], [], [], time_left)
                        if ready[0]:
                            data, addr = sock.recvfrom(4096)
                            if data.startswith("DISCOVER_CUBIELORD_RESPONSE ".encode()):
                                ip_addresses.append(str(addr[0]))
            except Exception as exc:
                logger.error("Failed to bind to interface %s and address %s: %s", iface_name, address.address, exc)
    return ip_addresses
