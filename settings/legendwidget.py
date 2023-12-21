import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QToolBar, QWidget
from window.scaler import update_scale_of_class
from window.utils import DIR_MEDIA


@update_scale_of_class
class LegendWidget(QToolBar):

    ICON_SIZE: int = 20

    def __init__(self, text: str, color_path: str, left_margin: int) -> None:
        """
        :param text: legend text;
        :param color_path: path to icon with legend color;
        :param left_margin: left margin.
        """

        super().__init__()
        self._pixmap_select: QPixmap = self._load_select_pixmap()
        self._init_ui(text, color_path, left_margin)

    def _init_ui(self, text: str, color_path: str, left_margin: int) -> None:
        """
        :param text: legend text;
        :param color_path: path to icon with legend color;
        :param left_margin: left margin.
        """

        self.label_color: QLabel = QLabel()
        self.label_color.setContentsMargins(left_margin, 0, 0, 0)
        pixmap = QPixmap(color_path)
        self.label_color.setPixmap(pixmap.scaled(LegendWidget.ICON_SIZE, LegendWidget.ICON_SIZE, Qt.KeepAspectRatio))
        self.label_text: QLabel = QLabel(text)
        self.label_status: QLabel = QLabel()

        self.h_layout: QHBoxLayout = QHBoxLayout()
        self.h_layout.setSpacing(4)
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        for label in (self.label_color, self.label_text, self.label_status):
            label.setStyleSheet("background-color: black; color: white")
            self.h_layout.addWidget(label)
        self.h_layout.addStretch(1)

        widget = QWidget()
        widget.setLayout(self.h_layout)
        self.addWidget(widget)
        self.setStyleSheet("background-color: black;")

    @staticmethod
    def _load_select_pixmap() -> QPixmap:
        """
        :return: image of select icon.
        """

        pixmap = QPixmap(os.path.join(DIR_MEDIA, "select_white.png"))
        return pixmap.scaled(LegendWidget.ICON_SIZE, LegendWidget.ICON_SIZE, Qt.KeepAspectRatio)

    def clear(self) -> None:
        self.setVisible(False)

    def set_active(self) -> None:
        self.setVisible(True)
        self.label_status.clear()
        self.label_status.setPixmap(self._pixmap_select)

    def set_inactive(self) -> None:
        self.setVisible(True)
        self.label_status.clear()
        self.label_status.setText("N/A")
