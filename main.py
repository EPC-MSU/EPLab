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
from mainwindow import EPLabWindow
from utils import read_json

tb = None


def exception_hook(exc_type, exc_value, exc_tb):
    global tb
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    for f in app.allWindows():
        f.close()


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

    if len(measurers) == 2:
        # Reorder measurers according to their ranks if needed.
        # We swap IVMs only if both ranks are set correctly.
        # If ranks are not set order should be the same to the order of cmd args.
        ivm_info = []
        for measurer in measurers:
            try:
                measurer.open_device()
                ivm_info.append(measurer.get_identity_information())
            finally:
                measurer.close_device()
        if (ivm_info[0].rank == 1 and
                ivm_info[1].rank == 2):
            ivm_0 = measurers[0]
            ivm_1 = measurers[1]
            measurers = [ivm_1, ivm_0]

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
        self.initUI(error, trace_back)

    def initUI(self, error: str, trace_back: str):
        self.centralwidget = QWidget()
        self.setCentralWidget(self.centralwidget)
        exit_btn = QPushButton("OK",  self)
        error_lbl = QLabel(self)
        traceback_lbl = QLabel(self)
        error_lbl.setText(error)
        traceback_lbl.setText(trace_back)
        self.v = QVBoxLayout(self.centralwidget)
        self.v.addWidget(error_lbl)
        self.v.addWidget(traceback_lbl)
        self.v.addWidget(exit_btn)
        exit_btn.clicked.connect(qApp.quit)
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle = self.frameGeometry()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        self.setWindowTitle("Error")


def start_err_app(app: QApplication, error: str = "", trace_back: str = ""):
    print(error)
    ex = ErrorWindow(error, trace_back)
    ex.show()
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
        assert tb is None
    except AssertionError:
        start_err_app(app, trace_back=str(tb))
    except Exception as e:
        start_err_app(app, error=str(e), trace_back="".join(traceback.format_exception(*sys.exc_info())))
