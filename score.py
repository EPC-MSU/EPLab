from PyQt5.QtWidgets import QLabel


class ScoreWrapper:
    def __init__(self, label: QLabel, score_threshold: float = 0.5, threshold_step: float = 0.1):
        self._label = label
        self._threshold = score_threshold
        self._step = threshold_step

        self._color_good = "#73d216"
        self._color_bad = "#cc0000"

    def _set_score_text(self, text: str, color: str):
        text = f'<html><head/><body><p><span style="font-size:48pt;color:{color};">' \
               f"{text}</span></p></body></html>"
        self._label.setText(text)

    def set_score(self, score: float):
        color = self._color_good if score < self._threshold else self._color_bad
        try:
            friendly_score = str(round(score * 100.0)) + "%"
        except ValueError:
            # TODO: this should not happen
            friendly_score = "NaN"
        self._set_score_text(friendly_score, color)

    def set_dummy_score(self):
        self._set_score_text("-", self._color_good)

    def increase_threshold(self):
        self._threshold = min(self._threshold + self._step, 1.0)

    def decrease_threshold(self):
        self._threshold = max(self._threshold - self._step, 0.0)

    def set_threshold(self, value: float):
        self._threshold = max(min(value, 1.0), 0.0)

    @property
    def threshold(self):
        return self._threshold
