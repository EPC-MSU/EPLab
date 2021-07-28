import logging
import os
import sys
import traceback
from argparse import ArgumentParser
from PyQt5.QtCore import QTranslator
from PyQt5.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QLabel, qApp,
                             QApplication, QWidget, QDesktopWidget)
from epcore.ivmeasurer import (IVMeasurerASA, IVMeasurerIVM10, IVMeasurerVirtual,
                               IVMeasurerVirtualASA)
from epcore.measurementmanager import MeasurementSystem
from epcore.product import EPLab
from language import Language
from mainwindow import EPLabWindow, show_exception
from utils import read_json, sort_devices_by_usb_numbers


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


def launch_eplab(app: QApplication, args):

    if args.en:
        translator = QTranslator()
        translator.load("gui/super_translate_en.qm")
        app.installTranslator(translator)
        app.setProperty("language", Language.en)
    else:
        app.setProperty("language", Language.ru)

    measurers = []
    measurers_args = (args.test, args.ref)
    for measurer_arg in measurers_args:
        if measurer_arg == "virtual":
            measurer = IVMeasurerVirtual()
            measurer.nominal = 1000
            measurers.append(measurer)
        elif measurer_arg == "virtualasa":
            measurer = IVMeasurerVirtualASA(defer_open=True)
            measurers.append(measurer)
        elif measurer_arg is not None and "com:" in measurer_arg:
            measurer = IVMeasurerIVM10(measurer_arg, config=os.path.abspath("cur.ini"),
                                       defer_open=True)
            measurers.append(measurer)
        elif measurer_arg is not None and "xmlrpc:" in measurer_arg:
            measurer = IVMeasurerASA(measurer_arg, defer_open=True)
            measurers.append(measurer)

    if len(measurers) == 0:
        # Logically it will be correctly to abort here.
        # But for better user experience we will add single virtual IVM.
        ivm_1 = IVMeasurerVirtual()
        measurers.append(ivm_1)
    elif len(measurers) == 2:
        # Reorder measurers according to their addresses in USB hubs tree
        measurers = sort_devices_by_usb_numbers(measurers)

    # Set pretty names for measurers
    measurers[0].name = "test"
    if len(measurers) == 2:
        measurers[1].name = "ref"

    measurement_system = MeasurementSystem(measurers)

    window = EPLabWindow(measurement_system, EPLab(read_json(args.config)))
    window.resize(1200, 600)
    window.show()
    app.exec()


class ErrorWindow(QMainWindow):
    """
    Window with error message with traceback
    """

    def __init__(self, error: str, trace_back: str):
        super().__init__()
        self.init_ui(error, trace_back)

    def init_ui(self, error: str, trace_back: str):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        exit_btn = QPushButton("OK",  self)
        error_lbl = QLabel(self)
        traceback_lbl = QLabel(self)
        error_lbl.setText(error)
        traceback_lbl.setText(trace_back)
        self.v = QVBoxLayout(self.central_widget)
        self.v.addWidget(error_lbl)
        self.v.addWidget(traceback_lbl)
        self.v.addWidget(exit_btn)
        exit_btn.clicked.connect(qApp.quit)
        center_point = QDesktopWidget().availableGeometry().center()
        qt_rectangle = self.frameGeometry()
        qt_rectangle.moveCenter(center_point)
        self.move(qt_rectangle.topLeft())
        self.setWindowTitle("Error")


def start_err_app(app: QApplication, error: str = "", trace_back: str = ""):
    print(error)
    error_window = ErrorWindow(error, trace_back)
    error_window.show()
    app.exec_()


if __name__ == "__main__":
    parser = ArgumentParser(description="EyePoint Lab")
    parser.add_argument("--ref", help="Path to REF [additional] measurer (type 'virtual'"
                                      " for virtual mode)")
    parser.add_argument("test", help="Path to TEST measurer (type 'virtual' for virtual mode)")
    parser.add_argument("--en", help="Use English version", action="store_true")
    parser.add_argument("--config", help="Path to specific EPLab config file", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)

    app = QApplication(sys.argv)
    try:
        launch_eplab(app, args)
    except Exception as exc:
        start_err_app(app, error=str(exc),
                      trace_back="".join(traceback.format_exception(*sys.exc_info())))
