from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QPointF
from typing import Optional
from boardview.BoardViewWidget import BoardView
from epcore.measurementmanager import MeasurementPlan


class BoardWidget(QWidget):

    _board: Optional[MeasurementPlan] = None
    _scene: BoardView

    def __init__(self, parent=None):
        super(BoardWidget, self).__init__(parent)

        layout = QVBoxLayout(self)

        self._scene = BoardView()
        layout.addWidget(self._scene)

    def set_board(self, board: MeasurementPlan):
        self.layout().removeWidget(self._scene)
        self._scene = BoardView()
        self.layout().addWidget(self._scene)

        if board.image:
            self._scene.set_background(QPixmap(board.image))
            self._scene.scale_to_window_size(self.width(), self.height())

        for number, pin in board.all_pins_iterator():
            self._scene.add_point(QPointF(pin.x, pin.y), number=number)

    def add_point(self, x: float, y: float, number: int):
        self._scene.add_point(QPointF(x, y), number)

    @property
    def workspace(self) -> BoardView:
        return self._scene
