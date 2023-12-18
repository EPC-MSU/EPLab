"""
File with class to show image of board.
"""

import os
from typing import Optional, Tuple, Union
from PIL import Image
from PyQt5.QtCore import pyqtSlot, QEvent, QObject, QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PyQt5.QtGui import QIcon, QImage, QKeyEvent, QPixmap, QResizeEvent, QWheelEvent
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from boardview.BoardViewWidget import BoardView, GraphicsManualPinItem
from epcore.elements import Pin
from epcore.measurementmanager import MeasurementPlan
from dialogs.save_geometry import update_widget_to_save_geometry
from window import utils as ut
from window.common import WorkMode
from window.pedalhandler import add_pedal_handler


def pil_to_pixmap(image: Image) -> QPixmap:
    # See https://stackoverflow.com/questions/34697559/pil-image-to-qpixmap-conversion-issue
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
    q_image = QImage(data, image.size[0], image.size[1], QImage.Format_ARGB32)
    return QPixmap.fromImage(q_image)


@add_pedal_handler
@update_widget_to_save_geometry
class BoardWidget(QWidget):
    """
    Class to show board image.
    """

    HEIGHT: int = 600
    WIDTH: int = 600

    def __init__(self, main_window=None) -> None:
        """
        :param main_window: main window of application.
        """

        super().__init__()
        self._board: Optional[MeasurementPlan] = None
        self._board_image: QPixmap = None
        self._control_pressed: bool = False
        self._parent = main_window
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

        return self._parent.measurement_plan

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

        if self._control_pressed and key in (Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_Up):
            return super().eventFilter(obj, event)

        if key == Qt.Key_Left:
            self._parent.go_to_left_or_right_pin(True)
            return True

        if key == Qt.Key_Right:
            self._parent.go_to_left_or_right_pin(False)
            return True

        if key in (Qt.Key_Enter, Qt.Key_Return) and self._parent.save_point_action.isEnabled():
            self._parent.save_pin()
            return True

        return self._parent.eventFilter(self._parent, event)

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
        self.setStyleSheet("background-color: black;")

        self._scene: BoardView = BoardView()
        self._scene.on_right_click.connect(self.create_new_pin)
        self._scene.point_moved.connect(self.change_pin_coordinates)
        self._scene.point_selected.connect(self.select_pin_with_index)
        self._scene.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self._scene)
        self.setLayout(layout)

    def _set_scene_rect(self) -> None:
        """
        Method sets area of the scene visualized by view.
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
        image_rect = self._board_image.rect()
        x_left, x_right = get_left_and_right(viewport_width, image_rect.width())
        y_top, y_bottom = get_left_and_right(viewport_height, image_rect.height())
        self._scene.setSceneRect(QRectF(x_left, y_top, x_right - x_left, y_bottom - y_top))
        self._scene.update()

    def add_pin(self, x: float, y: float, index: int) -> None:
        """
        Method adds new pin to board image.
        :param x: x coordinate of point;
        :param y: y coordinate of point;
        :param index: pin index.
        """

        self._scene.add_point(QPointF(x, y), index)

    def allow_drag(self, allow: bool) -> None:
        """
        :param allow: True, if to enable drag mode.
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

        if obj == self._scene and isinstance(event, QWheelEvent):
            result = super().eventFilter(obj, event)
            if self._board_image:
                self._timer.start()
            return result

        return super().eventFilter(obj, event)

    def get_default_pin_xy(self) -> QPointF:
        """
        :return: point with coordinates in the center of the board.
        """

        width = self._scene.width()
        height = self._scene.height()
        return self._scene.mapToScene(int(width / 2), int(height / 2))

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        :param event: resize event.
        """

        super().resizeEvent(event)
        if self._board_image:
            self._timer.start()

    def select_pin_on_scene(self, index: int, pin_centering: bool = True) -> None:
        """
        :param index: pin index;
        :param pin_centering: if True, then the selected pin will be centered on the board window.
        """

        self._scene.select_point(index)
        if pin_centering:
            self.show_component_centered(index)

    @pyqtSlot(int)
    def select_pin_with_index(self, index: int) -> None:
        """
        Slot handles signal when pin
        :param index: pin index.
        """

        self.measurement_plan.go_pin(index)
        self._parent.update_current_pin(False)

    def show_component_centered(self, index_or_component: Union[int, GraphicsManualPinItem]) -> None:
        """
        Method displays the selected component in the center of the screen.
        :param index_or_component: index or selected component.
        """

        if isinstance(index_or_component, GraphicsManualPinItem):
            component = index_or_component
        else:
            for component_ in self._scene._components:
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
            self._board_image = pil_to_pixmap(self.measurement_plan.image)
            self._scene.set_background(self._board_image)
            self._scene.scale_to_window_size(self.width(), self.height())
            image_rect = self._board_image.rect()
            self._scene.setSceneRect(image_rect.x(), image_rect.y(), image_rect.width(), image_rect.height())
        else:
            del self._board_image
            self._board_image = None
            self.close()

        for index, pin in self.measurement_plan.all_pins_iterator():
            self._scene.add_point(QPointF(pin.x, pin.y), number=index)
