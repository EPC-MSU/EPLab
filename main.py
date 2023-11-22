import importlib.util
import os
import sys
import traceback
from argparse import ArgumentParser, Namespace
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import qApp, QApplication, QDesktopWidget, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget
from epcore.product import EyePointProduct
from window import utils as ut
from window.eplabwindow import EPLabWindow
from window.logger import set_logger


QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # enable high dpi scaling
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # use highdpi icons


if "_PYIBoot_SPLASH" in os.environ and importlib.util.find_spec("pyi_splash"):
    import pyi_splash
    pyi_splash.close()


def exception_hook(exc_type: Exception, exc_value: Exception, exc_traceback: "traceback"):
    """
    Function handles unexpected errors.
    :param exc_type: exception class;
    :param exc_value: exception instance;
    :param exc_traceback: traceback object.
    """

    traceback.print_exception(exc_type, exc_value, exc_traceback)
    traceback_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    ut.show_message("Error", str(exc_value), traceback_text)
    # sys.exit(1)


sys.excepthook = exception_hook


def launch_eplab(app: QApplication, args: Namespace) -> None:
    """
    :param app: application;
    :param args: arguments from command line.
    """

    window = EPLabWindow(EyePointProduct(ut.read_json(args.config)), args.test, args.ref, args.en, args.plan_path)
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


def show_error_window(app: QApplication, exc_type: Exception, exc_value: Exception, exc_traceback: "traceback"):
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
    set_logger()

    parser = ArgumentParser(description="EyePoint Lab")
    parser.add_argument("plan_path", help="Path to the test plan to be opened", type=str, nargs="?", default=None)
    parser.add_argument("--config", help="Path to specific EPLab config file", default=None)
    parser.add_argument("--en", help="Use English version", action="store_true", default=False)
    parser.add_argument("--ref", help="Path to REF [additional] measurer (type 'virtual' for virtual mode)")
    parser.add_argument("--test", help="Path to TEST measurer (type 'virtual' for virtual mode)", default=None)
    parsed_args = parser.parse_args()

    app_ = QApplication(sys.argv)
    try:
        launch_eplab(app_, parsed_args)
    except Exception:
        show_error_window(app_, *sys.exc_info())
