from typing import Callable, Optional, Tuple, Union
from PyQt5.QtCore import QCoreApplication as qApp
from epcore.analogmultiplexer.base import AnalogMultiplexerBase, MAX_CHANNEL_NUMBER
from epcore.elements import Board, Element, MultiplexerOutput, Pin
from epcore.ivmeasurer import IVMeasurerBase
from epcore.measurementmanager import MeasurementPlan, MeasurementSystem
from epcore.product import EyePointProduct
from . import utils as ut


class InvalidPinsForMuxError(Exception):
    """
    The exception to throw when there are points in the measurement plan that have invalid outputs for the multiplexer.
    """

    def __init__(self) -> None:
        self.text: str = qApp.translate("t", "В плане тестирования заданы неверные номера выходов мультиплексора.")


class PinsWithoutMuxOutputsError(Exception):
    """
    The exception to throw when there are points in the measurement plan for which the multiplexer output is not
    specified.
    """

    def __init__(self) -> None:
        self.text: str = qApp.translate("t", "В плане тестирования не заданы номера каналов мультиплексора. Вероятно, "
                                             "вы открыли план, созданный с помощью ручного устройства на устройстве с "
                                             "мультиплексором. Мультиплексор может использоваться только с планами "
                                             "тестирования, в которых заданы номера каналов.")


class WrongPinsNumberForMuxError(Exception):
    """
    The exception to throw when the number of points in the measurement plan does not match the number of outputs in
    the multiplexer.
    """

    def __init__(self, mux_outputs: int, plan: Optional[MeasurementPlan]) -> None:
        """
        :param mux_outputs:
        :param plan:
        """

        super().__init__()
        pins_number = 0 if plan is None else plan.pins_number
        self.text: str = qApp.translate("t", "Подключен мультиплексор с {} выходами. План с {} точками не совместим с "
                                             "данным мультиплексором. Количество точек в плане должно совпадать с "
                                             "количеством выходов мультиплексора.").format(mux_outputs, pins_number)


def update_plan_for_measurement_system(func: Callable[..., Tuple[MeasurementPlan, bool]]):
    """
    Method updates the measurer and multiplexer in the measurement plan for the current measurement system.
    :return: updated plan.
    """

    def wrapper(self, *args, **kwargs) -> Tuple[MeasurementPlan, bool]:
        plan, new_file_created = func(self, *args, **kwargs)
        board = Board(elements=plan.elements, image=plan.image if plan else None)
        return self.create_plan_with_measurer_and_mux(board), new_file_created

    return wrapper


