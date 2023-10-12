import sys
import unittest
from PyQt5.QtWidgets import QApplication
from dialogs.aboutwindow import AboutWindow


class TestAboutWindow(unittest.TestCase):

    def test_about_window(self) -> None:
        _ = QApplication(sys.argv[1:])
        window = AboutWindow()
        self.assertIsNotNone(window)
