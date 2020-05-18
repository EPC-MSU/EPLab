from PyQt5.QtWidgets import QApplication
import sys
import logging
from epcore.ivmeasurer import IVMeasurerVirtual
from epcore.measurementmanager import MeasurementSystem

from mainwindow import EPLabWindow


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)

    app = QApplication(sys.argv)

    ivm1 = IVMeasurerVirtual()
    ivm2 = IVMeasurerVirtual()
    measurement_system = MeasurementSystem([ivm1, ivm2])

    window = EPLabWindow(measurement_system)
    window.resize(1200, 600)
    window.show()

    app.exec()
