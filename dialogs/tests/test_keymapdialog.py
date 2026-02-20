import sys
import unittest
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from dialogs.keymapdialog import KeymapDialog


class TestKeymapDialog(unittest.TestCase):

    class MainWindow(QWidget):

        def __init__(self) -> None:
            super().__init__()
            self.save_point_action = QLabel("some text")

    def setUp(self) -> None:
        self.app: QApplication = QApplication(sys.argv[1:])
        self.main_window = self.MainWindow()

    def test_keymap_dialog(self) -> None:
        window = KeymapDialog(self.main_window)
        self.assertIsNotNone(window)
