import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget
from window.utils import DIR_MEDIA


class LegendWidget(QWidget):

    def __init__(self, text: str, icon_path: str) -> None:
        super().__init__()
        self._icon_path: str = icon_path
        self._text: str = text
        self._init_ui()

    def _init_ui(self) -> None:
        self.label_color: QLabel = QLabel()
        self.label_color.setPixmap(QPixmap(self._icon_path))
        self.label_text: QLabel = QLabel(self._text)
        self.label_status: QLabel = QLabel("N/A")

        self.h_layout: QHBoxLayout = QHBoxLayout()
        self.h_layout.setSpacing(0)
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        for label in (self.label_color, self.label_text, self.label_status):
            label.setStyleSheet("background-color: black; color: white")
            self.h_layout.addWidget(label)
        self.h_layout.addStretch(1)
        self.setLayout(self.h_layout)
        self.setStyleSheet("background-color: black;")

    def clear(self) -> None:
        self.setVisible(False)

    def set_active(self) -> None:
        self.setVisible(True)
        self.label_status.clear()
        pixmap = QPixmap(os.path.join(DIR_MEDIA, "select_white.png"))
        self.label_status.setPixmap(pixmap.scaled(20, 20, Qt.KeepAspectRatio))

    def set_inactive(self) -> None:
        self.setVisible(True)
        self.label_status.clear()
        self.label_status.setText("N/A")
