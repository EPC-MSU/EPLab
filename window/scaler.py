from PyQt5.QtWidgets import QLineEdit, QPushButton, QTextBrowser, QToolBar, QWidget
from settings import LowSettingsPanel


def scale_font_on_widget(widget: QWidget, font_size: int) -> None:
    """
    :param widget: widget whose font needs to be scaled;
    :param font_size: required font size.
    """

    font = widget.font()
    font.setPointSize(font_size)
    widget.setFont(font)


def scale_low_settings_panel(widget: LowSettingsPanel, font_size: int) -> None:
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

    font_size = 8
    for attr_name, child_widget in vars(widget).items():
        if isinstance(child_widget, (QLineEdit, QPushButton, QTextBrowser, QToolBar)):
            scale_font_on_widget(child_widget, font_size)
            child_widget.adjustSize()
        elif isinstance(child_widget, LowSettingsPanel):
            scale_low_settings_panel(child_widget, font_size)
