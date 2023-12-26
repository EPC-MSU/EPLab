import os
from enum import IntEnum
from typing import Optional, Union
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

    class Action(IntEnum):
        TRANSFORM = 0
        CLOSE_PLAN = 1
        CLOSE_MUX = 2

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

    def _check_compatibility_with_mux(self) -> bool:
        """
        Method checks the plan for compatibility with the multiplexer.
        :return: True if the plan is compatible, otherwise not.
        """

        multiplexer = self._measurement_system.multiplexers[0]
        modules = len(multiplexer.get_chain_info())
        channels = {module + 1: {channel + 1 for channel in range(MAX_CHANNEL_NUMBER)} for module in range(modules)}
        empty_points = []
        extra_points = []

        index = 0
        for element in self._plan.elements:
            for pin in element.pins:
                mux_output = pin.multiplexer_output
                if isinstance(mux_output, MultiplexerOutput):
                    if multiplexer.is_correct_output(mux_output):
                        channels[mux_output.module_number].discard(mux_output.channel_number)
                    else:
                        extra_points.append(index)
                else:
                    empty_points.append(index)
                index += 1

        if len(empty_points) == 0 and len(extra_points) == 0 and \
                all(len(channels_) == 0 for channels_ in channels.values()):
            return True

        return False

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
        if isinstance(self._plan, MeasurementPlan):
            measurer = self._measurement_system.measurers[0]
            plan = MeasurementPlan(board, measurer, multiplexer)
        else:
            plan = board
        return plan

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

    def _transform_plan(self) -> Union[Board, MeasurementPlan]:
        """
        Method creates an empty measurement plan for the connected multiplexer.
        :return: empty plan.
        """

        return self._plan

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

        if self._check_compatibility_with_mux():
            return self._plan

        action = self._show_warning_incompatibility_with_mux()
        if action == PlanCompatibility.Action.TRANSFORM:
            plan = self._transform_plan()
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
