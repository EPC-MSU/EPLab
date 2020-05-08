from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QPointF
from itertools import count
from typing import Optional
from PyQtExtendedScene import ExtendedScene
from boardview.BoardViewWidget import GraphicsManualPinItem
from epcore.elements import Board


class BoardWidget(QWidget):

    _board: Optional[Board] = None
    _scene: ExtendedScene

    def __init__(self, parent=None):
        super(BoardWidget, self).__init__(parent)

        layout = QVBoxLayout(self)

        self._scene = ExtendedScene()
        layout.addWidget(self._scene)

    def set_board(self, board: Board):

        self.layout().removeWidget(self._scene)
        self._scene = ExtendedScene()
        self.layout().addWidget(self._scene)

        if board.image:
            self._scene.set_background(QPixmap(board.image))

        pin_counter = count()

        for element in board.elements:
            for pin in element.pins:
                component = GraphicsManualPinItem(QPointF(pin.x, pin.y), number=next(pin_counter))
                self._scene.add_component(component)

    @property
    def workspace(self) -> ExtendedScene:
        return self._scene
