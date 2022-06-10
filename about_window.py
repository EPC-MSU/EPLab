"""
File with class for dialog window to show main information about application.
"""

import os
from typing import Tuple
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp
from PyQt5.QtGui import QIcon, QPalette
from PyQt5.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton, QTextBrowser, QVBoxLayout
import utils as ut
from language import Language

TEXT_HEIGHT: int = 100
WINDOW_WIDTH: int = 400


class AboutWindow(QDialog):
    """
    Class for dialog window to show main information about application.
    """

    def __init__(self):
        super().__init__()
        self._init_ui()

    @staticmethod
    def _create_info_text_and_link() -> Tuple[str, str]:
        """
        Method creates text with main information and hyperlink to website.
        :return: text with main information and hyperlink.
        """

        text = qApp.translate("t", "Программное обеспечение для работы с устройствами линейки EyePoint,"
                                   " предназначенными для поиска неисправностей на печатных платах в ручном режиме "
                                   "(при помощи ручных щупов). Более подробную информацию вы можете найти {}")
        page_url = "https://eyepoint.physlab.ru/"
        if qApp.instance().property("language") is Language.RU:
            page_url += "ru/"
        else:
            page_url += "en/"
        link = '<a href="{}">{}</a>'.format(page_url, qApp.translate("t", "на нашем сайте."))
        return text.format(link), page_url

    @staticmethod
    def _get_logo_name() -> str:
        """
        Method returns file name with logo.
        :return: file name with logo.
        """

        return "logo.png" if qApp.instance().property("language") is Language.RU else "logo_en.png"

    def _init_ui(self):
        """
        Method initializes widgets on dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "О программе"))
        self.setToolTip(qApp.translate("t", "О программе"))
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "ico.png")))
        self.setFixedWidth(WINDOW_WIDTH)
        color = self.palette().color(QPalette.Background)
        text, page_url = self._create_info_text_and_link()
        logo_name = self._get_logo_name()
        self.label_logo = QLabel()
        self.label_logo.setText(f'<a href="{page_url}"><img src="{os.path.join(ut.DIR_MEDIA, logo_name)}" '
                                f'width="{WINDOW_WIDTH}"></a>')
        self.label_logo.setOpenExternalLinks(True)
        self.text_edit_info: QTextBrowser = QTextBrowser()
        self.text_edit_info.setFrameStyle(QFrame.NoFrame)
        self.text_edit_info.setStyleSheet(f"background: {color.name()}")
        self.text_edit_info.setOpenExternalLinks(True)
        self.text_edit_info.setHtml(text)
        self.text_edit_info.setFixedSize(WINDOW_WIDTH, TEXT_HEIGHT)
        self.button_copy: QPushButton = QPushButton()
        self.button_copy.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "copy.png")))
        self.button_copy.setToolTip(qApp.translate("t", "Копировать"))
        self.button_copy.clicked.connect(self.copy_info)
        self.button_ok: QPushButton = QPushButton("OK")
        self.button_ok.setDefault(True)
        self.button_ok.setToolTip("OK")
        self.button_ok.clicked.connect(self.close)
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(self.button_copy)
        h_layout.addWidget(self.button_ok)
        layout = QVBoxLayout()
        layout.addWidget(self.label_logo)
        layout.addWidget(self.text_edit_info)
        layout.addLayout(h_layout)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)
        self.adjustSize()

    @pyqtSlot()
    def copy_info(self):
        """
        Slot copies information from dialog window.
        """

        app = qApp.instance()
        clipboard = app.clipboard()
        clipboard.setText(self.text_edit_info.toPlainText())


def show_product_info():
    """
    Function shows window with information about application.
    """

    window = AboutWindow()
    window.exec_()