class PlanCompatibility:
    """
    Class for checking the plan for compatibility with the product and multiplexer.
    There was already a measurement plan conversion, but it was removed in #94274.
    """

    def __init__(self, main_window, measurement_system: MeasurementSystem, product: EyePointProduct) -> None:
        """
        :param main_window: main window of application;
        :param measurement_system: measurement system;
        :param product: product.
        """

        self._measurement_system: MeasurementSystem = measurement_system
        self._parent = main_window
        self._product: EyePointProduct = product

    @property
    def measurer(self) -> Optional[IVMeasurerBase]:
        """
        :return: measurer in measurement system.
        """

        if self._measurement_system and self._measurement_system.measurers:
            return self._measurement_system.measurers[0]
        return None

    @property
    def multiplexer(self) -> Optional[AnalogMultiplexerBase]:
        """
        :return: multiplexer in measurement system.
        """

        if self._measurement_system and self._measurement_system.multiplexers:
            return self._measurement_system.multiplexers[0]
        return None

    def _check_compatibility_with_mux(self, plan: MeasurementPlan) -> None:
        """
        Method checks the plan for compatibility with the multiplexer.
        :param plan: plan to check for compatibility.
        """

        multiplexer = self.multiplexer
        modules = len(multiplexer.get_chain_info())
        if not plan or modules * MAX_CHANNEL_NUMBER != plan.pins_number:
            raise WrongPinsNumberForMuxError(modules * MAX_CHANNEL_NUMBER, plan)

        channels = {module: {channel: [] for channel in range(1, MAX_CHANNEL_NUMBER + 1)}
                    for module in range(1, modules + 1)}
        empty_pins = []
        invalid_pins = []
        for element_index, element in enumerate(plan.elements):
            for pin_index, pin in enumerate(element.pins):
                mux_output = pin.multiplexer_output
                if isinstance(mux_output, MultiplexerOutput):
                    if multiplexer.is_correct_output(mux_output):
                        channels[mux_output.module_number][mux_output.channel_number].append(
                            (element_index, pin_index))
                    else:
                        invalid_pins.append((element_index, pin_index))
                else:
                    empty_pins.append((element_index, pin_index))

        if len(empty_pins) != 0:
            raise PinsWithoutMuxOutputsError()

        if len(invalid_pins) != 0:
            raise InvalidPinsForMuxError()

        for channels_in_module in channels.values():
            if not all(len(channels_) > 0 for channels_ in channels_in_module.values()):
                raise InvalidPinsForMuxError()

    def _check_compatibility_with_product(self, plan: MeasurementPlan) -> bool:
        """
        Method checks the plan for compatibility with the product (available measurement settings).
        :param plan: plan to check for compatibility.
        :return: True if the plan is compatible, otherwise not.
        """

        for element in plan.elements:
            for pin in element.pins:
                for measurement in pin.measurements:
                    try:
                        if len(self._product.settings_to_options(measurement.settings)) < 3:
                            return False
                    except Exception:
                        return False
        return True

    def _close_mux(self) -> None:
        """
        Method closes the multiplexer.
        """

        for multiplexer in self._measurement_system.multiplexers:
            multiplexer.close_device()
        self._measurement_system.multiplexers = []

    def _create_plan_for_mux(self) -> MeasurementPlan:
        """
        Method creates an empty measurement plan for the connected multiplexer.
        :return: empty plan for the connected multiplexer.
        """

        modules = len(self.multiplexer.get_chain_info())
        pins = []
        x, y = self._parent.get_default_pin_coordinates()
        for module in range(1, modules + 1):
            for channel in range(1, MAX_CHANNEL_NUMBER + 1):
                mux_output = MultiplexerOutput(channel, module)
                pins.append(Pin(x=x, y=y, multiplexer_output=mux_output))

        board = Board(elements=[Element(pins=pins)])
        return self.create_plan_with_measurer_and_mux(board)

    def _create_plan_without_mux(self) -> MeasurementPlan:
        """
        Method creates an empty measurement plan without multiplexer.
        :return: empty plan.
        """

        x, y = self._parent.get_default_pin_coordinates()
        board = Board(elements=[Element(pins=[Pin(x=x, y=y)])])
        return self.create_plan_with_measurer_and_mux(board)

    @staticmethod
    def _display_incompatibility_with_mux(exc: Union[InvalidPinsForMuxError, PinsWithoutMuxOutputsError,
                                                     WrongPinsNumberForMuxError], is_new_plan: bool) -> None:
        """
        :param exc: exception;
        :param is_new_plan: if True, then the new measurement plan was checked for compatibility.
        """

        if is_new_plan:
            error = qApp.translate("t", "Нажмите 'ОК' и откройте подходящий план тестирования.")
        else:
            error = qApp.translate("t", "Мультиплексор будет закрыт.")
        ut.show_message(qApp.translate("t", "Ошибка"), exc.text, additional_info=error)

    @staticmethod
    def _display_incompatibility_with_product(is_new_plan: bool, filename: str) -> None:
        """
        :param is_new_plan: if True, then the new test plan was checked for compatibility;
        :param filename: name of the measurement plan file.
        """

        if is_new_plan:
            error = qApp.translate("t", "План тестирования {}нельзя загрузить, поскольку он не соответствует режиму "
                                        "работы EPLab.")
        else:
            error = qApp.translate("t", "План тестирования {}не соответствует режиму работы EPLab и будет закрыт.")
        error = error.format(f"'{filename}' " if filename else "")
        ut.show_message(qApp.translate("t", "Ошибка"), error)

    def create_plan_with_measurer_and_mux(self, board: Board) -> MeasurementPlan:
        """
        :param board: board for new measurement plan.
        :return: new measurement plan.
        """

        return MeasurementPlan(board, self.measurer, self.multiplexer)

    @update_plan_for_measurement_system
    def get_compatible_plan(self, plan: MeasurementPlan, is_new_plan: bool, filename: str
                            ) -> Tuple[MeasurementPlan, bool]:
        """
        Method checks the measurement plan for compatibility with the product (available measurement settings) and
        multiplexer.
        :param plan: measurement plan that is checked for compatibility;
        :param is_new_plan: if True, then the new measurement plan will be checked for compatibility;
        :param filename: name of the measurement plan file.
        :return: compatible measurement plan and True if a new plan is created.
        """

        if not self._measurement_system:
            return plan, False

        if not self._check_compatibility_with_product(plan):
            self._display_incompatibility_with_product(is_new_plan, filename)
            plan = self._create_plan_without_mux()
            new_plan_created = True
        else:
            new_plan_created = False

        if not self.multiplexer:
            return plan, new_plan_created

        try:
            self._check_compatibility_with_mux(plan)
        except (InvalidPinsForMuxError, PinsWithoutMuxOutputsError, WrongPinsNumberForMuxError) as exc:
            if not (new_plan_created or not filename):
                self._display_incompatibility_with_mux(exc, is_new_plan)
        else:
            return plan, new_plan_created

        if is_new_plan:
            plan = self._create_plan_for_mux()
            new_plan_created = True
        else:
            self._close_mux()

        return plan, new_plan_created
