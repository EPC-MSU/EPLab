from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTranslator
import sys
import logging
from argparse import ArgumentParser
from epcore.ivmeasurer import IVMeasurerVirtual
from epcore.measurementmanager import MeasurementSystem

from mainwindow import EPLabWindow


if __name__ == "__main__":

    parser = ArgumentParser(description="EyePoint Lab")
    parser.add_argument("--en", help="Use English version", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.ERROR)

    app = QApplication(sys.argv)

    if args.en:
        translator = QTranslator()
        translator.load("gui/super_translate_en.qm")
        app.installTranslator(translator)

    ivm1 = IVMeasurerVirtual()
    ivm2 = IVMeasurerVirtual()
    measurement_system = MeasurementSystem([ivm1, ivm2])

    window = EPLabWindow(measurement_system)
    window.resize(1200, 600)
    window.show()

    app.exec()
