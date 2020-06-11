from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTranslator
import sys
import logging
from argparse import ArgumentParser
from epcore.ivmeasurer import IVMeasurerVirtual, IVMeasurerIVM10
from epcore.measurementmanager import MeasurementSystem

from mainwindow import EPLabWindow


if __name__ == "__main__":

    parser = ArgumentParser(description="EyePoint Lab")
    parser.add_argument("--ref", help="Path to REF [additional] measurer (type 'virtual' for virtual mode)")
    parser.add_argument("test", help="Path to TEST measurer (type 'virtual' for virtual mode)")
    parser.add_argument("--en", help="Use English version", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)

    app = QApplication(sys.argv)

    if args.en:
        translator = QTranslator()
        translator.load("gui/super_translate_en.qm")
        app.installTranslator(translator)

    measurers = []

    if args.test == "virtual":
        ivm_test = IVMeasurerVirtual(name="test")
        ivm_test.nominal = 1000
    else:
        ivm_test = IVMeasurerIVM10(args.test, name="test", defer_open=True)
    measurers.append(ivm_test)

    if args.ref:
        if args.ref == "virtual":
            ivm_ref = IVMeasurerVirtual(name="ref")
        else:
            ivm_ref = IVMeasurerIVM10(args.ref, name="ref", defer_open=True)
        measurers.append(ivm_ref)

    measurement_system = MeasurementSystem(measurers)

    window = EPLabWindow(measurement_system)
    window.resize(1200, 600)
    window.show()

    app.exec()
