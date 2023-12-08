from typing import Optional
from PyQt5.QtCore import pyqtSlot, Qt, QTimer
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QWidget
from window.scaler import update_scale_of_class


@update_scale_of_class
class PopupMessage(QWidget):
    """
    Class for popup message.
    """

    OPACITY: float = 0.6
    TIME_TO_HIDE_IN_MSEC: int = 5000
    TIME_TO_SET_POSITION_IN_MSEC: int = 50

    def __init__(self, main_window: QMainWindow, text: str, time_to_hide: Optional[int] = None) -> None:
        """
        :param main_window: main window of application;
        :param text: message to show;
        :param time_to_hide: time after which to hide the message, in msec.
        """

        super().__init__()
        self._main_window: QMainWindow = main_window
        self._text: str = text
        self._init_ui()

        self._timer_to_hide_widget: QTimer = QTimer()
        self._timer_to_hide_widget.timeout.connect(self.close)
        self._timer_to_hide_widget.setSingleShot(True)
        self._timer_to_hide_widget.start(time_to_hide or PopupMessage.TIME_TO_HIDE_IN_MSEC)

        self._timer_to_set_position: QTimer = QTimer()
        self._timer_to_set_position.timeout.connect(self.set_position)
        self._timer_to_set_position.setSingleShot(True)
        self._timer_to_set_position.start(PopupMessage.TIME_TO_SET_POSITION_IN_MSEC)

    def _init_ui(self) -> None:
        self.setWindowOpacity(PopupMessage.OPACITY)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #FFC0CB;")

        self.label: QLabel = QLabel(self._text)
        self.h_layout: QHBoxLayout = QHBoxLayout()
        self.h_layout.addWidget(self.label)
        self.setLayout(self.h_layout)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.show()
        self.setVisible(False)

    @pyqtSlot()
    def set_position(self) -> None:
        """
        Method sets the position for the popup message.
        """

        main_window_geometry = self._main_window.geometry()
        x = main_window_geometry.x() + main_window_geometry.width() - self.width()
        y = main_window_geometry.y()
        self.move(x, y)
        self.setVisible(True)
