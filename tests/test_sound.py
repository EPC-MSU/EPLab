import unittest
from player import SoundPlayer
from common import WorkMode
from random import random


class TestSound(unittest.TestCase):
    def test_here_no_fails(self):
        # Just test that here are no unexpected errors like ValueError, RuntimeError, etc

        player = SoundPlayer()
        player.set_mute(True)

        for mode in WorkMode:
            player.set_work_mode(mode)

            for _ in range(20):
                player.set_threshold(random())
                player.score_updated(random())

        self.assertTrue(True)
