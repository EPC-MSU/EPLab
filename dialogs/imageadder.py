import gc
import os
from typing import Optional
from boardview.BoardViewWidget import BoardView
from PIL import Image, ImageOps, UnidentifiedImageError
from PyQt6.QtCore import pyqtSlot, QCoreApplication as qApp, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QTransform
from PyQt6.QtWidgets import QDialog, QGraphicsScene, QHBoxLayout, QPushButton, QStyle, QVBoxLayout
from window import utils as ut
from window.boardwidget import convert_pil_image_to_qpixmap
from window.scaler import update_scale_of_class


@update_scale_of_class
class ImageAdder(QDialog):
    """
    Dialog box for adding a board image.
    """

    INIT_SIZE_AS_PROPORTION_OF_SCREEN: float = 0.6

    def __init__(self, filepath: str) -> None:
        """
        :param filepath: path to image file.
        """

        super().__init__()
        self._angle: int = 0
        self._image: Optional[Image.Image] = self._read_image(filepath)
        if self._image is None:
            return

        self._pixmap: Optional[QPixmap] = self._convert_image_to_pixmap()
        if self._pixmap is None:
            return

        self._init_ui()
        self._set_init_position()
        QTimer.singleShot(100, self._rotate_pixmap)

    def _add_pixmap_to_scene(self) -> None:
        self._scene.set_background(self._rotated_pixmap)
        center_pos = self._scene.scene().sceneRect().center()
        self._scene._background.setPos(center_pos - self._scene._background.boundingRect().center())
        self._scene.fitInView(self._scene._background, Qt.AspectRatioMode.KeepAspectRatio)
        self._scene.update()

    def _change_rotation_angle(self, angle_change: int) -> None:
        """
        :param angle_change: how much the image rotation angle should be changed (positive values - clockwise rotation,
        negative - counterclockwise).
        """

        self._angle += angle_change

    def _convert_image_to_pixmap(self) -> Optional[QPixmap]:
        """
        :return: pixmap for image.
        """

        try:
            pixmap = convert_pil_image_to_qpixmap(self._image)
        except MemoryError:
            pixmap = None
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Загружаемое изображение слишком большое. Выберите изображение меньшего"
                                                " размера или воспользуйтесь 64-битной версией программы EPLab."))
        return pixmap

    def _create_buttons(self) -> None:
        self.button_rotate_counterclockwise: QPushButton = QPushButton(qApp.translate("dialogs",
                                                                                      "Повернуть на 90° влево"))
        icon_path = os.path.join(ut.DIR_MEDIA, "rotate_counterclockwise.png")
        self.button_rotate_counterclockwise.setIcon(QIcon(icon_path))
        self.button_rotate_counterclockwise.clicked.connect(self._rotate_counterclockwise)

        self.button_rotate_clockwise: QPushButton = QPushButton(qApp.translate("dialogs", "Повернуть на 90° вправо"))
        icon_path = os.path.join(ut.DIR_MEDIA, "rotate_clockwise.png")
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
        self._scene.scene().setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)

    def _init_ui(self) -> None:
        self.setWindowTitle(qApp.translate("MainWindow", "Добавить изображение"))
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))

        self._create_buttons()
        self._create_scene()

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self._scene)
        v_layout.addLayout(self._h_layout)
        self.setLayout(v_layout)

    @staticmethod
    def _read_image(filepath: str) -> Optional[Image.Image]:
        """
        :param filepath: path to image file.
        :return: image read from file.
        """

        filename = os.path.basename(filepath)
        try:
            image = Image.open(filepath)
            image = ImageOps.exif_transpose(image)
        except FileNotFoundError:
            image = None
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("dialogs", 'Файл изображения "{}" не найден.').format(filename))
        except MemoryError:
            image = None
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Загружаемое изображение слишком большое. Выберите изображение меньшего"
                                                " размера или воспользуйтесь 64-битной версией программы EPLab."))
        except UnidentifiedImageError:
            image = None
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("dialogs", 'Не удается идентифицировать файл изображения "{}".'
                                           ).format(filename))
        return image

    def _remove_pixmap_from_scene(self) -> None:
        if self._scene._background is not None:
            self._scene.scene().removeItem(self._scene._background)
            self._scene._background = None

    def _rotate_pixmap(self) -> None:
        transform = QTransform()
        transform.rotate(self._angle)
        self._rotated_pixmap = self._pixmap.transformed(transform)

        self._remove_pixmap_from_scene()
        self._add_pixmap_to_scene()

    @pyqtSlot()
    def _rotate_clockwise(self) -> None:
        """
        Slot rotates the image 90 degrees clockwise.
        """

        self._change_rotation_angle(90)
        self._rotate_pixmap()

    @pyqtSlot()
    def _rotate_counterclockwise(self) -> None:
        """
        Slot rotates the image 90 degrees counterclockwise.
        """

        self._change_rotation_angle(-90)
        self._rotate_pixmap()

    def _set_init_position(self) -> None:
        """
        Method moves the window to the desired position and sets the initial dimensions.
        """

        geometry = qApp.instance().desktop().availableGeometry()
        available_height = geometry.height() - self.style().pixelMetric(QStyle.PixelMetric.PM_TitleBarHeight)
        available_width = geometry.width()

        height = self.INIT_SIZE_AS_PROPORTION_OF_SCREEN * available_height
        width = self.INIT_SIZE_AS_PROPORTION_OF_SCREEN * available_width
        pos_x = geometry.x() + (available_width - width) / 2
        pos_y = geometry.y() + (available_height - height) / 2
        self.move(pos_x, pos_y)
        self.resize(width, height)

    def exec_(self) -> int:
        """
        :return: dialog code result.
        """

        if self._image is None or self._pixmap is None:
            gc.collect()
            return QDialog.DialogCode.Rejected

        result = super().exec()
        gc.collect()
        return result

    def get_image(self) -> Image.Image:
        """
        :return: image obtained from file after rotations.
        """

        if self._angle:
            return self._image.rotate(-self._angle, expand=True)

        return self._image


def get_image_from_file(filepath: str) -> Optional[Image.Image]:
    """
    :param filepath: path to image file.
    :return: image obtained from file after rotations.
    """

    image_adder = ImageAdder(filepath)
    if image_adder.exec_() == QDialog.DialogCode.Accepted:
        return image_adder.get_image()

    return None
