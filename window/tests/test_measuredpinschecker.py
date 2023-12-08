import unittest
from window.measuredpinschecker import get_borders


class TestMeasuredPinsChecker(unittest.TestCase):

    def test_get_borders(self) -> None:
        self.assertEqual(get_borders([1, 2, 3, 5, 6, 27, 34, 35, 36, 37]), [(1, 3), (5, 6), (27, 27), (34, 37)])
