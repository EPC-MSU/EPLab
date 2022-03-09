"""
File with class for dialog window to show main information about application.
"""

import os
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtGui import QIcon, QPalette
from PyQt5.QtWidgets import QDialog, QFrame, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout
from language import Language


class AboutWindow(QDialog):
    """
    Class for dialog window to show main information about application.
    """

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        """
        Method initializes widgets on dialog window.
        """

        self.setWindowTitle(qApp.translate("t", "О программе"))
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media", "ico.png")
        self.setWindowIcon(QIcon(icon_path))
        color = self.palette().color(QPalette.Background)
        text = qApp.translate("t", "Программное обеспечение для работы с устройствами линейки EyePoint,"
                                   " предназначенными для поиска неисправностей на печатных платах в ручном режиме "
                                   "(при помощи ручных щупов). Более подробную информацию вы можете найти "
                                   '<a href="{}">на нашем сайте</a>')
        self.text_edit_info = QTextBrowser()
        self.text_edit_info.setFrameStyle(QFrame.NoFrame)
        self.text_edit_info.setStyleSheet(f"background: {color.name()}")
        self.text_edit_info.setOpenExternalLinks(True)
        page_url = "https://eyepoint.physlab.ru/"
        if qApp.instance().property("language") is Language.RU:
            page_url += "ru/"
        else:
            page_url += "en/"
        self.text_edit_info.setHtml(text.format(page_url))
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit_info)
        self.button_ok = QPushButton("OK")
        self.button_ok.clicked.connect(self.close)
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(self.button_ok)
        layout.addLayout(h_layout)
        self.setLayout(layout)
