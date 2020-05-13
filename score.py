from PyQt5.QtWidgets import QLabel


class ScoreWrapper:
    def __init__(self, label: QLabel, score_threshold: float = 0.5):
        self._label = label
        self._treshold = score_threshold

        self._color_good = "#73d216"
        self._color_bad = "#cc0000"

    def set_score(self, score: float):

        color = self._color_good if score < self._treshold else self._color_bad
        friendly_score = round(score * 100.0)
        text = f'<html><head/><body><p><span style="font-size:48pt;color:{color};">' \
               f'{friendly_score}%</span></p></body></html>'
        self._label.setText(text)
