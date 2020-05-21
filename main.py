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
    parser.add_argument("--en", help="Use English version", action="store_true")
    parser.add_argument("-a", help="Path to measurer A", default="virtual")
    parser.add_argument("-b", help="Path to measurer B", default="virtual")
    args = parser.parse_args()

    logging.basicConfig(level=logging.ERROR)

    app = QApplication(sys.argv)

    if args.en:
        translator = QTranslator()
        translator.load("gui/super_translate_en.qm")
        app.installTranslator(translator)

    if args.a == "virtual":
        ivm1 = IVMeasurerVirtual()
    else:
        ivm1 = IVMeasurerIVM10(args.a)
    if args.b == "virtual":
        ivm2 = IVMeasurerVirtual()
    else:
        ivm2 = IVMeasurerIVM10(args.b)

    measurement_system = MeasurementSystem([ivm1, ivm2])

    window = EPLabWindow(measurement_system)
    window.resize(1200, 600)
    window.show()

    app.exec()
