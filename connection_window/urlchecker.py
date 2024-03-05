import ipaddress
import re
from typing import Callable, Optional, Union
from PyQt5.QtGui import QFocusEvent
from PyQt5.QtWidgets import QComboBox
import connection_window.utils as ut
from connection_window.productname import MeasurerType


def get_reg_exp_for_ivm10():
    """
    :return: regular expression for IVM10 measurer URL.
    """

    if ut.get_platform() == "debian":
        return re.compile(r"^(com:///dev/tty.*|(?i)virtual)$")
    return re.compile(r"^(?i)(com:\\\\\.\\COM\d+|virtual)$")


def get_reg_exp_for_mux():
    """
    :return: regular expression for multiplexer URL.
    """

    if ut.get_platform() == "debian":
        return re.compile(r"^(com:///dev/tty.*|(?i)virtual|(?i)none)$")
    return re.compile(r"^(?i)(com:\\\\\.\\COM\d+|virtual|none)$")


class URLChecker:
    """
    Class checks that the URL for the IV-measurer and multiplexer is correct.
    """

    ASA_REG_EXP = re.compile(r"^(?i)(xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|virtual(asa)?)$")
    IVM10_REG_EXP = get_reg_exp_for_ivm10()
    MUX_REG_EXP = get_reg_exp_for_mux()
    URL_BAD_COLOR: str = "#FFC0CB"

    def __init__(self, for_mux: bool = False) -> None:
        """
        :param for_mux: if True, then need to check the URL for the multiplexer, otherwise for the IV-measurer.
        """

        self._check_url: Callable[[str], bool] = None
        if for_mux:
            self._check_url = self.check_mux

    @classmethod
    def check_mux(cls, url: str) -> bool:
        """
        :param url: URL of the multiplexer to be checked for correctness.
        :return: True if the URL is valid.
        """

        return bool(cls.MUX_REG_EXP.match(url))

    @classmethod
    def check_asa(cls, url: str) -> bool:
        """
        :param url: URL of the ASA IV-measurer that needs to be checked for correctness.
        :return: True if the URL is valid.
        """

        if not cls.ASA_REG_EXP.match(url):
            return False

        url = url.lower()
        if url not in ("virtual", "virtualasa"):
            try:
                ipaddress.ip_address(url.replace("xmlrpc://", ""))
            except ValueError:
                return False
        return True

    @classmethod
    def check_ivm10(cls, url: str) -> bool:
        """
        :param url: URL of the IV-measurer or multiplexer to be checked for correctness.
        :return: True if the URL is valid.
        """

        return bool(cls.IVM10_REG_EXP.match(url))

    def check_url_for_correctness(self, url_or_widget: Union[str, QComboBox]) -> bool:
        """
        :param url_or_widget: widget with URL or URL to check for correct entry.
        :return: True if the URL is valid.
        """

        url = url_or_widget.currentText() if isinstance(url_or_widget, QComboBox) else url_or_widget
        if self._check_url:
            return self._check_url(url.strip())
        return True

    def color_widget(self, combo_box: QComboBox, event: Optional[QFocusEvent] = None) -> None:
        """
        :param combo_box: widget that needs to be colored depending on the correctness of the entered URL;
        :param event: focus event.
        """

        if event and event.gotFocus():
            color = "white"
        else:
            color = "white" if self.check_url_for_correctness(combo_box) else URLChecker.URL_BAD_COLOR
        line_edit = combo_box.lineEdit()
        line_edit.setStyleSheet(f"background: {color};")

    def color_widgets(self, *combo_boxes: QComboBox) -> None:
        """
        :param combo_boxes: widgets that needs to be colored depending on the correctness of the entered URL.
        """

        for combo_box in combo_boxes:
            self.color_widget(combo_box)

    def set_measurer_type(self, measurer_type: MeasurerType) -> None:
        """
        :param measurer_type: the type of IV-measurer for which the URL needs to be checked.
        """

        self._check_url = self.check_ivm10 if measurer_type == MeasurerType.IVM10 else self.check_asa


def check_port_name(port: str) -> bool:
    """
    Function checks that port name is correct.
    :param port: port name.
    :return: True if port name is correct.
    """

    if port is None:
        return True

    if URLChecker.check_ivm10(port) or URLChecker.check_asa(port):
        return True
    return False
