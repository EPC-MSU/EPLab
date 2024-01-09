from PyQt5.QtWidgets import QLabel


class ScoreWrapper:

    _COLOR_BAD: str = "#cc0000"
    _COLOR_GOOD: str = "#73d216"
    DEFAULT_SCORE_TOLERANCE: float = 0.15

    def __init__(self, label: QLabel) -> None:
        """
        :param label: QLabel widget for score value.
        """

        self._friendly_score: str = "-"
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

    def _set_score_text(self, text: str, color: str) -> None:
        """
        :param text: user friendly score value to display in the label widget;
        :param color: display color.
        """

        self._label.setText(f'<html><head/><body><p><span style="font-size:48pt;color:{color};">{text}</span>'
                            f"</p></body></html>")

    def check_score(self, score: float) -> bool:
        """
        Method compares the given score with the threshold.
        :param score: score.
        :return: True if score is not greater than the threshold, otherwise False.
        """

        score = convert_to_percent_with_tenths(score)
        return score <= self._tolerance_with_tenths

    def get_friendly_score(self) -> str:
        """
        :return: user friendly score value.
        """

        return self._friendly_score

    def set_dummy_score(self) -> None:
        self._friendly_score = "-"
        self._set_score_text(self._friendly_score, self._COLOR_GOOD)

    def set_score(self, score: float) -> None:
        """
        :param score: new score value.
        """

        score = convert_to_percent_with_tenths(score)
        color = self._COLOR_GOOD if score <= self._tolerance_with_tenths else self._COLOR_BAD
        self._friendly_score = str(score) + "%"
        self._set_score_text(self._friendly_score, color)

    def set_tolerance(self, new_tolerance: float) -> None:
        """
        :param new_tolerance: new tolerance value.
        """

        self._tolerance = max(min(new_tolerance, 1.0), 0.0)
        self._get_tolerance_with_tenths()


def convert_to_percent_with_tenths(value: float) -> float:
    """
    :param value: the value to be converted to an percentage with tenths.
    :return: percent with tenths.
    """

    value = round(100 * value, 1)
    if value == 100.0:
        value = 100
    return value
