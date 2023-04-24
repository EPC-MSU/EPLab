from PyQt5.QtCore import QSettings
from epcore.elements.measurement import MeasurementSettings
from eplab.common import WorkMode
from settings.settingshandler import SettingsHandler
from settings.utils import float_to_str, get_parameter, set_parameter, to_bool


class SettingsEditor:
    """
    Disables settings changed signal emitting and forces it on exit.
    """

    def __init__(self, settings) -> None:
        self.__settings = settings

    def __enter__(self):
        self.__settings.add_editor(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__settings.remove_editor(self)


class Settings(SettingsHandler):

    internal_resistance: float = None
    max_voltage: float = None
    probe_signal_frequency: int = None
    sampling_rate: int = None
    hide_curve_a: bool = False
    hide_curve_b: bool = False
    score_threshold: float = 0.5
    sound_enabled: bool = False
    work_mode: WorkMode = WorkMode.COMPARE

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.__active_editors = set()

    def _read(self, settings: QSettings) -> None:
        with SettingsEditor(self):
            settings.beginGroup("General")
            self.internal_resistance = get_parameter(settings, "internal_resistance", convert=float, required=False,
                                                     default=Settings.internal_resistance)
            self.max_voltage = get_parameter(settings, "max_voltage", convert=float, required=False,
                                             default=Settings.max_voltage)
            self.probe_signal_frequency = get_parameter(settings, "probe_signal_frequency", convert=int, required=False,
                                                        default=Settings.probe_signal_frequency)
            self.sampling_rate = get_parameter(settings, "sampling_rate", convert=int, required=False,
                                               default=Settings.sampling_rate)
            self.score_threshold = get_parameter(settings, "score_threshold", convert=float, required=False,
                                                 default=Settings.score_threshold)
            self.sound_enabled = get_parameter(settings, "sound_enabled", convert=to_bool, required=False,
                                               default=Settings.sound_enabled)
            self.hide_curve_a = get_parameter(settings, "hide_curve_a", convert=to_bool, required=False,
                                              default=Settings.hide_curve_a)
            self.hide_curve_b = get_parameter(settings, "hide_curve_b", convert=to_bool, required=False,
                                              default=Settings.hide_curve_b)
            mode_key = get_parameter(settings, "work_mode", convert=str, required=False, default="compare")
            self.work_mode = getattr(WorkMode, mode_key.upper(), WorkMode.COMPARE)
            settings.endGroup()

    def _write(self, settings: QSettings) -> None:
        settings.beginGroup("General")
        set_parameter(settings, "internal_resistance", float_to_str(self.internal_resistance))
        set_parameter(settings, "max_voltage", float_to_str(self.max_voltage))
        set_parameter(settings, "probe_signal_frequency", self.probe_signal_frequency)
        set_parameter(settings, "sampling_rate", self.sampling_rate)
        set_parameter(settings, "hide_curve_a", self.hide_curve_a)
        set_parameter(settings, "hide_curve_b", self.hide_curve_b)
        set_parameter(settings, "score_threshold", float_to_str(self.score_threshold))
        set_parameter(settings, "sound_enabled", self.sound_enabled)
        set_parameter(settings, "work_mode", self.work_mode.name.lower())
        settings.endGroup()

    def add_editor(self, editor) -> None:
        self.__active_editors.add(editor)

    def measurement_settings(self) -> MeasurementSettings:
        return MeasurementSettings(internal_resistance=self.internal_resistance,
                                   max_voltage=self.max_voltage,
                                   probe_signal_frequency=self.probe_signal_frequency,
                                   sampling_rate=self.sampling_rate)

    def remove_editor(self, editor) -> None:
        self.__active_editors.discard(editor)
        if len(self.__active_editors) == 0:
            self.changed.emit()

    def set_measurement_settings(self, settings: MeasurementSettings) -> None:
        self.internal_resistance = settings.internal_resistance
        self.max_voltage = settings.max_voltage
        self.probe_signal_frequency = settings.probe_signal_frequency
        self.sampling_rate = settings.sampling_rate
