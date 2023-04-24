import logging
import os
from epsound import WavPlayer
from eplab.common import WorkMode
from eplab.utils import DIR_MEDIA


class SoundPlayer:

    def __init__(self) -> None:
        self._player: WavPlayer = WavPlayer(wait=False)
        self._score: float = 0
        self._sound_available: bool = True
        self._threshold: float = 0
        self._work_mode: WorkMode = WorkMode.COMPARE

        if not self._player.check_sound_available():
            logging.error("Sound is not available on your system, mute")
            self._player.set_mute()
            self._sound_available = False

        for i in range(1, 11):
            self._player.add_sound(os.path.join(DIR_MEDIA, f"{i}.wav"), f"{i}")
        self._player.add_sound(os.path.join(DIR_MEDIA, "test.wav"), "test")

    def _play(self, name: str) -> None:
        """
        :param name: name of sound to play.
        """

        try:
            self._player.play(name)
        except RuntimeError:
            pass  # Another sound in progress - it's ok to get error here...

    @staticmethod
    def _score_to_sound_number(score: float) -> int:
        """
        :param score: score for which to play sound.
        """

        # TODO: When will stabilise ivcmp library,
        # add exceptions here
        return max(1, min(int(score * 10.0) + 1, 10))

    def score_updated(self, score: float) -> None:
        """
        :param score: new score.
        """

        # Logic described here #39296
        # FIXME: in case of *very fast* score update in asynchronous mode here may be big stack of wav files
        if self._work_mode is WorkMode.COMPARE:
            if score > self._threshold:
                try:
                    self._play(f"{self._score_to_sound_number(self._score)}")
                except ValueError:  # NaN score or smth else strange
                    return
        else:
            if self._score > self._threshold > score:
                self._play("test")
        self._score = score

    def set_mute(self, mute: bool = True) -> None:
        """
        :param mute: if True, sound will be muted.
        """

        if self._sound_available:  # We can't disable MUTE if sound driver is not available
            self._player.set_mute(mute)

    def set_threshold(self, threshold: float) -> None:
        """
        :param threshold: new threshold.
        """

        self._threshold = threshold

    def set_work_mode(self, mode: WorkMode) -> None:
        """
        :param mode: new work mode.
        """

        self._work_mode = mode
