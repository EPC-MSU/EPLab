"""
File with dialog box class that displays the keyboard shortcuts used in the application.
"""

import os
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon, QPalette
from PyQt5.QtWidgets import QDialog, QFrame, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout
from window import utils as ut
from window.scaler import update_scale_of_class


@update_scale_of_class
class KeymapDialog(QDialog):
    """
    Dialog box class that displays the keyboard shortcuts used in the application.
    """

    HEIGHT: int = 410
    WIDTH: int = 280

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self._main_window = main_window
        self._init_ui()

    def _create_text_browser(self) -> QTextBrowser:
        """
        :return: text browser.
        """

        color = self.palette().color(QPalette.Background)
        text_browser = QTextBrowser()
        text_browser.setStyleSheet(f"background: {color.name()};")
        text_browser.setFrameStyle(QFrame.NoFrame)
        text_browser.setHtml(self._get_text())
        return text_browser

    def _get_text(self) -> str:
        """
        :return: text describing the keyboard shortcuts used in the application.
        """

        style = ("<style>"
                 "table {width: 100%; border: none; border-collapse: collapse; margin-bottom: 20px;}"
                 "table td {padding: 10px; line-height: 20px; color: #444441; border-bottom: 1px solid #716561; "
                 "border-top: 1px solid #716561;}"
                 "</style>")
        key_map = [("Ctrl+N", qApp.translate("MainWindow", "Создать план тестирования")),
                   ("Ctrl+O", qApp.translate("MainWindow", "Открыть план тестирования")),
                   ("Ctrl+S", qApp.translate("MainWindow", "Сохранить план тестирования")),
                   ("Alt+A", qApp.translate("MainWindow", "Автоподбор параметров")),
                   ("Enter", self._main_window.save_point_action.text()),
                   ("Left", qApp.translate("MainWindow", "Предыдущая точка")),
                   ("Right", qApp.translate("MainWindow", "Следующая точка")),
                   ("Del", qApp.translate("MainWindow", "Удалить точку"))]
        row_format = "<tr><td><b>{}</b></td><td>{}</td></tr>"
        text = "".join([row_format.format(key, description) for key, description in key_map])
        return f"{style}<table>{text}</table>"

    def _init_ui(self) -> None:
        self.setWindowTitle(qApp.translate("MainWindow", "Горячие клавиши"))
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.text_browser: QTextBrowser = self._create_text_browser()
        self.button_ok = QPushButton("OK")
        self.button_ok.clicked.connect(self.close)

        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(self.button_ok)

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.text_browser)
        v_layout.addLayout(h_layout)

        self.setLayout(v_layout)
        self.setFixedHeight(KeymapDialog.HEIGHT)
        self.setFixedWidth(KeymapDialog.WIDTH)


def show_keymap_info(main_window) -> None:
    """
    Function shows window with information about keyboard shortcuts used in the application.
    :param main_window: main window of application.
    """

    window = KeymapDialog(main_window)
    window.exec_()
