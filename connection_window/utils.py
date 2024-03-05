"""
File with useful functions.
"""

import configparser
import ipaddress
import logging
import os
import re
import select
import socket
import struct
from datetime import datetime, timedelta
from platform import system
from typing import List, Optional, Tuple
import psutil
import serial.tools.list_ports
import serial.tools.list_ports_common
from epcore.ivmeasurer import IVMeasurerVirtual, IVMeasurerVirtualASA
from connection_window.productname import MeasurerType


logger = logging.getLogger("eplab")
EXCLUSIVE_COM_PORT = {
    "debian": "com:///dev/ttyACMx",
    "win32": "com:\\\\.\\COMx",
    "win64": "com:\\\\.\\COMx"}
COM_PATTERN = {
    "debian": re.compile(r"^com:///dev/ttyACM\d+$"),
    "win32": re.compile(r"^com:\\\\\.\\COM\d+$"),
    "win64": re.compile(r"^com:\\\\\.\\COM\d+$")}


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
    :return: list of good COM-ports that can be used for IV-measurers and list of bad COM-ports.
    """

    from connection_window.urlchecker import check_port_name
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


def create_uri_name(com_port: str) -> str:
    """
    Function returns URI for port.
    :param com_port: COM-port.
    :return: URI.
    """

    os_name = get_platform()
    if "win" in os_name:
        return f"com:\\\\.\\{com_port}"
    if os_name == "debian":
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
            # VID or PID does not match or Hardware COM-port (not USB) without metainformation (VID and PID).
            # It is not our device. Skip it.
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


def get_current_measurers_ports(main_window) -> List[str]:
    """
    :param main_window: main window of application.
    :return: list of measurer ports that the application currently works with.
    """

    ports = [None, None]
    for i_measurer, measurer in enumerate(main_window.get_measurers()):
        if measurer.url:
            ports[i_measurer] = measurer.url
        elif isinstance(measurer, IVMeasurerVirtualASA):
            ports[i_measurer] = MeasurerType.ASA_VIRTUAL.value
        elif isinstance(measurer, IVMeasurerVirtual):
            ports[i_measurer] = MeasurerType.IVM10_VIRTUAL.value
    return ports


def get_different_urls(urls: List[str]) -> List[str]:
    """
    Function returns only different real URLs in list of URLs.
    :param urls: initial list of URLs.
    :return: list with different real URLs.
    """

    different_urls = []
    for url in urls:
        if url is None:
            continue

        if url.lower() == "virtual":
            different_urls.append(url)
            continue

        for registered_url in different_urls:
            if get_platform() == "debian":
                registered_url_cmp = registered_url
                url_cmp = url
            else:
                registered_url_cmp = registered_url.lower()
                url_cmp = url.lower()

            if registered_url_cmp == url_cmp:
                break
        else:
            different_urls.append(url)
    return different_urls


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
        return "debian"

    raise RuntimeError("Unexpected OS")


def reveal_asa(timeout: float = None) -> List[ipaddress.IPv4Address]:
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
                                ip_addresses.append(ipaddress.ip_address(str(addr[0])))
            except Exception as exc:
                logger.error("Failed to bind to interface %s and address %s: %s", iface_name, address.address, exc)
    return ip_addresses
