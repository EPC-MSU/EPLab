import unittest
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QApplication
import sys
from score import ScoreWrapper


class TestScore(unittest.TestCase):
    def test_score_display(self):
        app = QApplication(sys.argv)
        label = QLabel()
        wrap = ScoreWrapper(label)

        wrap.set_score(0.54)
        self.assertTrue("54" in label.text())

        app.exit(0)
