from typing import Optional
from PyQt5.QtCore import QCoreApplication as qApp, QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QLineEdit
from window import utils as ut


class PinIndexWidget(QLineEdit):
    """
    Widget that displays the index of the current pin in user format, that is the index starts from 1.
    """

    WIDTH: int = 40

    def __init__(self, parent=None) -> None:
        """
        :param parent: parent widget.
        """

        super().__init__(parent)
        self._index: int = None
        self.setValidator(QRegExpValidator(QRegExp(r"\d+")))
        self.setFixedWidth(PinIndexWidget.WIDTH)

    def get_index(self) -> Optional[int]:
        """
        :return: pin index in programmatic format (starts at 1).
        """

        if not self.text():
            return None

        try:
            pin_index = int(self.text()) - 1
        except ValueError:
            ut.show_message(qApp.translate("t", "Ошибка"),
                            qApp.translate("t", "Неверный формат номера точки. Номер точки может принимать только "
                                                "целочисленное значение."))
            pin_index = None
        return pin_index

    def set_index(self, index: int) -> None:
        """
        :param index: pin index in programmatic format (starts with 1).
        """

        self.setText(str(index + 1))
