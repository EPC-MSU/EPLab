from PyQt5.QtWidgets import QLabel


class ScoreWrapper:

    _COLOR_BAD: str = "#cc0000"
    _COLOR_GOOD: str = "#73d216"
    DEFAULT_SCORE_THRESHOLD: float = 0.15

    def __init__(self, label: QLabel) -> None:
        """
        :param label: QLabel widget for score value.
        """

        self._friendly_score: str = "-"
        self._label: QLabel = label
        self._threshold: float = ScoreWrapper.DEFAULT_SCORE_THRESHOLD
        self._get_threshold_int()

    @property
    def threshold(self) -> float:
        """
        :return: threshold score.
        """

        return self._threshold

    def _get_threshold_int(self) -> None:
        self._threshold_int: int = convert_to_int(self._threshold)

    def _set_score_text(self, text: str, color: str) -> None:
        """
        :param text: user friendly score value to display in the label widget;
        :param color: display color.
        """

        self._label.setText(f'<html><head/><body><p><span style="font-size:48pt;color:{color};">{text}</span>'
                            f"</p></body></html>")

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

        score = convert_to_int(score)
        color = self._COLOR_GOOD if score <= self._threshold_int else self._COLOR_BAD
        self._friendly_score = str(score) + "%"
        self._set_score_text(self._friendly_score, color)

    def set_threshold(self, new_threshold: float) -> None:
        """
        :param new_threshold: new threshold score value.
        """

        self._threshold = max(min(new_threshold, 1.0), 0.0)
        self._get_threshold_int()


def convert_to_int(value: float) -> int:
    """
    :param value: the value to be converted to an integer percentage.
    :return: integer percentage.
    """

    return round(100 * value)