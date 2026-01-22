"""
File with dialog box class that displays the keyboard shortcuts used in the application.
"""

import os
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QLabel, QLayout, QPushButton, QVBoxLayout
from window import utils as ut
from window.scaler import update_scale_of_class


@update_scale_of_class
class KeymapDialog(QDialog):
    """
    Dialog box class that displays the keyboard shortcuts used in the application.
    """

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self._main_window = main_window
        self._init_ui()

    def _get_layout_with_button_ok(self) -> QHBoxLayout:
        """
        :return: horizontal layout with button OK.
        """

        self.button_ok: QPushButton = QPushButton("OK")
        self.button_ok.clicked.connect(self.close)

        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(self.button_ok)
        return h_layout

    def _get_layout_with_text(self) -> QGridLayout:
        """
        :return: text describing the keyboard shortcuts used in the application.
        """

        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        key_map = [("Ctrl+N", qApp.translate("MainWindow", "Создать план тестирования")),
                   ("Ctrl+O", qApp.translate("MainWindow", "Открыть план тестирования")),
                   ("Ctrl+S", qApp.translate("MainWindow", "Сохранить план тестирования")),
                   ("Ctrl+Shift+S", qApp.translate("MainWindow", "Сохранить план тестирования как")),
                   ("Alt+A", qApp.translate("MainWindow", "Автоподбор параметров")),
                   ("Space", self._main_window.save_point_action.text()),
                   ("Left", qApp.translate("MainWindow", "Предыдущая точка")),
                   ("Right", qApp.translate("MainWindow", "Следующая точка")),
                   ("Del", qApp.translate("MainWindow", "Удалить точку")),
                   ("F1", qApp.translate("MainWindow", "О программе")),
                   ("F2", qApp.translate("dialogs", "Редактировать комментарий"))]
        for row, key_and_description in enumerate(key_map):
            for column, key_or_description in enumerate(key_and_description):
                label = QLabel(key_or_description)
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                if column == 0:
                    label.setStyleSheet("font: bold")
                grid_layout.addWidget(label, row, column)

        return grid_layout

    def _init_ui(self) -> None:
        self.setWindowTitle(qApp.translate("MainWindow", "Горячие клавиши"))
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        v_layout = QVBoxLayout()
        v_layout.addLayout(self._get_layout_with_text())
        v_layout.addLayout(self._get_layout_with_button_ok())

        self.setLayout(v_layout)
        v_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)


def show_keymap_info(main_window) -> None:
    """
    Function shows window with information about keyboard shortcuts used in the application.
    :param main_window: main window of application.
    """

    window = KeymapDialog(main_window)
    window.exec()
