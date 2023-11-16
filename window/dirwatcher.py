import os
from typing import Any, Dict, Optional


class DirWatcher:

    def __init__(self, dir_base: str) -> None:
        """
        :param dir_base: path to base directory.
        """

        self._dir_base: str = dir_base
        self._tree: Dict[str, Any] = {"EPLab-Files": {"Reference": {},
                                                      "Reports": {},
                                                      "Screenshot": {}}}
        self._create_tree()

    def __getattr__(self, item: str) -> Optional[str]:
        """
        :param item: name of the directory, the path to which to return.
        :return: path to required directory.
        """

        def find_path(dir_base: str, dir_tree: Dict[str, Any]) -> Optional[str]:
            """
            :param dir_base: path to base directory;
            :param dir_tree: dictionary with a directory tree, the base of which is the base path.
            :return: path to required directory.
            """

            for dir_name, children_dirs in dir_tree.items():
                dir_path = os.path.join(dir_base, dir_name)
                if item.lower() == dir_name.lower():
                    os.makedirs(dir_path, exist_ok=True)
                    return dir_path

                if children_dirs:
                    return find_path(dir_path, children_dirs)

            return None

        return find_path(self._dir_base, self._tree)

    def _create_tree(self) -> None:
        """
        Method creates a folder tree that is required for EPLab to work.
        """

        def create_dirs(dir_base: str, dir_tree: Dict[str, Any]) -> None:
            """
            :param dir_base: path to base directory;
            :param dir_tree: dictionary with a directory tree, the base of which is the base path.
            """

            for dir_name, children_dirs in dir_tree.items():
                dir_path = os.path.join(dir_base, dir_name)
                os.makedirs(dir_path, exist_ok=True)
                if children_dirs:
                    create_dirs(dir_path, children_dirs)

        create_dirs(self._dir_base, self._tree)
