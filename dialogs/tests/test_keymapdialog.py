import sys
import unittest
from PyQt5.QtWidgets import QApplication
from dialogs.keymapdialog import KeymapDialog


class TestKeymapDialog(unittest.TestCase):

    def test_keymap_dialog(self) -> None:
        _ = QApplication(sys.argv[1:])
        window = KeymapDialog()
        self.assertIsNotNone(window)
