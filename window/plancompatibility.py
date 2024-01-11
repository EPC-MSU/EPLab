import os
from collections import namedtuple
from enum import auto, IntEnum
from typing import Dict, List, Optional, Tuple
from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox
from epcore.analogmultiplexer.base import MAX_CHANNEL_NUMBER
from epcore.elements import Board, Element, MultiplexerOutput, Pin
from epcore.measurementmanager import MeasurementPlan, MeasurementSystem
from epcore.product import EyePointProduct
from window import utils as ut


class PlanCompatibility:
    """
    Class for checking the plan for compatibility with the product and multiplexer.
    """

    AnalyzedData = namedtuple("AnalyzedData", ["channels", "empty", "extra"])

    class Action(IntEnum):
        """
        Class listing possible actions to correct incompatibility with the multiplexer.
        """

        CLOSE_MUX = auto()
        CLOSE_PLAN = auto()
        TRANSFORM = auto()

    def __init__(self, main_window, measurement_system: MeasurementSystem, product: EyePointProduct,
                 plan: MeasurementPlan) -> None:
        """
        :param main_window: main window of application;
        :param measurement_system: measurement system;
        :param product: product;
        :param plan: measurement plan to check.
        """

        self._measurement_system: MeasurementSystem = measurement_system
        self._parent = main_window
        self._plan: MeasurementPlan = plan
        self._product: EyePointProduct = product

    def _check_compatibility_with_mux(self) -> Tuple[bool, "PlanCompatibility.AnalyzedData"]:
        """
        Method checks the plan for compatibility with the multiplexer.
        :return: True if the plan is compatible, otherwise not. Data is also returned about empty pins (in which
        there is no multiplexer output), pins that have incorrect multiplexer outputs.
        """

        multiplexer = self._measurement_system.multiplexers[0]
        modules = len(multiplexer.get_chain_info())
        channels = {module: {channel: [] for channel in range(1, MAX_CHANNEL_NUMBER + 1)}
                    for module in range(1, modules + 1)}
        empty_pins = []
        extra_pins = []

        if self._plan:
            index = 0
            for element in self._plan.elements:
                for pin in element.pins:
                    mux_output = pin.multiplexer_output
                    if isinstance(mux_output, MultiplexerOutput):
                        if multiplexer.is_correct_output(mux_output):
                            channels[mux_output.module_number][mux_output.channel_number].append(index)
                        else:
                            extra_pins.append(index)
                    else:
                        empty_pins.append(index)
                    index += 1

        extra_pins.reverse()
        data = self.AnalyzedData(channels, empty_pins, extra_pins)
        if len(empty_pins) == 0 and len(extra_pins) == 0:
            for channels_in_module in channels.values():
                if not all(len(channels_) > 0 for channels_ in channels_in_module.values()):
                    break
            else:
                return True, data

        return False, data

    def _check_compatibility_with_product(self) -> bool:
        """
        Method checks the plan for compatibility with the product (available measurement settings).
        :return: True if the plan is compatible, otherwise not.
        """

        for element in self._plan.elements:
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

    def _create_new_plan(self, board: Board) -> MeasurementPlan:
        """
        :param board: board for new measurement plan or new board.
        :return: new measurement plan.
        """

        measurer = self._measurement_system.measurers[0]
        multiplexer = self._measurement_system.multiplexers[0]
        return MeasurementPlan(board, measurer, multiplexer)

    def _create_plan_for_mux(self) -> MeasurementPlan:
        """
        Method creates an empty measurement plan for the connected multiplexer.
        :return: empty plan.
        """

        multiplexer = self._measurement_system.multiplexers[0]
        modules = len(multiplexer.get_chain_info())
        x, y = self._parent.get_default_pin_coordinates()
        pins = []
        for module in range(1, modules + 1):
            for channel in range(1, MAX_CHANNEL_NUMBER + 1):
                pins.append(Pin(x=x, y=y, multiplexer_output=MultiplexerOutput(channel, module)))
        board = Board(elements=[Element(pins=pins)], image=self._plan.image if self._plan else None)
        return self._create_new_plan(board)

    def _transform_plan(self, data: "PlanCompatibility.AnalyzedData") -> MeasurementPlan:
        """
        Method transforms the plan to be compatible with the multiplexer.
        :param data:
        :return: transformed plan.
        """

        elements = self._plan.elements
        remove_extra_points(elements, data.extra)
        add_points(elements, data.channels, len(data.empty))
        set_mux_output(elements, data.channels)
        board = Board(elements=elements, image=self._plan.image)
        return self._create_new_plan(board)

    def check_compatibility(self, new_plan: bool, empty_plan: bool, filename: str) -> Optional[MeasurementPlan]:
        """
        Method checks the measurement plan for compatibility with the product (available measurement settings) and
        multiplexer.
        :param new_plan: if True, then the new measurement plan will be checked for compatibility;
        :param empty_plan:
        :param filename: name of the measurement plan file.
        :return: verified measurement plan or None if the plan did not pass the test.
        """

        self._plan = self.check_compatibility_with_product(new_plan, filename)
        return self.check_compatibility_with_mux(empty_plan)

    def check_compatibility_with_mux(self, empty_plan: bool) -> Optional[MeasurementPlan]:
        """
        Method checks the measurement plan for compatibility with the multiplexer.
        :param empty_plan:
        :return: verified measurement plan or None if the plan did not pass the test.
        """

        if not self._measurement_system or not self._measurement_system.multiplexers:
            return self._plan

        compatible, data = self._check_compatibility_with_mux()
        if compatible:
            return self._plan

        if empty_plan:
            action = PlanCompatibility.Action.TRANSFORM
        elif self._plan is None:
            action = PlanCompatibility.Action.CLOSE_PLAN
        else:
            action = show_warning_incompatibility_with_mux()

        if action == PlanCompatibility.Action.TRANSFORM:
            plan = self._transform_plan(data)
        elif action == PlanCompatibility.Action.CLOSE_PLAN:
            plan = self._create_plan_for_mux()
        elif action == PlanCompatibility.Action.CLOSE_MUX:
            self._close_mux()
            plan = self._plan
        else:
            plan = self._plan
        return plan

    def check_compatibility_with_product(self, new_plan: bool, filename: str) -> Optional[MeasurementPlan]:
        """
        Method checks the plan for compatibility with the product (available measurement settings).
        :param new_plan: if True, then the new measurement plan (that to be loaded) will be checked for compatibility;
        :param filename: name of the measurement plan file.
        :return: verified measurement plan or None if the plan did not pass the test.
        """

        if self._measurement_system and not self._check_compatibility_with_product():
            show_warning_incompatibility_with_product(new_plan, filename)
            plan = None
        else:
            plan = self._plan
        return plan


