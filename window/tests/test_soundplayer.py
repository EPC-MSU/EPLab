import time
import unittest
from window.common import WorkMode
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
                player.set_tolerance(0)
                player.update_score(score)
                time.sleep(0.1)
        self.assertTrue(True)
