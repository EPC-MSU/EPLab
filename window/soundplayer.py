import logging
import os
from epsound import WavPlayer
from window.common import WorkMode


logger = logging.getLogger("eplab")


class SoundPlayer:

    def __init__(self) -> None:
        self._difference: float = 0
        self._player: WavPlayer = WavPlayer(wait=False)
        self._sound_available: bool = True
        self._tolerance: float = 0
        self._work_mode: WorkMode = WorkMode.COMPARE

        if not self._player.check_sound_available():
            logger.error("Sound is not available on your system; mute")
            self._player.set_mute()
            self._sound_available = False
        self._load_sounds()

    @staticmethod
    def _convert_difference_to_sound_n(difference: float) -> int:
        """
        :param difference: signature difference value.
        :return: number of the sound file that corresponds to the given difference.
        """

        # TODO: When will stabilise ivcmp library, add exceptions here
        sound_n = min(int(difference * 10.0) + 1, 10)
        return max(1, sound_n)

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

    def _play_sound_in_compare_mode(self, score: float) -> None:
        """
        :param score: signature difference value.
        """

        if score > self._tolerance:
            try:
                sound_num = self._convert_difference_to_sound_n(self._difference)
                self._play(f"{sound_num}")
            except ValueError:
                pass

    def _play_sound_in_test_mode(self, difference: float) -> None:
        """
        :param difference: signature difference value.
        """

        if self._difference > self._tolerance > difference:
            self._play("test")

    def set_mute(self, mute: bool = True) -> None:
        """
        :param mute: if True, then the sound will be muted.
        """

        if self._sound_available:
            self._player.set_mute(mute)

    def set_tolerance(self, tolerance: float) -> None:
        """
        :param tolerance: new tolerance value.
        """

        self._tolerance = tolerance

    def set_work_mode(self, mode: WorkMode) -> None:
        """
        :param mode: new work mode.
        """

        self._work_mode = mode

    def update_difference(self, difference: float) -> None:
        """
        :param difference: signature difference value.
        """

        # Logic described here #39296
        # FIXME: in case of *very fast* score update in asynchronous mode here may be big stack of wav files
        if self._work_mode is WorkMode.COMPARE:
            # Users do not like the original sound in comparison mode. Therefore, in task #92261 it was decided to
            # replace it with the same one as in test plan mode
            # self._play_sound_in_compare_mode(difference)
            self._play_sound_in_test_mode(difference)
        elif self._work_mode in (WorkMode.TEST, WorkMode.WRITE):
            self._play_sound_in_test_mode(difference)
        self._difference = difference
