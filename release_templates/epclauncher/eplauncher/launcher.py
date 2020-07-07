import configparser
import logging
from epclauncher.list_ports import list_ports, find_urpc_ports
from PyQt5.QtWidgets import QApplication
import sys


class LaunchInfo:
    """
    Class for main launch information.
    """
    def __init__(self,
                 template="",
                 pre_launch_command="",
                 command="",
                 num_devices="",
                 device_types=[],
                 device_urls=[]):
        self.template = template
        self.pre_launch_command = pre_launch_command
        self.command = command
        self.num_devices = num_devices
        self.device_types = device_types
        self.device_urls = device_urls


def get_command_from_file():
    """
    Read existing command file
    and read main launch command from this file
    """
    try:
        with open("launch_command.bat", "r") as f:
            lines = f.readlines()

        return lines[2]  # Warning! Not universal solution
    except Exception:
        # Maybe this is not the best solution
        return ""


def get_launch_info_from_config():
    """
    Fill LaunchInfo structure from config file.
    """
    config = configparser.ConfigParser()
    config.read("launch.ini")

    command_template = ""
    if str(config["Commands"]["launch_command"]) != "":
        command_template += str(config["Commands"]["launch_command"])
    if config["Commands"]["launch_file"] != "":
        if len(command_template) > 0:
            command_template += " "
        command_template += config["Commands"]["launch_file"]

    device_types = []
    for i in range(int(config["Commands"]["num_devices"])):
        if config["Commands"]["device_arg_" + str(i+1)] != "":
            command_template += " " + config["Commands"]["device_arg_" + str(i+1)]
        command_template += " " + "{device_url_" + str(i+1) + "}"
        device_types.append(config["Commands"]["device_type_" + str(i+1)])

    if config["Commands"]["additional_args"] != "":
        command_template += " " + config["Commands"]["additional_args"]

    logging.debug("Command template: " + command_template)

    launch_info = LaunchInfo(
        template=command_template,
        pre_launch_command=config["Commands"]["pre_launch_command"],
        command="",
        num_devices=int(config["Commands"]["num_devices"]),
        device_types=device_types
    )
    return launch_info


def get_device_urls_from_command(command, template):
    """
    Find in command device URL according to template,
    extract them and return as a list.
    """
    command_elements = command.split(" ")
    template_elements = template.split(" ")

    device_urls = []

    for i, element in enumerate(template_elements):
        if element[0] == "{":
            # TODO make more acurate search
            # We found url placeholder
            device_urls.append(command_elements[i])

    return device_urls


def command_is_valid(command, template):
    """
    Compare command structure with template.
    Return True if command structure (not URLs) is valid.
    Otherwise return False.
    """
    logging.info("Check command structure")
    command_elements = command.split(" ")
    template_elements = template.split(" ")

    if len(command_elements) != len(template_elements):
        logging.info("Command structure mismatch")
        logging.debug("Command: " + str(command_elements))
        logging.debug("Template: " + str(command_elements))
        return False

    for i, element in enumerate(template_elements):
        if len(element) < 1:
            # element is not URL placeholder
            return False

        if element[0] != "{":
            # element is not URL placeholder
            if element != command_elements[i]:
                logging.info("Element mismatch. Expected " + element + " got " + command_elements[i])
                return False

        return True


def check_device_urls(launch_info: LaunchInfo):
    """
    Check whether the URLs from list are valid for this PC:
    can be opened an have corresponding device types.
    """
    # Add device urls check here

    for i in range(launch_info.num_devices):
        try:
            urpc_ports = find_urpc_ports(launch_info.device_types[i])
        except Exception as e:
            logging.info("Cannot find ports for {}: {}.".format(launch_info.device_types[i], str(e)))
            return False

        urpc_ports.append("virtual")
        urpc_ports.append("none")

        try:
            url = launch_info.device_urls[i]
        except IndexError:
            logging.info("Not enough devices {} expected, got {}.".format(
                launch_info.num_devices,
                len(launch_info.device_urls)
            ))
            return False

        if url not in urpc_ports:
            logging.info("{} not found on local machine.".format(url))
            return False

    return True


def ask_for_device_urls(num_devices, device_types):
    """
    Ask user to choose devices to work
    """
    # TODO Here should be user friendly GUI
    device_urls = []

    app = QApplication(sys.argv)
    # TODO make list of valid urls
    url = list_ports(app, num_devices, device_types)
    device_urls.extend(url)

    return device_urls


def make_command_file(launch_info):
    """
    Create launch command file according to information
    from LaunchInfo structure.
    """
    device_urls_dict = {}
    for i, url in enumerate(launch_info.device_urls):
        device_urls_dict["device_url_" + str(i+1)] = url

    with open("launch_command.bat", "w") as f:
        f.write(":rem: This file is autogenerated\n")
        f.write(launch_info.pre_launch_command + "\n")
        f.write(launch_info.template.format(**device_urls_dict) + "\n")


def make_dummy_command_file(launch_info):
    """
    Create launch command file according to information
    from LaunchInfo structure.
    """
    with open("launch_command.bat", "w") as f:
        f.write(":rem: This file is autogenerated.\n")
        f.write(":rem: It is empty because ports were not set correctly.\n")
        f.write("@echo Devices were not set.\n")
        f.write("@echo Run launch.bat to set ports.\n")
