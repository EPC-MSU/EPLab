import json
import re
from operator import itemgetter
from platform import system
from typing import Dict, Iterable, List, Optional
import serial.tools.list_ports


def read_json(path: Optional[str] = None) -> Optional[Dict]:
    if not path:
        return None

    with open(path, "r") as file:
        return json.load(file)


def get_port(url) -> str:
    """
    Functions returns port name from URL.
    :return: port.
    """

    port = ""
    if system() == "Linux":
        port = re.findall(r"^com:///dev/(?P<port>.+)$", url)
    elif system() == "Windows":
        port = re.findall(r"^com:\\\\.\\(?P<port>.+)$", url)
    if not port:
        return None
    return port[0]


def find_address_in_usb_hubs_tree(url: str) -> str:
    """
    Function finds address of given URL in USB hubs tree.
    :param url: URL of device.
    :return: address of port in USB hubs tree or None if address was not found.
    """

    ports = list(serial.tools.list_ports.comports())
    port = get_port(url)
    if not port:
        return None
    for existing_port in ports:
        if port in existing_port.device:
            hub = re.findall(r"LOCATION=(?P<hub>.+)", existing_port.hwid)
            if not hub:
                raise ValueError("No hub found in " + existing_port.hwid)
            return hub[0]
    return None


def sort_devices_by_usb_numbers(measurers: Iterable, reverse: bool = False) -> List:
    """
    Function sorts devices by numbers in the USB hubs tree.
    :param measurers: list or tuple of sortable devices;
    :param reverse: if False devices will be sorted in ascending order.
    :return: sorted devices.
    """

    # Get addresses of devices in USB hubs tree
    addresses = []
    for measurer in measurers:
        address = find_address_in_usb_hubs_tree(measurer.url)
        if address is None:
            return measurers
        addresses.append((address, measurer))

    # Sort by addresses
    sorted_addresses = sorted(addresses, key=itemgetter(0), reverse=reverse)
    return [item[1] for item in sorted_addresses]
