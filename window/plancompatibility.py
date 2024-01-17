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

    AnalyzedData = namedtuple("AnalyzedData", ["channels", "empty", "invalid"])

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

    def _add_points(self, elements: List[Element], channels: Dict[int, Dict[int, List[int]]],
                    empty: List[Tuple[int, int]]) -> None:
        """
        Method adds a given number of points to the list of points on the board.
        :param elements: list of elements on the board;
        :param channels: dictionary with point indices that correspond to the corresponding numbers of the module and
        channel of the multiplexer;
        :param empty: list with indices of points where there are no multiplexer outputs.
        """

        if len(elements) == 0:
            elements.append(Element(pins=[]))
        element = elements[-1]

        x, y = self._parent.get_default_pin_coordinates()
        for module in sorted(channels):
            channels_in_module = channels[module]
            for channel in sorted(channels_in_module):
                if len(channels_in_module[channel]) == 0:
                    mux_output = MultiplexerOutput(channel, module)
                    if len(empty) == 0:
                        element.pins.append(Pin(x=x, y=y, multiplexer_output=mux_output))
                    else:
                        element_index, pin_index = empty.pop()
                        elements[element_index].pins[pin_index].multiplexer_output = mux_output

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
        invalid_pins = []

        if self._plan:
            for element_index, element in enumerate(self._plan.elements):
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

        empty_pins.reverse()
        invalid_pins.reverse()
        data = self.AnalyzedData(channels, empty_pins, invalid_pins)
        if len(empty_pins) == 0 and len(invalid_pins) == 0:
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

        elements = []
        multiplexer = self._measurement_system.multiplexers[0]
        modules = len(multiplexer.get_chain_info())
        channels = {module: {channel: [] for channel in range(1, MAX_CHANNEL_NUMBER + 1)}
                    for module in range(1, modules + 1)}
        self._add_points(elements, channels, [])
        board = Board(elements=elements, image=self._plan.image if self._plan else None)
        return self._create_new_plan(board)

    @staticmethod
    def _remove_invalid_points(elements: List[Element], invalid: List[Tuple[int, int]]) -> None:
        """
        Method removes points with invalid multiplexer outputs.
        :param elements: list of board elements;
        :param invalid: list with indices of points that have incorrect multiplexer outputs.
        """

        for element_index, pin_index in invalid:
            element = elements[element_index]
            element.pins.pop(pin_index)
            if len(element.pins) == 0:
                elements.pop(element_index)

    def _transform_plan(self, data: "PlanCompatibility.AnalyzedData") -> MeasurementPlan:
        """
        Method transforms the plan to be compatible with the multiplexer.
        :param data:
        :return: transformed plan.
        """

        elements = self._plan.elements
        self._add_points(elements, data.channels, data.empty)
        self._remove_invalid_points(elements, data.invalid)
        board = Board(elements=elements, image=self._plan.image)
        return self._create_new_plan(board)

    def check_compatibility(self, new_plan: bool, empty_plan: bool, filename: str) -> Optional[MeasurementPlan]:
        """
        Method checks the measurement plan for compatibility with the product (available measurement settings) and
        multiplexer.
        :param new_plan: if True, then the new measurement plan will be checked for compatibility;
        :param empty_plan: if True, then the measurement plan is empty;
        :param filename: name of the measurement plan file.
        :return: verified measurement plan or None if the plan did not pass the test.
        """

        self._plan = self.check_compatibility_with_product(new_plan, filename)
        return self.check_compatibility_with_mux(empty_plan)

    def check_compatibility_with_mux(self, empty_plan: bool) -> Optional[MeasurementPlan]:
        """
        Method checks the measurement plan for compatibility with the multiplexer.
        :param empty_plan: if True, then the measurement plan is empty.
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
            plan.multiplexer = None
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
                                  "<li>Отключить мультиплексор.</li>"
                                  "</ul>")
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
