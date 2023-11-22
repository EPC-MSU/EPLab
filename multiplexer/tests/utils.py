"""
File with function to  create dummy main window.
"""

from PyQt5.QtWidgets import QWidget
from epcore.analogmultiplexer import AnalogMultiplexerVirtual
from epcore.elements import Board, Element, Pin
from epcore.filemanager import load_board_from_ufiv
from epcore.ivmeasurer import IVMeasurerVirtual
from epcore.measurementmanager import MeasurementPlan
from epcore.product import EyePointProduct
from window.common import DeviceErrorsHandler, WorkMode


def create_dummy_main_window():
    """
    Function creates dummy main window for tests.
    :return: dummy main window.
    """

    class DummyMainWindow(QWidget):

        def __init__(self):
            super().__init__()
            self.device_errors_handler: DeviceErrorsHandler = DeviceErrorsHandler()
            self.measurer: IVMeasurerVirtual = IVMeasurerVirtual()
            self.multiplexer: AnalogMultiplexerVirtual = AnalogMultiplexerVirtual()
            board = Board(elements=[Element(pins=[Pin(x=0, y=0, measurements=[])])])
            self.measurement_plan: MeasurementPlan = MeasurementPlan(board, self.measurer, self.multiplexer)
            self.product: EyePointProduct = EyePointProduct()
            self.work_mode: WorkMode = WorkMode.COMPARE

        def go_to_selected_pin(self, _: int):
            pass

        def update_measurement_plan(self, path: str):
            board = load_board_from_ufiv(path, True)
            self.measurement_plan = MeasurementPlan(board, self.measurer)

    return DummyMainWindow()
