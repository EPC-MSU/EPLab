import platform
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialogButtonBox, QDoubleSpinBox, QGroupBox, QLabel, QLineEdit,
                             QProgressBar, QPushButton, QSpinBox, QTextBrowser, QToolBar, QWidget)


def get_font_size() -> int:
    """
    :return: font size for operating system.
    """

    if platform.system().lower() == "windows":
        return 8
    return 11


def scale_font_on_widget(widget: QWidget, font_size: int) -> None:
    """
    :param widget: widget whose font needs to be scaled;
    :param font_size: required font size.
    """

    font = widget.font()
    font.setPointSize(font_size)
    widget.setFont(font)


def scale_low_settings_panel(widget, font_size: int) -> None:
    """
    :param widget:
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
            scale_font_on_widget(child_widget, font_size)
            child_widget.adjustSize()
        elif isinstance(child_widget, LowSettingsPanel):
            scale_low_settings_panel(child_widget, font_size)


def update_scale_decorator(func):
    """
    A decorator that will scale the ParameterWidget after creating option widgets.
    :param func: decorated method.
    """

    def wrapper(*args, **kwargs):

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
