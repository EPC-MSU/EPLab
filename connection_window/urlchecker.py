import ipaddress
import re
from typing import Callable, Optional, Tuple, Union
from PyQt5.QtGui import QFocusEvent
from PyQt5.QtWidgets import QComboBox
import connection_window.utils as ut
from connection_window.productname import MeasurerType


class URLChecker:

    URL_BAD_COLOR: str = "#FFC0CB"

    def __init__(self, for_mux: bool = False) -> None:
        self._asa_reg_exp: str = r"^(xmlrpc://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|virtual)$"
        self._ivm10_reg_exp, self._mux_reg_exp = self._get_reg_exp_for_ivm10_and_mux()
        self._check_url: Callable[[str], bool] = None
        self._reg_exp = None

        if for_mux:
            self._reg_exp = re.compile(self._mux_reg_exp)
            self._check_url = self._check_ivm10_and_mux_url

    def _check_asa_url(self, url: str) -> bool:
        if not self._reg_exp.match(url):
            return False

        if url != "virtual":
            try:
                ipaddress.ip_address(url.replace("xmlrpc://", ""))
            except ValueError:
                return False
        return True

    def _check_ivm10_and_mux_url(self, url: str) -> bool:
        return bool(self._reg_exp.match(url))

    @staticmethod
    def _get_reg_exp_for_ivm10_and_mux() -> Tuple[str, str]:
        if ut.get_platform() == "debian":
            return r"^(com:///dev/ttyacm\d+|virtual)$", r"^(com:///dev/ttyacm\d+|virtual|none)$"
        return r"^(com:\\\\\.\\com\d+|virtual)$", r"^(com:\\\\\.\\com\d+|virtual|none)$"

    def check_url_for_correctness(self, url_or_widget: Union[str, QComboBox]) -> bool:
        """
        :param url_or_widget: widget with URL or URL to check for correct entry.
        :return: True if the URL matches the pattern.
        """

        url = url_or_widget.currentText() if isinstance(url_or_widget, QComboBox) else url_or_widget
        if self._check_url:
            return self._check_url(url.strip().lower())
        return True

    def color_widget(self, combo_box: QComboBox, event: Optional[QFocusEvent] = None) -> None:
        """
        :param combo_box:
        :param event:
        """

        if event and event.gotFocus():
            color = "white"
        else:
            color = "white" if self.check_url_for_correctness(combo_box) else URLChecker.URL_BAD_COLOR
        line_edit = combo_box.lineEdit()
        line_edit.setStyleSheet(f"background: {color};")

    def color_widgets(self, *combo_boxes: QComboBox) -> None:
        for combo_box in combo_boxes:
            self.color_widget(combo_box)

    def set_measurer_type(self, measurer_type: MeasurerType) -> None:
        if measurer_type == MeasurerType.IVM10:
            self._reg_exp = re.compile(self._ivm10_reg_exp)
            self._check_url = self._check_ivm10_and_mux_url
        else:
            self._reg_exp = re.compile(self._asa_reg_exp)
            self._check_url = self._check_asa_url
