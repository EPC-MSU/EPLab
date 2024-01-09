from epcore.filemanager import load_board_from_ufiv
from epcore.measurementmanager import MeasurementPlan


class SimpleMainWindow:
    """
    Class for modeling simple main window.
    """

    def __init__(self, board_path: str) -> None:
        """
        :param board_path: path to file with board.
        """

        self._measurement_plan: MeasurementPlan = self._create_measurement_plan(board_path)

    @property
    def measurement_plan(self) -> MeasurementPlan:
        """
        :return: measurement plan.
        """

        return self._measurement_plan

    @staticmethod
    def _create_measurement_plan(board_path: str) -> MeasurementPlan:
        """
        :param board_path: path to file with board.
        :return: a simple test plan loaded from a file.
        """

        board = load_board_from_ufiv(board_path)
        return MeasurementPlan(board, None)
