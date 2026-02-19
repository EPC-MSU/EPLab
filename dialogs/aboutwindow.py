"""
File containing a dialog box class for displaying basic information about the application.
"""

import os
import re
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QLayout, QPushButton, QVBoxLayout
from connection_window.utils import get_platform
from version import Version
from window import utils as ut
from window.language import get_language, Language
from window.scaler import update_scale_of_class


@update_scale_of_class
class AboutWindow(QDialog):
    """
    Class for dialog window to show main information about the application.
    """

    WINDOW_WIDTH: int = 400

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__(main_window)
        self._init_ui()

    def _create_info_text(self) -> str:
        """
        :return: text with main information.
        """

        platform_name = {"debian": "Debian 64-bit",
                         "win32": "Windows 32-bit",
                         "win64": "Windows 64-bit"}
        app_name = f"<b>EPLab v{Version.full} ({platform_name[get_platform()]})</b><br><br>"
        text = qApp.translate("dialogs", "Программное обеспечение для работы с устройствами линейки EyePoint,"
                                         " предназначенными для поиска неисправностей на печатных платах в ручном "
                                         "режиме (при помощи ручных щупов). Более подробную информацию вы можете найти "
                                         "{}")
        link = '<a href="{}">{}</a>'.format(self._get_page_url(), qApp.translate("dialogs", "на нашем сайте."))
        text = app_name + text.format(link)
        return text.format(link)

    def _create_label_with_info(self) -> QLabel:
        """
        :return: label with main information text.
        """

        self.label_info: QLabel = QLabel(self._create_info_text())
        self.label_info.setOpenExternalLinks(True)
        self.label_info.setWordWrap(True)
        self.label_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                                Qt.TextInteractionFlag.LinksAccessibleByMouse)
        return self.label_info

    def _create_label_with_logo(self) -> QLabel:
        """
        :return: label with logo.
        """

        logo_name = self._get_logo_name()
        self.label_logo: QLabel = QLabel()
        self.label_logo.setText(f'<a href="{self._get_page_url()}"><img src="{os.path.join(ut.DIR_MEDIA, logo_name)}" '
                                f'width="{self.WINDOW_WIDTH}"></a>')
        self.label_logo.setOpenExternalLinks(True)
        return self.label_logo

    def _create_layout_with_buttons(self) -> QHBoxLayout:
        """
        :return: horizontal layout with copy and OK buttons.
        """

        self.button_copy: QPushButton = QPushButton()
        self.button_copy.setIcon(QIcon(os.path.join(ut.DIR_MEDIA, "copy.png")))
        self.button_copy.setToolTip(qApp.translate("dialogs", "Копировать"))
        self.button_copy.clicked.connect(self.copy_info)
        self.button_ok: QPushButton = QPushButton("OK")
        self.button_ok.clicked.connect(self.close)

        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(self.button_copy)
        h_layout.addWidget(self.button_ok)
        return h_layout

    def _get_logo_name(self) -> str:
        """
        :return: file name with logo.
        """

        return "logo.png" if get_language() is Language.RU else "logo_en.png"

    def _get_page_url(self) -> str:
        """
        :return: hyperlink to website.
        """

        page_url = "https://eyepoint.physlab.ru/"
        page_url += "ru/" if get_language() is Language.RU else "en/"
        return page_url

    def _init_ui(self) -> None:
        """
        Method initializes widgets on dialog window.
        """

        self.setWindowTitle(qApp.translate("MainWindow", "О программе"))
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setFixedWidth(self.WINDOW_WIDTH)

        layout = QVBoxLayout()
        layout.addWidget(self._create_label_with_logo())
        layout.addWidget(self._create_label_with_info())
        layout.addLayout(self._create_layout_with_buttons())
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.setLayout(layout)
        self.adjustSize()
        self.button_copy.setAutoDefault(False)
        self.button_ok.setAutoDefault(True)

    @staticmethod
    def _remove_tags(text: str) -> str:
        """
        :param text: source text with HTML tags.
        :return: text without HTML tags.
        """

        result = re.search(r'<a href="(?P<url>.*)">(?P<text>.*)\.</a>', text)
        text = text[:result.start()] + result.group("text") + f" ({result.group('url')})."

        tags_to_replace_with = {"<b>": "",
                                "</b>": "",
                                "<br>": "\n"}
        for tag, symbol in tags_to_replace_with.items():
            text = text.replace(tag, symbol)

        return text

    @pyqtSlot()
    def copy_info(self):
        """
        Slot copies information from dialog window.
        """

        app = qApp.instance()
        clipboard = app.clipboard()
        clipboard.setText(self._remove_tags(self.label_info.text()))


@ut.restore_ld_library_path
def show_product_info(main_window) -> None:
    """
    Function shows window with information about application.
    :param main_window: main window of application.
    """

    window = AboutWindow(main_window)
    window.exec()
