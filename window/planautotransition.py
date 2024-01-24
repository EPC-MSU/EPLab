import os
from PyQt5.QtCore import QObject
from epcore.product import EyePointProduct
from settings.autosettings import AutoSettings


class PlanAutoTransition(QObject):

    def __init__(self, auto_settings: AutoSettings) -> None:
        """
        :param auto_settings:
        """

        super().__init__()
        self._auto_settings: AutoSettings = auto_settings
        self._dir: str = os.path.join(os.path.curdir, "break_signatures")
        self._product: EyePointProduct = None
