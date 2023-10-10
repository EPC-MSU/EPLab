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
        return self._threshold

    def _get_threshold_int(self) -> None:
        self._threshold_int: int = convert_to_int(self._threshold)

    def _set_score_text(self, text: str, color: str) -> None:
        self._label.setText(f'<html><head/><body><p><span style="font-size:48pt;color:{color};">{text}</span>'
                            f"</p></body></html>")

    def get_score(self) -> str:
        return self._friendly_score

    def set_dummy_score(self) -> None:
        self._friendly_score = "-"
        self._set_score_text(self._friendly_score, self._COLOR_GOOD)

    def set_score(self, score: float) -> None:
        score = convert_to_int(score)
        color = self._COLOR_GOOD if score < self._threshold_int else self._COLOR_BAD
        try:
            self._friendly_score = str(score) + "%"
        except ValueError:
            # TODO: this should not happen
            self._friendly_score = "NaN"
        self._set_score_text(self._friendly_score, color)

    def set_threshold(self, new_threshold: float) -> None:
        self._threshold = max(min(new_threshold, 1.0), 0.0)
        self._get_threshold_int()


def convert_to_int(value: float) -> int:
    return round(100 * value)
