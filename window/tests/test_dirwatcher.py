import os
import shutil
import unittest
from window.dirwatcher import DirWatcher


class TestDirWatcher(unittest.TestCase):

    def setUp(self) -> None:
        self._dir_base: str = os.path.dirname(os.path.abspath(__file__))
        dir_path = os.path.join(self._dir_base, "EPLab-Files")
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)

        self._dir_watcher = DirWatcher(self._dir_base)

    def test_creation(self) -> None:
        for dir_name in ("reference", "reports", "screenshot"):
            dir_path = getattr(self._dir_watcher, dir_name, None)
            self.assertTrue(os.path.exists(dir_path))
