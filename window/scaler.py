from PyQt5.QtWidgets import QLineEdit, QPushButton, QTextBrowser, QToolBar, QWidget


def scale_widget_with_font(widget: QWidget, font_size: int) -> None:
    font = widget.font()
    font.setPointSize(font_size)
    widget.setFont(font)


def update_scale(widget: QWidget) -> None:
    font_size = 8
    for attr_name, attr_value in vars(widget).items():
        if isinstance(attr_value, (QLineEdit, QPushButton, QTextBrowser, QToolBar)):
            scale_widget_with_font(attr_value, font_size)
            attr_value.adjustSize()
