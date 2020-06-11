from epsound import WavPlayer
import logging
from os.path import join as join_path
from common import WorkMode


class SoundPlayer:
    def __init__(self):
        self._player = WavPlayer(wait=False)
        self._sound_available = True
        self._score = 0
        self._work_mode: WorkMode = WorkMode.compare
        self._threshold = 0

        if not self._player.check_sound_available():
            logging.error("Sound is not available on your system; mute")
            self._player.set_mute()
            self._sound_available = False

        for i in range(1, 11):
            self._player.add_sound(join_path("media", f"{i}.wav"), f"{i}")
        self._player.add_sound(join_path("media", "test.wav"), "test")

    def set_mute(self, mute: bool = True):
        if self._sound_available:  # We can't disable MUTE if sound driver is not available
            self._player.set_mute(mute)

    def _score_to_sound_n(self, score: float) -> int:
        # TODO: When will stabilise ivcmp library,
        # add exceptions here
        sound_n = min(int(score * 10.0) + 1, 10)
        return max(1, sound_n)

    def _play(self, name: str):
        try:
            self._player.play(name)
        except RuntimeError:
            pass  # Another sound in progress - it's ok to get error here...

    def score_updated(self, score: float):
        # Logic described here #39296
        # FIXME: in case of *very fast* score update in asynchronous mode here may be big stack of wav files
        if self._work_mode is WorkMode.compare:
            if score > self._threshold:
                try:
                    sound_num = self._score_to_sound_n(self._score)
                    self._play(f"{sound_num}")
                except ValueError:  # NaN score or smth else strange
                    return
        else:
            if self._score > self._threshold > score:
                self._play("test")
        self._score = score

    def set_threshold(self, threshold: float):
        self._threshold = threshold

    def set_work_mode(self, mode: WorkMode):
        self._work_mode = mode
