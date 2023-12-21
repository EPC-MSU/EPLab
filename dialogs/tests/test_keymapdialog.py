import sys
import unittest
from PyQt5.QtWidgets import QApplication, QLabel
from dialogs.keymapdialog import KeymapDialog


class TestKeymapDialog(unittest.TestCase):

    class MainWindow:

        def __init__(self) -> None:
            self.save_point_action = QLabel("some text")

    def setUp(self) -> None:
        self.app: QApplication = QApplication(sys.argv[1:])
        self.main_window = self.MainWindow()

    def test_keymap_dialog(self) -> None:
        window = KeymapDialog(self.main_window)
        self.assertIsNotNone(window)
