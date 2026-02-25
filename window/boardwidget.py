"""
File with class to show image of board.
"""

import gc
import os
from typing import Optional, Tuple, Union
from PIL import Image
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, QByteArray, QCoreApplication as qApp, QEvent, QObject, QPoint, QPointF,
                          QRect, QRectF, Qt, QTimer)
from PyQt5.QtGui import QIcon, QImage, QKeyEvent, QMoveEvent, QPixmap, QResizeEvent, QWheelEvent
from PyQt5.QtWidgets import QGraphicsScene, QVBoxLayout, QWidget
from boardview.BoardViewWidget import BoardView, GraphicsManualPinItem
from epcore.measurementmanager import MeasurementPlan
from dialogs.save_geometry import update_widget_to_save_geometry
from . import utils as ut
from .common import WorkMode
from .pedalhandler import add_pedal_handler


def convert_pil_image_to_qpixmap(image: Image) -> QPixmap:
    """
    See https://stackoverflow.com/questions/34697559/pil-image-to-qpixmap-conversion-issue.
    :param image: image.
    :return: pixmap.
    """

    if image.mode == "RGB":
        red, green, blue = image.split()
        image = Image.merge("RGB", (blue, green, red))
    elif image.mode == "RGBA":
        red, green, blue, alpha = image.split()
        image = Image.merge("RGBA", (blue, green, red, alpha))
    elif image.mode == "L":
        image = image.convert("RGBA")
    image_2 = image.convert("RGBA")
    data = image_2.tobytes("raw", "RGBA")
    q_image = QImage(data, image.size[0], image.size[1], QImage.Format.Format_ARGB32)
    return QPixmap.fromImage(q_image)


