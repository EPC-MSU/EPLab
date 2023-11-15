from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, QRect, Qt
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QLineEdit, QMainWindow, QPushButton, QToolBar, QWidget


class Scaler:

    FONT_SIZE: int = 8

    def __init__(self, main_window: QMainWindow) -> None:
        self.window: QMainWindow = main_window
        app = qApp.instance()
        screen = app.screens()[0]
        screen.logicalDotsPerInchChanged.connect(lambda _: self.update_scale())

    @pyqtSlot()
    def update_scale(self) -> None:
        for attr_name, attr_value in vars(self.window).items():
            if isinstance(attr_value, (QLineEdit, QPushButton, QToolBar)):
                scale_widget_with_font(attr_value, Scaler.FONT_SIZE)


def scale_widget_with_font(widget: QWidget, font_size: int) -> None:
    font = widget.font()
    font.setPointSize(font_size)
    widget.setFont(font)
    if isinstance(widget, QPushButton):
        font_metric = QFontMetrics(font)
        widget.setMinimumHeight(int(1.5 * font_metric.boundingRect(QRect(), Qt.AlignCenter, widget.text()).height()))
