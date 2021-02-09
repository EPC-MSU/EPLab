from epcore.elements.measurement import MeasurementSettings
from settings.utils import get_parameter, set_parameter, to_bool, float_to_str
from .settingshandler import SettingsHandler
from common import WorkMode
from PyQt5 import QtCore


__all__ = ["Settings"]


Modes = {"Compare": WorkMode.compare, "Write": WorkMode.write, "Test": WorkMode.test}


class SettingsEditor:
    """Disables settings changed signal emitting and forces it on exit."""

    def __init__(self, settings):
        self.__settings = settings

    def __enter__(self):
        self.__settings.add_editor(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__settings.remove_editor(self)


class Settings(SettingsHandler):
    changed = QtCore.pyqtSignal()
    max_voltage = None
    internal_resistance = None
    frequency = None
    score_threshold = 0.5
    sound_enabled = False
    hide_curve_a = False
    hide_curve_b = False
    work_mode = WorkMode.compare

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.__active_editors = set()

    def add_editor(self, editor):
        self.__active_editors.add(editor)

    def remove_editor(self, editor):
        self.__active_editors.discard(editor)
        if len(self.__active_editors) == 0:
            self.changed.emit()

    def measurement_settings(self) -> MeasurementSettings:
        return MeasurementSettings(
            probe_signal_frequency=self.frequency[0],
            sampling_rate=self.frequency[1],
            internal_resistance=self.internal_resistance,
            max_voltage=self.max_voltage,
        )

    def set_measurement_settings(self, settings: MeasurementSettings):
        self.max_voltage = settings.max_voltage
        self.frequency = settings.probe_signal_frequency, settings.sampling_rate
        self.internal_resistance = settings.internal_resistance

    def _read(self, settings):
        with SettingsEditor(self):
            settings.beginGroup("General")
            self.max_voltage = get_parameter(settings, "max_voltage", convert=float, required=False,
                                             default=self.max_voltage)
            self.internal_resistance = get_parameter(settings, "internal_resistance", convert=float,
                                                     required=False, default=Settings.internal_resistance)
            self.probe_signal_frequency = get_parameter(settings, "frequency",
                                                        convert=lambda value: tuple(map(int, value)),
                                                        required=False, default=Settings.frequency)
            self.score_threshold = get_parameter(settings, "score_threshold", convert=float,
                                                 required=0.5, default=Settings.score_threshold)
            self.sound_enabled = get_parameter(settings, "sound_enabled", convert=to_bool, required=False,
                                               default=Settings.sound_enabled)
            self.hide_curve_a = get_parameter(settings, "hide_curve_a", convert=to_bool, required=False,
                                              default=Settings.hide_curve_a)
            self.hide_curve_b = get_parameter(settings, "hide_curve_b", convert=to_bool, required=False,
                                              default=Settings.hide_curve_b)
            _mode_key = get_parameter(settings, "work_mode", convert=str, required=False, default="Compare")
            self.work_mode = Modes[_mode_key]
            settings.endGroup()

    def _write(self, settings):
        settings.beginGroup("General")
        set_parameter(settings, "frequency", [int(f) for f in self.frequency])
        set_parameter(settings, "max_voltage", float_to_str(self.max_voltage))
        set_parameter(settings, "internal_resistance", float_to_str(self.internal_resistance))
        set_parameter(settings, "score_threshold", float_to_str(self.score_threshold))
        set_parameter(settings, "sound_enabled", self.sound_enabled)
        set_parameter(settings, "hide_curve_a", self.hide_curve_a)
        set_parameter(settings, "hide_curve_b", self.hide_curve_b)
        for k in Modes.keys():
            if Modes[k] == self.work_mode:
                _mode_key = k
        set_parameter(settings, "work_mode", _mode_key)

        settings.endGroup()


def _str_to_int_or_str(value):
    try:
        return int(value)
    except ValueError:
        return str(value)
