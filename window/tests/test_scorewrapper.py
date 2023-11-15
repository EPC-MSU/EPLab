import sys
import unittest
from PyQt5.QtWidgets import QApplication, QLabel
from window.scorewrapper import ScoreWrapper


class TestScoreWrapper(unittest.TestCase):

    def setUp(self) -> None:
        self.app = QApplication(sys.argv)
        self.label = QLabel()
        self.score_wrapper = ScoreWrapper(self.label)

    def tearDown(self) -> None:
        self.app.exit(0)

    def test_set_dummy_score(self) -> None:
        self.score_wrapper.set_dummy_score()
        self.assertEqual(self.score_wrapper.get_friendly_score(), "-")

    def test_set_score(self) -> None:
        self.score_wrapper.set_score(0.69)
        self.assertEqual(self.score_wrapper.get_friendly_score(), "69%")
