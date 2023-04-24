from PyQt5.QtWidgets import QLabel


DEFAUT_SCORE_THRESHOLD = 0.15
DEFAULT_SCORE_THRESHOLD_STEP = 0.05


class ScoreWrapper:

    _COLOR_BAD = "#cc0000"
    _COLOR_GOOD = "#73d216"

    def __init__(self, label: QLabel, score_threshold: float = DEFAUT_SCORE_THRESHOLD,
                 threshold_step: float = DEFAULT_SCORE_THRESHOLD_STEP) -> None:
        """
        :param label: QLabel widget for score value;
        :param score_threshold: threshold score;
        :param threshold_step: step of changing of threshold score.
        """

        self._friendly_score: str = "-"
        self._label: QLabel = label
        self._step: float = threshold_step
        self._threshold: float = score_threshold

    def _set_score_text(self, text: str, color: str) -> None:
        self._label.setText(f'<html><head/><body><p><span style="font-size:48pt;color:{color};">{text}</span>'
                            f"</p></body></html>")

    def decrease_threshold(self) -> None:
        self._threshold = max(self._threshold - self._step, 0.0)

    def get_score(self) -> str:
        return self._friendly_score

    def increase_threshold(self) -> None:
        self._threshold = min(self._threshold + self._step, 1.0)

    def set_dummy_score(self) -> None:
        self._friendly_score = "-"
        self._set_score_text(self._friendly_score, self._COLOR_GOOD)

    def set_score(self, score: float) -> None:
        color = self._COLOR_GOOD if score < self._threshold else self._COLOR_BAD
        try:
            self._friendly_score = str(round(score * 100.0)) + "%"
        except ValueError:
            # TODO: this should not happen
            self._friendly_score = "NaN"
        self._set_score_text(self._friendly_score, color)

    def set_threshold(self, value: float) -> None:
        self._threshold = max(min(value, 1.0), 0.0)

    @property
    def threshold(self) -> float:
        return self._threshold
