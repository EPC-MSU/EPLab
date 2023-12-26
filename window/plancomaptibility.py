import os
from collections import namedtuple
from enum import auto, IntEnum
from typing import List, Optional, Tuple, Union
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

    def __init__(self, measurement_system: MeasurementSystem, product: EyePointProduct,
                 plan: Union[Board, MeasurementPlan], new_plan: bool, filename: str) -> None:
        """
        :param measurement_system: measurement system;
        :param product: product;
        :param plan: measurement plan to check;
        :param new_plan: True if the new measurement plan is checked. Otherwise, the already loaded plan with the
        newly connected IV-measurers and multiplexer is checked for compatibility;
        :param filename: file name of the measurement plan being checked.
        """

        self._filename: str = filename
        self._measurement_system: MeasurementSystem = measurement_system
        self._new_plan: bool = new_plan
        self._plan: Union[Board, MeasurementPlan] = plan
        self._product: EyePointProduct = product

    def _check_compatibility_with_mux(self) -> Tuple[bool, "PlanCompatibility.AnalyzedData"]:
        """
        Method checks the plan for compatibility with the multiplexer.
        :return: True if the plan is compatible, otherwise not.
        """

        multiplexer = self._measurement_system.multiplexers[0]
        modules = len(multiplexer.get_chain_info())
        channels = {module + 1: {channel + 1: [] for channel in range(MAX_CHANNEL_NUMBER)} for module in range(modules)}
        empty_points = []
        extra_points = []

        index = 0
        for element in self._plan.elements:
            for pin in element.pins:
                mux_output = pin.multiplexer_output
                if isinstance(mux_output, MultiplexerOutput):
                    if multiplexer.is_correct_output(mux_output):
                        channels[mux_output.module_number][mux_output.channel_number].append(index)
                    else:
                        extra_points.append(index)
                else:
                    empty_points.append(index)
                index += 1

        data = self.AnalyzedData(channels, empty_points, extra_points)
        if len(empty_points) == 0 and len(extra_points) == 0:
            for channels_in_module in channels.values():
                if not all(len(channels_) == 1 for channels_ in channels_in_module.values()):
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
                        options = self._product.settings_to_options(measurement.settings)
                        if len(options) < 3:
                            return False
                    except Exception:
                        return False
        return True

    def _create_new_plan(self, board: Board) -> Union[Board, MeasurementPlan]:
        if isinstance(self._plan, MeasurementPlan):
            measurer = self._measurement_system.measurers[0]
            multiplexer = self._measurement_system.multiplexers[0]
            plan = MeasurementPlan(board, measurer, multiplexer)
        else:
            plan = board
        return plan

    def _create_plan_for_mux(self) -> Union[Board, MeasurementPlan]:
        """
        Method creates an empty measurement plan for the connected multiplexer.
        :return: empty plan.
        """

        multiplexer = self._measurement_system.multiplexers[0]
        x, y = 0, 0
        pins = []
        for module, _ in enumerate(multiplexer.get_chain_info(), start=1):
            for channel in range(1, MAX_CHANNEL_NUMBER + 1):
                pins.append(Pin(x=x, y=y, multiplexer_output=MultiplexerOutput(channel, module)))
        board = Board(elements=[Element(pins=pins)], image=self._plan.image)
        return self._create_new_plan(board)

    @staticmethod
    def _show_warning_incompatibility_with_mux() -> int:
        """
        Method displays a message stating that the plan is incompatible with the multiplexer and suggests possible
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
        return buttons.get(clicked_button, None)

    def _show_warning_incompatibility_with_product(self) -> None:
        """
        Method displays a message stating that the plan is incompatible with the product.
        """

        if self._new_plan:
            error = qApp.translate("t", "План тестирования {}нельзя загрузить, поскольку он не соответствует режиму "
                                        "работы EPLab.")
        else:
            error = qApp.translate("t", "План тестирования {}не соответствует режиму работы EPLab и будет закрыт.")
        error = error.format(f"'{self._filename}' " if self._filename else "")
        ut.show_message(qApp.translate("t", "Ошибка"), error)

    def _transform_plan(self, data: "PlanCompatibility.AnalyzedData") -> Union[Board, MeasurementPlan]:
        """
        Method transforms the plan to be compatible with the multiplexer.
        :param data:
        :return: transformed plan.
        """

        elements = self._plan.elements
        total_points = sum([len(element.pins) for element in elements])
        mux_channels = len(data.channels) * MAX_CHANNEL_NUMBER
        if total_points > mux_channels:
            remove_extra_points(elements, data, total_points - mux_channels)
        elif total_points < mux_channels:
            add_points(elements, mux_channels - total_points)
        set_mux_output(elements, data)

        board = Board(elements=elements, image=self._plan.image)
        return self._create_new_plan(board)

    def check_compatibility(self) -> Optional[Union[Board, MeasurementPlan]]:
        """
        Method checks the measurement plan for compatibility.
        :return:
        """

        self._plan = self.check_compatibility_with_product()
        return self.check_compatibility_with_mux()

    def check_compatibility_with_mux(self) -> Optional[Union[Board, MeasurementPlan]]:
        """
        Method checks the measurement plan for compatibility with the multiplexer .
        :return: verified measurement plan or None if the plan did not pass the test.
        """

        if not self._measurement_system or not self._measurement_system.multiplexers:
            return self._plan

        compatible, data = self._check_compatibility_with_mux()
        if compatible:
            return self._plan

        action = self._show_warning_incompatibility_with_mux()
        if action == PlanCompatibility.Action.TRANSFORM:
            plan = self._transform_plan(data)
        elif action == PlanCompatibility.Action.CLOSE_PLAN:
            plan = self._create_plan_for_mux()
        elif action == PlanCompatibility.Action.CLOSE_MUX:
            plan = None
        else:
            plan = None
        return plan

    def check_compatibility_with_product(self) -> Optional[Union[Board, MeasurementPlan]]:
        """
        Method checks the plan for compatibility with the product (available measurement settings).
        :return: verified measurement plan or None if the plan did not pass the test.
        """

        if self._measurement_system and not self._check_compatibility_with_product():
            self._show_warning_incompatibility_with_product()
            plan = None
        else:
            plan = self._plan
        return plan


def add_points(elements: List[Element], number: int) -> None:
    """
    :param elements:
    :param number:
    """

    element = elements[-1]
    x, y = 0, 0
    while number > 0:
        element.pins.append(Pin(x=x, y=y))
        number -= 1


def get_free_mux_output(data: PlanCompatibility.AnalyzedData, index: int) -> Optional[Tuple[int, int]]:
    """
    :param data:
    :param index:
    :return:
    """

    for module in range(1, len(data.channels) + 1):
        module_channels = data.channels[module]
        for channel in range(1, MAX_CHANNEL_NUMBER + 1):
            if len(module_channels[channel]) == 0:
                module_channels[channel].append(index)
                return channel, module
    return None


def get_point_index_to_remove(elements: List[Element], data: PlanCompatibility.AnalyzedData) -> int:
    """
    Function returns the index of a point that can be removed from the list of points.
    :param elements: list of board elements;
    :param data:
    :return:
    """

    if data.extra:
        return data.extra.pop(-1)

    if data.empty:
        return data.empty.pop(-1)

    for module_channels in data.channels:
        for channel, indeces in module_channels.items():
            if len(indeces) > 1:
                return indeces.pop(-1)

    return sum(len(element.pins) for element in elements) - 1


def remove_extra_points(elements: List[Element], data: PlanCompatibility.AnalyzedData, number: int) -> None:
    """
    Function removes a given number of points from the list of points.
    :param elements: list of board elements;
    :param data:
    :param number: number of points to remove.
    """

    while number > 0:
        remove_point(elements, data)
        number -= 1


def remove_point(elements: List[Element], data: PlanCompatibility.AnalyzedData) -> None:
    """
    Function removes a point from the list of points.
    :param elements: list of board elements;
    :param data:
    """

    index_to_remove = get_point_index_to_remove(elements, data)
    pin_index = 0
    for element in elements:
        for i, pin in enumerate(element.pins):
            if pin_index == index_to_remove:
                element.pins.pop(i)
                return


def set_mux_output(elements: List[Element], data: PlanCompatibility.AnalyzedData) -> None:
    """
    Function
    :param elements:
    :param data:
    """

    index = 0
    mux_outputs = set()
    for element in elements:
        for pin in element.pins:
            if pin.multiplexer_output is None or pin.multiplexer_output in mux_outputs:
                mux_output = get_free_mux_output(data, index)
                pin.multiplexer_output = MultiplexerOutput(*mux_output)
                mux_outputs.add(mux_output)
            index += 1