def add_points(elements: List[Element], channels: Dict[int, Dict[int, List[int]]], empty: int) -> None:
    """
    Function adds a given number of points to the list of points on the board.
    :param elements: list of elements on the board;
    :param channels: dictionary with point indices that correspond to the corresponding numbers of the module and
    channel of the multiplexer;
    :param empty: number of points where there are no multiplexer outputs.
    """

    element = elements[-1] if len(elements) > 0 else Element(pins=[])
    x, y = 0, 0
    for modules in channels.values():
        for module_channels in modules.values():
            if len(module_channels) == 0:
                if empty > 0:
                    empty -= 1
                else:
                    element.pins.append(Pin(x=x, y=y))


def get_free_mux_output(channels: Dict[int, Dict[int, List[int]]], index: int) -> Optional[Tuple[int, int]]:
    """
    Function returns the free output of the multiplexer.
    :param channels:
    :param index: index of the point for which to return the multiplexer output.
    :return: channel and module numbers of multiplexer output.
    """

    for module in range(1, len(channels) + 1):
        module_channels = channels[module]
        for channel in range(1, MAX_CHANNEL_NUMBER + 1):
            if len(module_channels[channel]) == 0:
                module_channels[channel].append(index)
                return channel, module
    return None


def remove_extra_points(elements: List[Element], extra: List[int]) -> None:
    """
    Function removes points with invalid multiplexer outputs.
    :param elements: list of board elements;
    :param extra: list with indices of points that have incorrect multiplexer outputs.
    """

    for index in sorted(extra, reverse=True):
        remove_point(elements, index)


