import unittest
from player import SoundPlayer
from common import WorkMode
from random import random
import time


class TestSound(unittest.TestCase):
    def test_here_no_fails(self):
        # Just test that here are no unexpected errors like ValueError, RuntimeError, etc

        player = SoundPlayer()

        for mode in WorkMode:
            player.set_work_mode(mode)

            for i in range(-1, 11):
                player.set_threshold(0)
                player.score_updated(i)
                time.sleep(0.1)

        self.assertTrue(True)
