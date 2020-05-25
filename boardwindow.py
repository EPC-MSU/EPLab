from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QPointF
from typing import Optional
from boardview.BoardViewWidget import BoardView
from epcore.measurementmanager import MeasurementPlan
from PIL import Image


def pil_to_pixmap(im):
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
    _board: Optional[MeasurementPlan] = None
    _scene: BoardView

    def __init__(self, parent=None):
        super(BoardWidget, self).__init__(parent)

        layout = QVBoxLayout(self)

        self._scene = BoardView()
        layout.addWidget(self._scene)

    def set_board(self, board: MeasurementPlan):

        self._scene.clear_scene()

        if board.image:
            self._scene.set_background(pil_to_pixmap(board.image))
            self._scene.scale_to_window_size(self.width(), self.height())

        for number, pin in board.all_pins_iterator():
            self._scene.add_point(QPointF(pin.x, pin.y), number=number)

    def add_point(self, x: float, y: float, number: int):
        self._scene.add_point(QPointF(x, y), number)

    @property
    def workspace(self) -> BoardView:
        return self._scene
