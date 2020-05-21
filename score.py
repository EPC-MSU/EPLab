from PyQt5.QtWidgets import QLabel


class ScoreWrapper:
    def __init__(self, label: QLabel, score_threshold: float = 0.5, threshold_step: float = 0.1):
        self._label = label
        self._threshold = score_threshold
        self._step = threshold_step

        self._color_good = "#73d216"
        self._color_bad = "#cc0000"

    def set_score(self, score: float):
        color = self._color_good if score < self._threshold else self._color_bad
        try:
            friendly_score = round(score * 100.0)
        except ValueError:
            # TODO: this should not happen
            friendly_score = "NaN"
        text = f'<html><head/><body><p><span style="font-size:48pt;color:{color};">' \
               f"{friendly_score}%</span></p></body></html>"
        self._label.setText(text)

    def increase_threshold(self):
        self._threshold = min(self._threshold + self._step, 1.0)

    def decrease_threshold(self):
        self._threshold = max(self._threshold - self._step, 0.0)

    @property
    def threshold(self):
        return self._threshold
