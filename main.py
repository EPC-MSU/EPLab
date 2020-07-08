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
        ivm_1 = IVMeasurerVirtual()
        ivm_1.nominal = 1000
        measurers.append(ivm_1)
    elif "com:" in args.test:
        ivm_1 = IVMeasurerIVM10(args.test, defer_open=True)
        measurers.append(ivm_1)

    if args.ref:
        if args.ref == "virtual":
            ivm_2 = IVMeasurerVirtual()
            measurers.append(ivm_2)
        elif "com:" in args.ref:
            ivm_2 = IVMeasurerIVM10(args.ref, defer_open=True)
            measurers.append(ivm_2)

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
        for i in range(len(measurers)):
            try:
                measurers[i].open_device()
                ivm_info.append(measurers[i].get_identity_information())
            finally:
                measurers[i].close_device()

        if (ivm_info[0].rank == 1 and
                ivm_info[1].rank == 2):
            ivm_0 = measurers[0]
            ivm_1 = measurers[1]
            measurers = [ivm_1, ivm_0]

    # Set pretty names for measurers
    measurers[0]._name = "test"
    if len(measurers) == 2:
        measurers[1]._name = "ref"

    measurement_system = MeasurementSystem(measurers)

    window = EPLabWindow(measurement_system)
    window.resize(1200, 600)
    window.show()

    app.exec()