@add_pedal_handler
@update_widget_to_save_geometry
class BoardWidget(QWidget):
    """
    Class to show board image.
    """

    HEIGHT: int = 600
    WIDTH: int = 600
    current_pin_signal: pyqtSignal = pyqtSignal(int, bool)
    geometry_changed: pyqtSignal = pyqtSignal(QByteArray)

    def __init__(self, main_window) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self._board: Optional[MeasurementPlan] = None
        self._board_pixmap: Optional[QPixmap] = None
        self._control_pressed: bool = False
        self._main_window = main_window
        self._previous_pos: Optional[QRect] = None
        self._timer: QTimer = QTimer()
        self._timer.timeout.connect(self._set_scene_rect)
        self._timer.setInterval(50)
        self._timer.setSingleShot(True)
        self._init_ui()

    @property
    def measurement_plan(self) -> MeasurementPlan:
        """
        :return: measurement plan.
        """

        return self._main_window.measurement_plan

    def _convert_image_to_pixmap(self) -> None:
        try:
            self._board_pixmap = convert_pil_image_to_qpixmap(self.measurement_plan.image)
        except MemoryError:
            self._delete_board_pixmap()
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Загружаемое изображение слишком большое. Выберите изображение меньшего"
                                                " размера или воспользуйтесь 64-битной версией программы EPLab."))

    def _delete_board_pixmap(self) -> None:
        del self._board_pixmap
        self._board_pixmap = None
        gc.collect()

    def _handle_key_press_event(self, obj: QObject, event: QKeyEvent) -> bool:
        """
        Method handles key press events for board view.
        :param obj: board view object;
        :param event: key press event.
        :return: handling result.
        """

        key = event.key()
        if key == Qt.Key.Key_Control:
            self._control_pressed = True

        if self._control_pressed and key in (Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up):
            return super().eventFilter(obj, event)

        return self._main_window.eventFilter(self._main_window, event)

    def _handle_key_release_event(self, obj: QObject, event: QKeyEvent) -> bool:
        """
        Method handles key release event for board view.
        :param obj: board view object;
        :param event: key release event.
        :return: handling result.
        """

        key = event.key()
        if key == Qt.Key.Key_Control:
            self._control_pressed = False
        return super().eventFilter(obj, event)

    def _init_ui(self) -> None:
        """
        Method initializes widgets.
        """

        self.setWindowTitle("EPLab - Board")
        self.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
        self.resize(self.WIDTH, self.HEIGHT)
        self.setStyleSheet("background-color: black;")

        self._scene: BoardView = BoardView(cross_in_center=True)
        self._scene.scene().setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        self._scene.on_right_click.connect(self.create_new_pin)
        self._scene.point_moved.connect(self.change_pin_coordinates)
        self._scene.point_selected.connect(self.send_current_pin_index)
        self._scene.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self._scene)
        self.setLayout(layout)

    @pyqtSlot()
    def _set_scene_rect(self) -> None:
        """
        Slot sets area of the scene visualized by view.
        """

        def get_viewport_size_in_scene_coordinates() -> Tuple[float, float]:
            viewport_size = self._scene.viewport().size()
            top_left = QPoint(0, 0)
            top_left = self._scene.mapToScene(top_left)
            bottom_right = QPoint(viewport_size.width(), viewport_size.height())
            bottom_right = self._scene.mapToScene(bottom_right)
            return bottom_right.x() - top_left.x(), bottom_right.y() - top_left.y()

        def get_left_and_right(viewport_size: float, image_size: float) -> Tuple[float, float]:
            d_size = (viewport_size - image_size) / 2
            if viewport_size < image_size:
                d_size = 0
            left = 0 - 2 * d_size - image_size / 2
            right = image_size + 2 * d_size + image_size / 2
            return left, right

        viewport_width, viewport_height = get_viewport_size_in_scene_coordinates()
        image_rect = self._board_pixmap.rect()
        x_left, x_right = get_left_and_right(viewport_width, image_rect.width())
        y_top, y_bottom = get_left_and_right(viewport_height, image_rect.height())
        self._scene.setSceneRect(QRectF(x_left, y_top, x_right - x_left, y_bottom - y_top))
        self._scene.update()

    def add_pin_to_board_image(self, x: float, y: float, index: int) -> None:
        """
        Method adds new pin to board image.
        :param x: x coordinate of point;
        :param y: y coordinate of point;
        :param index: pin index.
        """

        self._scene.add_point(QPointF(x, y), index)

    def allow_drag(self, allow: bool) -> None:
        """
        :param allow: True, if to enable drag mode (pins can be moved around the board).
        """

        self._scene.allow_drag(allow)

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

        if (not self._main_window.measurement_plan.multiplexer and self._main_window.work_mode is WorkMode.WRITE
                and self._main_window.create_new_pin(point, False)):
            self._main_window.save_pin(False)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        :param obj: object for which event occurred;
        :param event: event.
        :return: True if event should be filtered out, otherwise - False.
        """

        if obj == self._scene and isinstance(event, QKeyEvent):
            key_event = event
            if key_event.type() == QEvent.Type.KeyPress:
                return self._handle_key_press_event(obj, event)

            if key_event.type() == QEvent.Type.KeyRelease:
                return self._handle_key_release_event(obj, event)

        if obj == self._scene and isinstance(event, QWheelEvent):
            result = super().eventFilter(obj, event)
            if self._board_pixmap:
                self._timer.start()
            return result

        return super().eventFilter(obj, event)

    def get_default_pin_xy(self) -> Tuple[float, float]:
        """
        :return: coordinates in the center of the board.
        """

        width = self._scene.width()
        height = self._scene.height()
        point = self._scene.mapToScene(int(width / 2), int(height / 2))
        return point.x(), point.y()

    def moveEvent(self, event: QMoveEvent) -> None:
        """
        :param event: move event.
        """

        if self._board_pixmap:
            self.geometry_changed.emit(self.saveGeometry())
        super().moveEvent(event)

    def open_board_image(self) -> None:
        if not self.measurement_plan.image:
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Для данной платы изображение не задано."))
        elif not self._board_pixmap:
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Для данной платы не удалось загрузить изображение."))
        else:
            self.open_board_image_if_needed()

    def open_board_image_if_needed(self) -> None:
        if self._board_pixmap:
            if not self.isVisible():
                self.show()
            else:
                self.activateWindow()

    def remove_pin_from_board_image(self, index: int) -> None:
        """
        :param index: pin index to delete from board image.
        """

        self._scene.remove_point(index)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        :param event: resize event.
        """

        super().resizeEvent(event)
        if self._board_pixmap:
            self._timer.start()
            self.geometry_changed.emit(self.saveGeometry())

    def select_pin_on_scene(self, index: int, pin_centering: bool = True) -> None:
        """
        :param index: pin index;
        :param pin_centering: if True, then the selected pin will be centered on the board window.
        """

        if index is None:
            self._scene.remove_all_selections()
            return

        self._scene.select_point(index)
        if pin_centering:
            self.show_component_centered(index)

    @pyqtSlot(int)
    def send_current_pin_index(self, index: int) -> None:
        """
        Slot sends a signal with the number of the current pin.
        :param index: pin index.
        """

        self.current_pin_signal.emit(index, False)

    def show_component_centered(self, index_or_component: Union[int, GraphicsManualPinItem]) -> None:
        """
        Method displays the selected component in the center of the screen.
        :param index_or_component: index or selected component.
        """

        if isinstance(index_or_component, GraphicsManualPinItem):
            component = index_or_component
        else:
            for component_ in getattr(self._scene, "_components", []):
                if component_.number == index_or_component:
                    component = component_
                    break
            else:
                component = None

        if component is not None:
            self._scene.centerOn(component)

    def update_board(self) -> None:
        """
        Method updates board image.
        """

        self._scene.clear_scene()
        if self.measurement_plan.image:
            self._convert_image_to_pixmap()
        else:
            self._delete_board_pixmap()

        if self._board_pixmap:
            self._scene.set_background(self._board_pixmap)
            self._scene.scale_to_window_size(self.width(), self.height())
            image_rect = self._board_pixmap.rect()
            self._scene.setSceneRect(image_rect.x(), image_rect.y(), image_rect.width(), image_rect.height())
        else:
            self.close()

        for index, pin in self.measurement_plan.all_pins_iterator():
            self._scene.add_point(QPointF(pin.x, pin.y), index)
