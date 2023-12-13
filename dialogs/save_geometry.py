from typing import Optional
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QCloseEvent, QShowEvent


def update_widget_to_save_geometry(widget_cls: type) -> type:
    """
    The decorator transforms the widget class so that the widget maintains its position when hidden.
    :param widget_cls: widget class.
    :return: decorated class.
    """

    class WidgetWithSavedGeometry(widget_cls):

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self._previous_geometry: Optional[QRect] = None

        def closeEvent(self, event: QCloseEvent) -> None:
            """
            :param event: close event.
            """

            if self.isVisible():
                self._previous_geometry = self.geometry()
            super().closeEvent(event)

        def showEvent(self, event: QShowEvent) -> None:
            """
            :param event: show event.
            """

            if self._previous_geometry is not None:
                self.setGeometry(self._previous_geometry)
            super().showEvent(event)

    return WidgetWithSavedGeometry
