"""
File with class to show image of board.
"""

import os
from typing import Optional
from PIL import Image
from PyQt5.QtCore import pyqtSlot, QPointF
from PyQt5.QtGui import QIcon, QImage, QPixmap
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

    def __init__(self, parent=None):
        """
        :param parent: parent main window.
        """

        super().__init__()
        self._parent = parent
        self._scene: BoardView = BoardView()
        self._scene.on_right_click.connect(self.create_new_pin)
        self._scene.point_moved.connect(self.change_pin_coordinates)
        self._scene.point_selected.connect(self.select_pin_with_index)
        self._init_ui()

    def _init_ui(self):
        """
        Method initializes widgets.
        """

        self.setWindowTitle("EPLab - Board")
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "ico.png")))
        self.resize(self.WIDTH, self.HEIGHT)
        self.setStyleSheet("background-color:black;")
        layout = QVBoxLayout(self)
        layout.addWidget(self._scene)
        self.setLayout(layout)

    def add_pin(self, x: float, y: float, index: int):
        """
        Method adds new pin to board image.
        :param x: x coordinate of point;
        :param y: y coordinate of point;
        :param index: pin index.
        """

        self._scene.add_point(QPointF(x, y), index)

    @pyqtSlot(int, QPointF)
    def change_pin_coordinates(self, index: int, pin: QPointF):
        """
        Slot changes coordinates of given pin.
        :param index: pin index;
        :param pin: new coordinates of pin.
        """

        self._parent.measurement_plan.go_pin(index)
        self._parent.measurement_plan.get_current_pin().x = pin.x()
        self._parent.measurement_plan.get_current_pin().y = pin.y()

    @pyqtSlot(QPointF)
    def create_new_pin(self, point: QPointF):
        """
        Slot creates new pin on board.
        :param point: object with coordinates of new pin.
        """

        if self._parent.work_mode is WorkMode.WRITE:
            pin = Pin(x=point.x(), y=point.y(), measurements=[])
            self._parent.measurement_plan.append_pin(pin)
            self.add_pin(pin.x, pin.y, self._parent.measurement_plan.get_current_index())
            self._parent.update_current_pin()

    @pyqtSlot(int)
    def select_pin_with_index(self, index: int):
        """
        Slot handles signal when pin
        :param index: pin index.
        """

        self._parent.measurement_plan.go_pin(index)
        self._parent.update_current_pin()

    def set_board(self, board: MeasurementPlan):
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

    @property
    def workspace(self) -> BoardView:
        return self._scene
