"""
File with useful functions.
"""

import configparser
import ipaddress
import logging
import os
import select
import socket
import struct
from datetime import datetime, timedelta
from platform import system
from typing import List, Optional
import psutil
import serial.tools.list_ports
import serial.tools.list_ports_common
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel
from epcore.ivmeasurer import IVMeasurerVirtual, IVMeasurerVirtualASA
from .productname import MeasurerType


logger = logging.getLogger("eplab")


def create_label_with_image(image_path: str, image_width: int, image_height: int) -> QLabel:
    """
    :param image_path: path to the image file;
    :param image_width: desired image width;
    :param image_height: desired image height.
    :return: label with image.
    """

    pixmap = QPixmap(image_path)
    height_factor = image_height / pixmap.height()
    width_factor = image_width / pixmap.width()
    factor = min(height_factor, width_factor)
    label = QLabel("")
    label.setPixmap(pixmap)
    label.setScaledContents(True)
    label.setFixedSize(int(factor * pixmap.width()), int(factor * pixmap.height()))
    return label


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

    def check_vid_and_pid(port: serial.tools.list_ports_common.ListPortInfo) -> bool:
        return port.vid == vid and port.pid == pid

    return list(filter(check_vid_and_pid, com_ports))


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
    return sorted(map(lambda port: create_uri_name(port.device), serial_ports))


def get_current_measurers_uris(main_window) -> List[str]:
    """
    :param main_window: main window of application.
    :return: list of measurer URIs that the application currently works with.
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


def get_different_uris(uris: List[str]) -> List[str]:
    """
    Function returns only different real URIs in list of URIs.
    :param uris: initial list of URIs.
    :return: list with different real URIs.
    """

    os_name = get_platform()
    different_uris = []
    for uri in uris:
        if uri is None:
            continue

        if uri.lower() == "virtual":
            different_uris.append(uri)
            continue

        for registered_uri in different_uris:
            if os_name == "debian":
                registered_uri_cmp = registered_uri
                uri_cmp = uri
            else:
                registered_uri_cmp = registered_uri.lower()
                uri_cmp = uri.lower()

            if registered_uri_cmp == uri_cmp:
                break
        else:
            different_uris.append(uri)
    return different_uris


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


def get_unique_uris(uris: List[Optional[str]]) -> List[Optional[str]]:
    """
    :param uris:
    :return:
    """

    os_name = get_platform()
    unique_uris = []
    unique_uris_cmp = []
    for uri in uris:
        if os_name != "debian" or (uri and uri.lower() == "virtual"):
            uri_cmp = uri.lower()
        else:
            uri_cmp = uri

        if uri_cmp == "virtual" or uri_cmp not in unique_uris_cmp:
            unique_uris.append(uri)
            unique_uris_cmp.append(uri_cmp)

    return unique_uris


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
