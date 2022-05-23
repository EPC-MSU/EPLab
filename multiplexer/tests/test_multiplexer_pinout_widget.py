"""
Tests for widget that displays multiplexer.
"""

import sys
import unittest
from PyQt5.QtWidgets import QApplication
from multiplexer.multiplexer_pinout_widget import MultiplexerPinoutWidget
from .utils import create_dummy_main_window


class TestMultiplexerPinoutWidget(unittest.TestCase):

    def test_creation_without_multiplexer(self):
        """
        Test checks creation of multiplexer pinout widget without multiplexer.
        """

        app = QApplication(sys.argv)
        dummy_main_window = create_dummy_main_window()
        dummy_main_window.measurement_plan.multiplexer = None
        multiplexer_pinout_widget = MultiplexerPinoutWidget(dummy_main_window)
        multiplexer_pinout_widget.update_info()
        self.assertEqual(len(multiplexer_pinout_widget._modules), 0)
        app.exit(0)

    def test_creation_with_multiplexer(self):
        """
        Test checks creation of multiplexer pinout widget with multiplexer.
        """

        app = QApplication(sys.argv)
        dummy_main_window = create_dummy_main_window()
        multiplexer_pinout_widget = MultiplexerPinoutWidget(dummy_main_window)
        multiplexer_pinout_widget.update_info()
        self.assertEqual(len(multiplexer_pinout_widget._modules), 3)
        app.exit(0)
