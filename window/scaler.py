import platform
from typing import Any, Callable, Optional
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialogButtonBox, QDoubleSpinBox, QGroupBox, QLabel, QLineEdit,
                             QProgressBar, QPushButton, QSpinBox, QTextBrowser, QToolBar, QWidget)


def get_font_size() -> int:
    """
    :return: font size for operating system.
    """

    if platform.system().lower() == "windows":
        return 8
    return 11


def get_scale_factor() -> float:
    """
    :return: scale factor for the current screen scale relative to the normal scale 96.
    """

    app = qApp.instance()
    for screen in app.screens():
        return screen.logicalDotsPerInch() / 96
    return 1


def scale_font_on_widget(widget: QWidget, font_size: int, scale_factor: Optional[float] = 1) -> None:
    """
    :param widget: widget whose font needs to be scaled;
    :param font_size: required font size;
    :param scale_factor: scale factor for the current screen scale relative to the normal scale 96.
    """

    font = widget.font()
    font.setPointSize(font_size)
    widget.setFont(font)

    if hasattr(widget, "minimumSize"):
        min_size = widget.minimumSize()
        min_size.setHeight(int(round(min_size.height() * scale_factor)))
        min_size.setWidth(int(round(min_size.width() * scale_factor)))
        widget.setMinimumSize(min_size)


def scale_low_settings_panel(widget, font_size: int) -> None:
    """
    :param widget: low settings panel widget;
    :param font_size: required font size.
    """

    for label in widget.get_labels():
        scale_font_on_widget(label, font_size)


def update_scale(widget: QWidget) -> None:
    """
    :param widget: widget that needs to be scaled.
    """

    from dialogs.measurersettingswindow import MeasurerSettingsWindow
    from settings import LowSettingsPanel
    from window.parameterwidget import ParameterWidget
    from window.pinindexwidget import PinIndexWidget

    font_size = get_font_size()
    scale_factor = get_scale_factor()
    if isinstance(widget, MeasurerSettingsWindow):
        for child_widget in widget.all_widgets:
            scale_font_on_widget(child_widget, font_size)
    elif isinstance(widget, ParameterWidget):
        for child_widget in widget.widgets:
            scale_font_on_widget(child_widget, font_size)

    for child_widget in vars(widget).values():
        if isinstance(child_widget, (QCheckBox, QComboBox, QDialogButtonBox, QDoubleSpinBox, QGroupBox, QLabel,
                                     QLineEdit, QProgressBar, QPushButton, QSpinBox, QTextBrowser, QToolBar,
                                     PinIndexWidget)):
            if isinstance(child_widget, QToolBar):
                for action in child_widget.actions():
                    scale_font_on_widget(action, font_size)
            scale_font_on_widget(child_widget, font_size, scale_factor)
            child_widget.adjustSize()
        elif isinstance(child_widget, LowSettingsPanel):
            scale_low_settings_panel(child_widget, font_size)


def update_scale_decorator(func: Callable[..., Any]):
    """
    A decorator that will scale the ParameterWidget after creating option widgets.
    :param func: decorated method.
    """

    def wrapper(*args, **kwargs) -> Any:

        result = func(*args, **kwargs)
        update_scale(args[0])
        return result

    return wrapper


def update_scale_of_class(widget_cls: type) -> type:
    """
    A decorator that will scale a widget created from a given class.
    :param widget_cls: widget class.
    :return: decorated class.
    """

    class ScaledWidgetClass(widget_cls):

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            update_scale(self)

    return ScaledWidgetClass
