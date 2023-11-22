import time
import unittest
from common import WorkMode
from window.soundplayer import SoundPlayer


class TestSoundPlayer(unittest.TestCase):

    def test_here_no_fails(self) -> None:
        """
        Just test that here are no unexpected errors like ValueError, RuntimeError, etc
        """

        player = SoundPlayer()
        for mode in WorkMode:
            player.set_work_mode(mode)
            for score in range(-1, 11):
                player.set_threshold(0)
                player.score_updated(score)
                time.sleep(0.1)
        self.assertTrue(True)
