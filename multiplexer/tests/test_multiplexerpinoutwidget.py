"""
Tests for widget that displays multiplexer.
"""

import sys
import unittest
from PyQt5.QtWidgets import QApplication
from epcore.analogmultiplexer import ModuleTypes
from multiplexer.multiplexerpinoutwidget import MultiplexerPinoutWidget


class TestMultiplexerPinoutWidget(unittest.TestCase):

    def test_creation_without_multiplexer(self):
        """
        Test checks creation of multiplexer pinout widget without multiplexer.
        """

        app = QApplication(sys.argv)
        multiplexer_pinout_widget = MultiplexerPinoutWidget()
        multiplexer_pinout_widget.update_info(False, [], None)
        self.assertEqual(len(multiplexer_pinout_widget._modules), 0)
        app.exit(0)

    def test_creation_with_multiplexer(self):
        """
        Test checks creation of multiplexer pinout widget with multiplexer.
        """

        app = QApplication(sys.argv)
        number_of_modules = 3
        chain = [ModuleTypes.MODULE_TYPE_A for _ in range(number_of_modules)]
        multiplexer_pinout_widget = MultiplexerPinoutWidget()
        multiplexer_pinout_widget.update_info(True, chain, None)
        self.assertEqual(len(multiplexer_pinout_widget._modules), number_of_modules)
        app.exit(0)
