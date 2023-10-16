from typing import Optional
from PyQt5.QtCore import QSettings
from epcore.elements import MeasurementSettings
from epcore.product import EyePointProduct
from dialogs.language import Language
from settings.settingshandler import SettingsHandler


class AutoSettings(SettingsHandler):

    frequency: str = None
    language: str = None
    sensitive: str = None
    voltage: str = None

    def _read(self, settings: QSettings) -> None:
        params = {"frequency": {},
                  "sensitive": {},
                  "voltage": {}}
        settings.beginGroup("MeasurementSettings")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

        params = {"language": {}}
        settings.beginGroup("Main")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

    def _write(self, settings: QSettings) -> None:
        params = {"frequency": {},
                  "sensitive": {},
                  "voltage": {}}
        settings.beginGroup("MeasurementSettings")
        self._write_parameters_to_settings(settings, params)
        settings.endGroup()

        params = {"language": {}}
        settings.beginGroup("Main")
        self._write_parameters_to_settings(settings, params)
        settings.endGroup()

    def get_language(self) -> Language:
        language = Language.get_language_value(self.language)
        if language is None:
            return Language.EN
        return language

    def get_measurement_settings(self, product: EyePointProduct) -> Optional[MeasurementSettings]:
        """
        :param product:
        :return: measurement settings that were specified for device during previous work.
        """

        if None in (self.frequency, self.sensitive, self.voltage):
            return None

        options = {EyePointProduct.Parameter.frequency: self.frequency,
                   EyePointProduct.Parameter.sensitive: self.sensitive,
                   EyePointProduct.Parameter.voltage: self.voltage}
        measurement_settings = MeasurementSettings(0, 0, 0, 0)
        measurement_settings = product.options_to_settings(options, measurement_settings)
        if -1 in (measurement_settings.probe_signal_frequency, measurement_settings.sampling_rate,
                  measurement_settings.max_voltage, measurement_settings.internal_resistance):
            return None

        return measurement_settings

    def save_language(self, language: str):
        self.language = language
        self.write()

    def save_measurement_settings(self, options) -> None:
        self.frequency = options[EyePointProduct.Parameter.frequency]
        self.sensitive = options[EyePointProduct.Parameter.sensitive]
        self.voltage = options[EyePointProduct.Parameter.voltage]
        self.write()
