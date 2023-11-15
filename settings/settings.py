from typing import Any, Dict, List, Tuple
from PyQt5.QtCore import pyqtSignal, QSettings
from epcore.elements.measurement import MeasurementSettings
from common import WorkMode
from settings import utils as ut
from settings.settingshandler import SettingsHandler


MODES = {"Compare": WorkMode.COMPARE,
         "Write": WorkMode.WRITE,
         "Test": WorkMode.TEST}


class SettingsEditor:
    """
    Disables settings changed signal emitting and forces it on exit.
    """

    def __init__(self, settings):
        self.__settings = settings

    def __enter__(self):
        self.__settings.add_editor(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__settings.remove_editor(self)


class Settings(SettingsHandler):

    ATTRIBUTE_NAMES: List[str] = ["frequency", "hide_curve_a", "hide_curve_b", "internal_resistance", "max_voltage",
                                  "score_threshold", "sound_enabled", "work_mode"]
    changed: pyqtSignal = pyqtSignal()
    frequency: Tuple[int, int] = None
    hide_curve_a: bool = False
    hide_curve_b: bool = False
    internal_resistance: float = None
    max_voltage: float = None
    score_threshold: float = 0.15
    sound_enabled: bool = False
    work_mode: WorkMode = WorkMode.COMPARE

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self._active_editors = set()

    def __copy__(self) -> "Settings":
        new_obj = type(self)()
        for attr_name in Settings.ATTRIBUTE_NAMES:
            value = getattr(self, attr_name, None)
            setattr(new_obj, attr_name, value)
        return new_obj

    def __repr__(self) -> str:
        attr_values = [f"{attr_name}={getattr(self, attr_name, None)}" for attr_name in Settings.ATTRIBUTE_NAMES]
        return f"Settings({', '.join(attr_values)})"

    def _read(self, settings: QSettings) -> None:
        """
        :param settings: QSettings object from which parameter values ​​need to be read.
        """

        params = {"frequency": {"convert": lambda value: tuple(map(int, value))},
                  "hide_curve_a": {"convert": ut.to_bool},
                  "hide_curve_b": {"convert": ut.to_bool},
                  "internal_resistance": {"convert": float},
                  "max_voltage": {"convert": float},
                  "score_threshold": {"convert": float},
                  "sound_enabled": {"convert": ut.to_bool},
                  "work_mode": {"convert": lambda value: MODES[value]}}
        with SettingsEditor(self):
            settings.beginGroup("General")
            self._read_parameters_from_settings(settings, params)
            settings.endGroup()

    def _write(self, settings: QSettings) -> None:
        """
        :param settings: QSettings object into which parameter values ​​should be written.
        """

        def get_work_mode(work_mode: WorkMode) -> str:
            for key in MODES:
                if MODES[key] == work_mode:
                    return key
            return "Compare"

        params = {"frequency": {"convert": lambda value: list(map(int, value))},
                  "hide_curve_a": {},
                  "hide_curve_b": {},
                  "internal_resistance": {"convert": ut.float_to_str},
                  "max_voltage": {"convert": ut.float_to_str},
                  "score_threshold": {"convert": ut.float_to_str},
                  "sound_enabled": {},
                  "work_mode": {"convert": get_work_mode}}
        settings.beginGroup("General")
        self._write_parameters_to_settings(settings, params)
        settings.endGroup()

    def add_editor(self, editor) -> None:
        self._active_editors.add(editor)

    def get_default_values(self) -> Dict[str, Any]:
        """
        :return: dictionary with default values ​​of attributes.
        """

        return {param: self._get_default_value(param) for param in Settings.ATTRIBUTE_NAMES}

    def get_measurement_settings(self) -> MeasurementSettings:
        """
        :return: measurement settings.
        """

        return MeasurementSettings(probe_signal_frequency=self.frequency[0],
                                   sampling_rate=self.frequency[1],
                                   internal_resistance=self.internal_resistance,
                                   max_voltage=self.max_voltage)

    def get_values(self) -> Dict[str, Any]:
        """
        :return: dictionary with default values of attributes.
        """

        return {param: getattr(self, param, None) for param in Settings.ATTRIBUTE_NAMES}

    def remove_editor(self, editor) -> None:
        self._active_editors.discard(editor)
        if len(self._active_editors) == 0:
            self.changed.emit()

    def set_measurement_settings(self, settings: MeasurementSettings) -> None:
        """
        :param settings: new measurement settings.
        """

        self.frequency = settings.probe_signal_frequency, settings.sampling_rate
        self.internal_resistance = settings.internal_resistance
        self.max_voltage = settings.max_voltage
