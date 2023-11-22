import logging
import os
from epsound import WavPlayer
from window.common import WorkMode


logger = logging.getLogger("eplab")


class SoundPlayer:

    def __init__(self) -> None:
        self._player: WavPlayer = WavPlayer(wait=False)
        self._score: float = 0
        self._sound_available: bool = True
        self._threshold: float = 0
        self._work_mode: WorkMode = WorkMode.COMPARE

        if not self._player.check_sound_available():
            logger.error("Sound is not available on your system; mute")
            self._player.set_mute()
            self._sound_available = False
        self._load_sounds()

    def _load_sounds(self) -> None:
        dir_media = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
        for i in range(1, 11):
            self._player.add_sound(os.path.join(dir_media, f"{i}.wav"), f"{i}")
        self._player.add_sound(os.path.join(dir_media, "test.wav"), "test")

    def _play(self, name: str) -> None:
        """
        :param name: name of the sound file to be played.
        """

        try:
            self._player.play(name)
        except RuntimeError:
            # Another sound in progress - it's ok to get error here...
            pass

    @staticmethod
    def _score_to_sound_n(score: float) -> int:
        """
        :param score: score.
        :return: number of the sound file that corresponds to the given score.
        """

        # TODO: When will stabilise ivcmp library, add exceptions here
        sound_n = min(int(score * 10.0) + 1, 10)
        return max(1, sound_n)

    def score_updated(self, score: float) -> None:
        """
        :param score: score.
        """

        # Logic described here #39296
        # FIXME: in case of *very fast* score update in asynchronous mode here may be big stack of wav files
        if self._work_mode is WorkMode.COMPARE:
            if score > self._threshold:
                try:
                    sound_num = self._score_to_sound_n(self._score)
                    self._play(f"{sound_num}")
                except ValueError:  # NaN score or smth else strange
                    return
        elif self._work_mode in (WorkMode.TEST, WorkMode.WRITE):
            if self._score > self._threshold > score:
                self._play("test")
        self._score = score

    def set_mute(self, mute: bool = True) -> None:
        """
        :param mute: if True, then the sound will be muted.
        """

        if self._sound_available:
            self._player.set_mute(mute)

    def set_threshold(self, threshold: float) -> None:
        """
        :param threshold: new threshold value for score.
        """

        self._threshold = threshold

    def set_work_mode(self, mode: WorkMode) -> None:
        """
        :param mode: new work mode.
        """

        self._work_mode = mode
