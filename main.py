import logging
import sys
import traceback
from argparse import ArgumentParser, Namespace
from PyQt5.QtWidgets import (qApp, QApplication, QDesktopWidget, QLabel, QMainWindow, QPushButton,
                             QVBoxLayout, QWidget)
from epcore.product import EyePointProduct
from mainwindow import EPLabWindow, show_exception
from utils import read_json


def exception_hook(exc_type: Exception, exc_value: Exception, exc_traceback: "traceback"):
    """
    Function handles unexpected errors.
    :param exc_type: exception class;
    :param exc_value: exception instance;
    :param exc_traceback: traceback object.
    """

    traceback.print_exception(exc_type, exc_value, exc_traceback)
    traceback_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    show_exception("Error", str(exc_value), traceback_text)
    sys.exit(1)


sys.excepthook = exception_hook


def launch_eplab(app: QApplication, args: Namespace):
    """
    Function to launch application.
    :param app:
    :param args: arguments from command line.
    """

    window = EPLabWindow(EyePointProduct(read_json(args.config)), args.test, args.ref, args.en)
    window.resize(1200, 600)
    window.show()
    app.exec()


class ErrorWindow(QMainWindow):
    """
    Window with error message with traceback.
    """

    MAX_MESSAGE_LENGTH = 500

    def __init__(self, exc_type: Exception, exc_value: Exception, exc_traceback: "traceback"):
        """
        :param exc_type: type of exception;
        :param exc_value: exception instance;
        :param exc_traceback: traceback object which encapsulates the call stack at
        the point where the exception originally occurred.
        """

        super().__init__()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        traceback_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self._init_ui(str(exc_value), traceback_text)

    def _init_ui(self, error: str, trace_back: str):
        """
        Method initializes widgets on window.
        :param error: text of exception instance;
        :param trace_back: full text of traceback.
        """

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        exit_btn = QPushButton("OK",  self)
        error_lbl = QLabel(self)
        traceback_lbl = QLabel(self)
        error_lbl.setText(error[-self.MAX_MESSAGE_LENGTH:])
        traceback_lbl.setText(trace_back[-self.MAX_MESSAGE_LENGTH:])
        self.v_box = QVBoxLayout(self.central_widget)
        self.v_box.addWidget(error_lbl)
        self.v_box.addWidget(traceback_lbl)
        self.v_box.addWidget(exit_btn)
        exit_btn.clicked.connect(qApp.quit)
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle = self.frameGeometry()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())
        self.setWindowTitle("Error")


def show_error_window(app: QApplication, exc_type: Exception, exc_value: Exception,
                      exc_traceback: "traceback"):
    """
    Function shows window with error.
    :param app: application;
    :param exc_type: type of exception;
    :param exc_value: exception instance;
    :param exc_traceback: traceback object which encapsulates the call stack at
    the point where the exception originally occurred.
    """

    error_window = ErrorWindow(exc_type, exc_value, exc_traceback)
    error_window.show()
    app.exec_()


if __name__ == "__main__":
    parser = ArgumentParser(description="EyePoint Lab")
    parser.add_argument("--ref", help="Path to REF [additional] measurer (type 'virtual'"
                                      " for virtual mode)")
    parser.add_argument("test", help="Path to TEST measurer (type 'virtual' for virtual mode)",
                        nargs="?", default=None)
    parser.add_argument("--en", help="Use English version", action="store_true")
    parser.add_argument("--config", help="Path to specific EPLab config file", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    app = QApplication(sys.argv)
    try:
        launch_eplab(app, args)
    except Exception:
        show_error_window(app, *sys.exc_info())
