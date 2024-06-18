from PyQt5.QtWidgets import QLabel


class ScoreWrapper:

    COLOR_BAD: str = "#cc0000"
    COLOR_GOOD: str = "#73d216"
    DEFAULT_SCORE_TOLERANCE: float = 0.15

    def __init__(self, label: QLabel) -> None:
        """
        :param label: QLabel widget for difference value.
        """

        self._friendly_difference: str = "-"
        self._label: QLabel = label
        self._tolerance: float = ScoreWrapper.DEFAULT_SCORE_TOLERANCE
        self._get_tolerance_with_tenths()

    @property
    def tolerance(self) -> float:
        """
        :return: tolerance.
        """

        return self._tolerance

    def _get_tolerance_with_tenths(self) -> None:
        self._tolerance_with_tenths: float = convert_to_percent_with_tenths(self._tolerance)

    def _set_difference_text(self, text: str, color: str) -> None:
        """
        :param text: user-friendly difference value to display in the label widget;
        :param color: display color.
        """

        self._label.setText(f'<html><head/><body><p><span style="font-size:48pt;color:{color};">{text}</span>'
                            f"</p></body></html>")

    def get_friendly_score(self) -> str:
        """
        :return: user-friendly difference value.
        """

        return self._friendly_difference

    def set_difference(self, difference: float) -> None:
        """
        :param difference: new difference value.
        """

        difference = convert_to_percent_with_tenths(difference)
        color = self.COLOR_GOOD if difference <= self._tolerance_with_tenths else self.COLOR_BAD
        self._friendly_difference = str(difference) + "%"
        self._set_difference_text(self._friendly_difference, color)

    def set_dummy_difference(self) -> None:
        self._friendly_difference = "-"
        self._set_difference_text(self._friendly_difference, self.COLOR_GOOD)

    def set_tolerance(self, new_tolerance: float) -> None:
        """
        :param new_tolerance: new tolerance value.
        """

        self._tolerance = max(min(new_tolerance, 1.0), 0.0)
        self._get_tolerance_with_tenths()


def check_difference_not_greater_tolerance(difference: float, tolerance: float) -> bool:
    """
    Function compares the given difference with the tolerance.
    :param difference: difference;
    :param tolerance: tolerance.
    :return: True if difference is not greater than the tolerance, otherwise False.
    """

    return convert_to_percent_with_tenths(difference) <= convert_to_percent_with_tenths(tolerance)


def convert_to_percent_with_tenths(value: float) -> float:
    """
    :param value: the value to be converted to an percentage with tenths.
    :return: percent with tenths.
    """

    value = round(100 * value, 1)
    if value == 100.0:
        value = 100
    return value
