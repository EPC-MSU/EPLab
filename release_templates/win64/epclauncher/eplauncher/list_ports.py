import epclauncher.safe_opener as safe_opener
import epclauncher.urpcbase as lib
import sys
import serial.tools.list_ports
import serial
import logging
import configparser
from typing import List
from PyQt5.QtWidgets import QComboBox, QApplication, QPushButton, QMainWindow,\
    QErrorMessage, QLabel


def _get_active_serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """

    ports = serial.tools.list_ports.comports()
    valid_ports = []
    for port in sorted(ports):
        try:
            s = serial.Serial(port.device)
            s.close()
            valid_ports.append(port)
        except (OSError, serial.SerialException):
            pass
    return valid_ports


def _filter_ports_by_vid_and_pid(ports: List, vid: str, pid: str):
    """
    Return a list of ports with specified vid and pid from given list
    ports - a list of serial ports, obtained by serial.tools.list_ports
    vid   - desired vid as a hex string (example: "1CBC")
    pid   - desired vid as a hex string (example: "0007")
    """
    filtered_ports = []

    for port in ports:
        try:
            # Normal hwid string example:
            # USB VID:PID=1CBC:0007 SER=7 LOCATION=1-4.1.1:x.0
            p_vid_pid_info_block = port.hwid.split(" ")[1]
            p_vid_pid = p_vid_pid_info_block.split("=")[1]
            p_vid, p_pid = p_vid_pid.split(":")
            if p_vid == vid and p_pid == pid:
                filtered_ports.append(port)
        except Exception:
            # Some ports can have malformed information.
            # We should simply ignore such devices.
            continue
    return filtered_ports


def find_urpc_ports(dev_type):
    """
    This function return available com-ports for connect
    :return: list of com-ports
    """

    config = configparser.ConfigParser()
    config_name = "{}_config.ini".format(dev_type)
    try:
        config.read(config_name)
    except Exception:
        logging.error("Cannot open {}".format(config_name))
        raise

    try:
        vid = config["Global"]["vid"]
        pid = config["Global"]["pid"]
    except Exception:
        logging.error("Cannot read 'vid' and 'pid' fields from {}".format(config_name))
    serial_ports = _get_active_serial_ports()
    serial_ports = _filter_ports_by_vid_and_pid(serial_ports, vid, pid)
    ximc_ports = []
    for port in serial_ports:
        device_name = "com:\\\\.\\{}".format(port.device)
        device = lib.UrpcbaseDeviceHandle(device_name.encode())
        if device._handle is not None:
            device.close()
        try:
            safe_opener.open_device_safe(device, "{}_config.ini".format(dev_type), lib._logging_callback)
            ximc_ports.append(device_name)
        except RuntimeError:
            logging.error("{} is not XIMC controller".format(device_name))
        device.close()
    return ximc_ports


class Window(QMainWindow):
    """
    This class show window with checklist of com-ports
    """
    def __init__(self, n_dev, dev_types):
        super().__init__()
        self.cb = []
        self.check_list = []
        self.n_dev = n_dev
        self.dev_types = dev_types
        self.initUI()

    def initUI(self):
        self.info_label = QLabel(self)
        self.info_label.setText("Выберите устройства.\n"
                                "Если Вы хотите использовать\n"
                                "не все устройства, для неиспользуемых\n"
                                "устройств выберите 'none'.")
        self.info_label.move(20, 15)
        self.info_label.resize(210, 50)

        for i in range(self.n_dev):
            try:
                self.urpc_ports = find_urpc_ports(self.dev_types[i])
            except Exception as e:
                error_dialog = QErrorMessage()
                error_dialog.showMessage(str(e))
            self.urpc_ports.append("virtual")
            self.urpc_ports.append("none")
            self.cb.append(QComboBox(self))
            self.cb[i].addItems(self.urpc_ports)
            self.cb[i].move(20, 80 + 40 * i)
            self.cb[i].resize(210, 30)
            if self.cb[i].count() >= i:
                self.cb[i].setCurrentIndex(i)
        button = QPushButton("Далее", self)
        button.move(20, 80 + 40 * len(self.cb))
        button.clicked.connect(self._ok_button)

        self.setWindowTitle("EPC Launcher 0.1.4")
        self.setGeometry(300, 300, 250, 120 + 40 * len(self.cb))
        self.show()

    def _ok_button(self):
        for dev in self.cb:
            self.check_list.append(dev.currentText())
        self.close()


def list_ports(app, n_dev, dev_types):
    """
    main function, which call find_ivm_ports and open qwindow
    :param app: QApplication
    :return: list of com-ports
    """
    ex = Window(n_dev, dev_types)
    app.exec_()
    return ex.check_list


if __name__ == "__main__":
    app = QApplication(sys.argv)