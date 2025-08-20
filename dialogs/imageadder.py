import os
from typing import Optional
from boardview.BoardViewWidget import BoardView
from PIL import Image, ImageOps
from PyQt5.QtCore import pyqtSlot, QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QGraphicsScene, QHBoxLayout, QPushButton, QVBoxLayout
from window.boardwidget import pil_to_pixmap


class ImageAdder(QDialog):
    """
    Dialog box for adding a board image.
    """

    def __init__(self, filename: str) -> None:
        """
        :param filename: the name of the file with the image to get.
        """

        super().__init__()
        self._read_image(filename)
        self._init_ui()

    def _add_image_to_scene(self) -> None:
        self._scene._background = None
        self._scene.set_background(pil_to_pixmap(self._image))
        self._scene.fitInView(self._scene._background, Qt.KeepAspectRatio)

    def _create_buttons(self) -> None:
        media_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")

        self.button_rotate_counterclockwise: QPushButton = QPushButton(qApp.translate("imageadder",
                                                                                      "Повернуть на 90° влево"))
        icon_path = os.path.join(media_path, "rotate_counterclockwise.png")
        self.button_rotate_counterclockwise.setIcon(QIcon(icon_path))
        self.button_rotate_counterclockwise.clicked.connect(self._rotate_counterclockwise)

        self.button_rotate_clockwise: QPushButton = QPushButton(qApp.translate("imageadder", "Повернуть на 90° вправо"))
        icon_path = os.path.join(media_path, "rotate_clockwise.png")
        self.button_rotate_clockwise.setIcon(QIcon(icon_path))
        self.button_rotate_clockwise.clicked.connect(self._rotate_clockwise)

        self.button_ok: QPushButton = QPushButton("OK")
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel: QPushButton = QPushButton(qApp.translate("t", "Отмена"))
        self.button_cancel.clicked.connect(self.reject)

        self._h_layout = QHBoxLayout()
        self._h_layout.setContentsMargins(0, 0, 0, 0)
        self._h_layout.addWidget(self.button_rotate_counterclockwise)
        self._h_layout.addWidget(self.button_rotate_clockwise)
        self._h_layout.addStretch(1)
        self._h_layout.addWidget(self.button_ok)
        self._h_layout.addWidget(self.button_cancel)

    def _create_scene(self) -> None:
        self._scene: BoardView = BoardView()
        self._scene.scene().setItemIndexMethod(QGraphicsScene.NoIndex)
        self._add_image_to_scene()

    def _init_ui(self) -> None:
        self._create_buttons()
        self._create_scene()

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self._scene)
        v_layout.addLayout(self._h_layout)
        self.setLayout(v_layout)

    def _read_image(self, filename: str) -> None:
        """
        :param filename: the name of the file with the image to get.
        """

        image = Image.open(filename)
        self._image: Image.Image = ImageOps.exif_transpose(image)

    def _rotate(self, angle: float) -> None:
        """
        :param angle: the angle by which the image should be rotated.
        """

        self._image = self._image.rotate(angle, expand=True)
        self._scene.scene().removeItem(self._scene._background)
        self._add_image_to_scene()

    @pyqtSlot()
    def _rotate_clockwise(self) -> None:
        self._rotate(-90)

    @pyqtSlot()
    def _rotate_counterclockwise(self) -> None:
        self._rotate(90)

    def get_image(self) -> Image.Image:
        """
        :return: image obtained from file after rotations.
        """

        return self._image


def get_image_from_file(filename: str) -> Optional[Image.Image]:
    """
    :param filename: the name of the file with the image to get.
    :return: image obtained from file after rotations.
    """

    image_adder = ImageAdder(filename)
    if image_adder.exec_() == QDialog.Accepted:
        return image_adder.get_image()

    return None
