"""
File with class for dialog window to show main information about application.
"""

import os
import platform
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon, QPalette, QPixmap
from PyQt5.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton, QTextBrowser, QVBoxLayout
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
        dir_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
        self.setWindowIcon(QIcon(os.path.join(dir_name, "ico.png")))
        color = self.palette().color(QPalette.Background)
        self.label_logo: QLabel = QLabel()
        self.label_logo.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(os.path.join(dir_name, "logo.png"))
        pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio)
        self.label_logo.setPixmap(pixmap)
        text = qApp.translate("t", "Программное обеспечение для работы с устройствами линейки EyePoint,"
                                   " предназначенными для поиска неисправностей на печатных платах в ручном режиме "
                                   "(при помощи ручных щупов). Более подробную информацию вы можете найти {}")
        page_url = "https://eyepoint.physlab.ru/"
        if qApp.instance().property("language") is Language.RU:
            page_url += "ru/"
        else:
            page_url += "en/"
        link = '<a href="{}">{}</a>'.format(page_url, qApp.translate("t", "на нашем сайте."))
        self.text_edit_info: QTextBrowser = QTextBrowser()
        self.text_edit_info.setFrameStyle(QFrame.NoFrame)
        self.text_edit_info.setStyleSheet(f"background: {color.name()}")
        self.text_edit_info.setOpenExternalLinks(True)
        self.text_edit_info.setHtml(text.format(link))
        width = 300 if platform.system().lower() == "windows" else 400
        self.text_edit_info.setFixedSize(width, pixmap.height())
        h_layout_1 = QHBoxLayout()
        h_layout_1.addWidget(self.label_logo)
        h_layout_1.addWidget(self.text_edit_info)
        self.button_ok: QPushButton = QPushButton("OK")
        self.button_ok.clicked.connect(self.close)
        h_layout_2 = QHBoxLayout()
        h_layout_2.addStretch(1)
        h_layout_2.addWidget(self.button_ok)
        layout = QVBoxLayout()
        layout.addLayout(h_layout_1)
        layout.addLayout(h_layout_2)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)