def remove_point(elements: List[Element], index: int) -> None:
    """
    Function removes a point from the list of points.
    :param elements: list of board elements;
    :param index: index of the point to be deleted.
    """

    pin_index = 0
    for element in elements:
        for i, _ in enumerate(element.pins):
            if pin_index == index:
                element.pins.pop(i)
                return


def set_mux_output(elements: List[Element], channels: Dict[int, Dict[int, List[int]]]) -> None:
    """
    Function sets multiplexer outputs to points where there are no outputs.
    :param elements: list of board elements;
    :param channels:
    """

    index = 0
    mux_outputs = set()
    for element in elements:
        for pin in element.pins:
            if pin.multiplexer_output is None:
                channel_and_module = get_free_mux_output(channels, index)
                if channel_and_module is None:
                    continue
                pin.multiplexer_output = MultiplexerOutput(*channel_and_module)
                mux_outputs.add(channel_and_module)
            index += 1


def show_warning_incompatibility_with_mux() -> int:
    """
    Function displays a message stating that the plan is incompatible with the multiplexer and suggests possible
    actions.
    """

    message_box = QMessageBox()
    message_box.setWindowTitle(qApp.translate("t", "Ошибка"))
    message_box.setWindowIcon(QIcon(os.path.join(ut.DIR_MEDIA, "icon.png")))
    message_box.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowTitleHint)
    message_box.setIcon(QMessageBox.Warning)
    message_box.setTextFormat(Qt.RichText)
    message_box.setTextInteractionFlags(Qt.TextBrowserInteraction)
    message = qApp.translate("t", "Текущий план тестирования несовместим с подключенным мультиплексором. Для "
                                  "продолжения работы можно выполнить одно из следующих действий:"
                                  "<ul>"
                                  "<li>Преобразовать план тестирования для обеспечения совместимости. Если число "
                                  "точек меньше числа каналов, то план будет дополнен новыми точками. Если число "
                                  "точек больше числа каналов, то лишние точки будут удалены из плана.</li>"
                                  "<li>Закрыть текущий план тестирования. После этого можно будет создать новый или"
                                  " открыть другой план тестирования.</li>"
                                  "<li>Отключить мультиплексор.</li>")
    message_box.setText(message)

    buttons = dict()
    for name, action, role in zip((qApp.translate("t", "Преобразовать"),
                                   qApp.translate("t", "Закрыть план тестирования"),
                                   qApp.translate("t", "Отключить мультиплексор")),
                                  (PlanCompatibility.Action.TRANSFORM, PlanCompatibility.Action.CLOSE_PLAN,
                                   PlanCompatibility.Action.CLOSE_MUX),
                                  (QMessageBox.AcceptRole, QMessageBox.NoRole, QMessageBox.ApplyRole)):
        buttons[message_box.addButton(name, role)] = action
    message_box.exec()
    clicked_button = message_box.clickedButton()
    return buttons.get(clicked_button, PlanCompatibility.Action.CLOSE_PLAN)


def show_warning_incompatibility_with_product(new_plan: bool, filename: str) -> None:
    """
    Function displays a message stating that the plan is incompatible with the product.
    :param new_plan: True if the new plan (that to be loaded) needs to be checked. Otherwise, the already loaded plan
    needs to be checked;
    :param filename: name of the measurement plan file.
    """

    if new_plan:
        error = qApp.translate("t", "План тестирования {}нельзя загрузить, поскольку он не соответствует режиму "
                                    "работы EPLab.")
    else:
        error = qApp.translate("t", "План тестирования {}не соответствует режиму работы EPLab и будет закрыт.")
    error = error.format(f"'{filename}' " if filename else "")
    ut.show_message(qApp.translate("t", "Ошибка"), error)
