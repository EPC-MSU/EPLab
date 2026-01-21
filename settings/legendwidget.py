import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QToolBar, QWidget
from window.scaler import update_scale_of_class
from window.utils import DIR_MEDIA


@update_scale_of_class
class LegendWidget(QToolBar):
    """
    Class with legend for curves that are displayed in the IVViewer window.
    """

    ICON_SIZE: int = 20

    def __init__(self, text: str, color_name: str, left_margin: int) -> None:
        """
        :param text: legend text;
        :param color_name: name of icon with legend color;
        :param left_margin: left margin.
        """

        super().__init__()
        self._init_ui(text, color_name, left_margin)

    def _init_ui(self, text: str, color_path: str, left_margin: int) -> None:
        """
        :param text: legend text;
        :param color_path: name of icon with legend color;
        :param left_margin: left margin.
        """

        self.label_color: QLabel = QLabel()
        self.label_color.setContentsMargins(left_margin, 0, 0, 0)
        pixmap = QPixmap(os.path.join(DIR_MEDIA, color_path))
        self.label_color.setPixmap(pixmap.scaled(self.ICON_SIZE, self.ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio))
        self.label_text: QLabel = QLabel(text)
        self.label_status: QLabel = QLabel()

        layout: QHBoxLayout = QHBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)
        for label in (self.label_color, self.label_text, self.label_status):
            label.setStyleSheet("background-color: black; color: white;")
            layout.addWidget(label)
        layout.addStretch(1)

        widget = QWidget()
        widget.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)
        self.addWidget(widget)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background-color: black;")

    def clear(self) -> None:
        self.setVisible(False)

    def set_active(self) -> None:
        self.setVisible(True)
        self.label_status.clear()
        self.label_status.setText("☑")

    def set_inactive(self) -> None:
        self.setVisible(True)
        self.label_status.clear()
        self.label_status.setText("N/A")
