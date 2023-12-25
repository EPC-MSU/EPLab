from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QLineEdit


class ModifiedLineEdit(QLineEdit):
    """
    Class for line edit widget with additional handling of left and right keystrokes.
    """

    left_pressed: pyqtSignal = pyqtSignal()
    right_pressed: pyqtSignal = pyqtSignal()

    def keyPressEvent(self, key_press_event: QKeyEvent) -> None:
        """
        Method handles key press event.
        :param key_press_event: key press event.
        """

        super().keyPressEvent(key_press_event)
        if key_press_event.key() == Qt.Key_Left and self.cursorPosition() == 0:
            self.left_pressed.emit()
        elif key_press_event.key() == Qt.Key_Right and self.cursorPosition() == len(self.text()):
            self.right_pressed.emit()
