"""
File with class to show image of board.
"""

import os
from typing import Optional
from PIL import Image
from PyQt5.QtCore import pyqtSlot, QEvent, QObject, QPointF, Qt
from PyQt5.QtGui import QIcon, QImage, QKeyEvent, QPixmap
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from boardview.BoardViewWidget import BoardView
from epcore.elements import Pin
from epcore.measurementmanager import MeasurementPlan
import utils as ut
from common import WorkMode


def pil_to_pixmap(im: Image) -> QPixmap:
    # See https://stackoverflow.com/questions/34697559/pil-image-to-qpixmap-conversion-issue
    if im.mode == "RGB":
        r, g, b = im.split()
        im = Image.merge("RGB", (b, g, r))
    elif im.mode == "RGBA":
        r, g, b, a = im.split()
        im = Image.merge("RGBA", (b, g, r, a))
    elif im.mode == "L":
        im = im.convert("RGBA")
    im2 = im.convert("RGBA")
    data = im2.tobytes("raw", "RGBA")
    qim = QImage(data, im.size[0], im.size[1], QImage.Format_ARGB32)
    pixmap = QPixmap.fromImage(qim)
    return pixmap


class BoardWidget(QWidget):
    """
    Class to show board image.
    """

    HEIGHT: int = 600
    WIDTH: int = 600
    _board: Optional[MeasurementPlan] = None
    _scene: BoardView

    def __init__(self, parent=None) -> None:
        """
        :param parent: parent main window.
        """

        super().__init__()
        self._control_pressed: bool = False
        self._parent = parent
        self._scene: BoardView = BoardView()
        self._scene.on_right_click.connect(self.create_new_pin)
        self._scene.point_moved.connect(self.change_pin_coordinates)
        self._scene.point_selected.connect(self.select_pin_with_index)
        self._scene.installEventFilter(self)
        self._init_ui()

    @property
    def measurement_plan(self) -> MeasurementPlan:
        """
        :return: measurement plan.
        """

        return self._parent.measurement_plan

    @property
    def workspace(self) -> BoardView:
        return self._scene

    def _handle_key_press_event(self, obj: QObject, event: QEvent) -> bool:
        """
        Method handles key press events for board view.
        :param obj: board view object;
        :param event: key press event.
        :return: handling result.
        """

        key = QKeyEvent(event).key()
        if key == Qt.Key_Control:
            self._control_pressed = True
            return True
        if self._control_pressed and key in (Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_Up):
            return super().eventFilter(obj, event)
        if key == Qt.Key_Left:
            self._parent.go_to_left_or_right_pin(True)
            return True
        if key == Qt.Key_Right:
            self._parent.go_to_left_or_right_pin(False)
            return True
        if key in (Qt.Key_Enter, Qt.Key_Return):
            self._parent.save_pin()
            return True
        return super().eventFilter(obj, event)

    def _handle_key_release_event(self, obj: QObject, event: QEvent) -> bool:
        """
        Method handles key release event for board view.
        :param obj: board view object;
        :param event: key release event.
        :return: handling result.
        """

        key = QKeyEvent(event).key()
        if key == Qt.Key_Control:
            self._control_pressed = False
        return super().eventFilter(obj, event)

    def _init_ui(self) -> None:
        """
        Method initializes widgets.
        """

        self.setWindowTitle("EPLab - Board")
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
        self.resize(BoardWidget.WIDTH, BoardWidget.HEIGHT)
        self.setStyleSheet("background-color:black;")
        layout = QVBoxLayout(self)
        layout.addWidget(self._scene)
        self.setLayout(layout)

    def add_pin(self, x: float, y: float, index: int) -> None:
        """
        Method adds new pin to board image.
        :param x: x coordinate of point;
        :param y: y coordinate of point;
        :param index: pin index.
        """

        self._scene.add_point(QPointF(x, y), index)

    @pyqtSlot(int, QPointF)
    def change_pin_coordinates(self, index: int, pin: QPointF) -> None:
        """
        Slot changes coordinates of given pin.
        :param index: pin index;
        :param pin: new coordinates of pin.
        """

        self.measurement_plan.go_pin(index)
        current_pin = self.measurement_plan.get_current_pin()
        current_pin.x = pin.x()
        current_pin.y = pin.y()

    @pyqtSlot(QPointF)
    def create_new_pin(self, point: QPointF) -> None:
        """
        Slot creates new pin on board.
        :param point: object with coordinates of new pin.
        """

        if self._parent.work_mode is WorkMode.WRITE:
            pin = Pin(x=point.x(), y=point.y(), measurements=[])
            self.measurement_plan.append_pin(pin)
            self.add_pin(pin.x, pin.y, self.measurement_plan.get_current_index())
            self._parent.update_current_pin()
            self._parent.save_pin()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj == self._scene and isinstance(event, QKeyEvent):
            key_event = QKeyEvent(event)
            if key_event.type() == QEvent.KeyPress:
                return self._handle_key_press_event(obj, event)
            if key_event.type() == QEvent.KeyRelease:
                return self._handle_key_release_event(obj, event)
        return super().eventFilter(obj, event)

    @pyqtSlot(int)
    def select_pin_with_index(self, index: int) -> None:
        """
        Slot handles signal when pin
        :param index: pin index.
        """

        self.measurement_plan.go_pin(index)
        self._parent.update_current_pin()

    def set_board(self, board: MeasurementPlan) -> None:
        """
        Method sets new board.
        :param board: new board.
        """

        self._scene.clear_scene()
        if board.image:
            self._scene.set_background(pil_to_pixmap(board.image))
            self._scene.scale_to_window_size(self.width(), self.height())
        for index, pin in board.all_pins_iterator():
            self._scene.add_point(QPointF(pin.x, pin.y), number=index)
