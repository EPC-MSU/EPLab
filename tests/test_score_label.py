import sys
import unittest
from PyQt5.QtWidgets import QApplication, QLabel
from score import ScoreWrapper


class TestScore(unittest.TestCase):

    def test_score_display(self):
        app = QApplication(sys.argv)
        label = QLabel()
        score_wrapper = ScoreWrapper(label)
        score_wrapper._set_score(0.54)
        self.assertTrue("54" in label.text())
        app.exit(0)
