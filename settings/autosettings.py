from typing import Any, Callable, Dict, Optional
from PyQt5.QtCore import QSettings
from epcore.elements import MeasurementSettings
from epcore.product import EyePointProduct
from settings.settingshandler import SettingsHandler
from window.language import Language, Translator


def save_settings(func: Callable[..., Any]):
    """
    Decorator for saving settings after executing the decorated method.
    :param func: decorated method.
    """

    def wrapper(self, *args, **kwargs) -> Any:
        result = func(self, *args, **kwargs)
        self.write()
        return result

    return wrapper


class AutoSettings(SettingsHandler):
    """
    Class for working with basic software settings. These settings are saved when the software is closed and updated
    upon startup.
    """

    frequency: str = None
    language: str = None
    sensitive: str = None
    voltage: str = None
    measurer_1_port: str = None
    measurer_2_port: str = None
    mux_port: str = None
    product_name: str = None

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

        def check_none(value: str) -> Optional[str]:
            if value and value.lower() == "none":
                return None
            return str(value)

        params = {"measurer_1_port": {"convert": check_none},
                  "measurer_2_port": {"convert": check_none},
                  "mux_port": {"convert": check_none},
                  "product_name": {"convert": check_none}}
        settings.beginGroup("Connection")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

    def _write(self, settings: QSettings) -> None:
        params = {"frequency": {},
                  "sensitive": {},
                  "voltage": {}}
        settings.beginGroup("MeasurementSettings")
        self._write_parameters_to_settings(settings, params)
        settings.endGroup()

        params = {"language": {"convert": str}}
        settings.beginGroup("Main")
        self._write_parameters_to_settings(settings, params)
        settings.endGroup()

        params = {"measurer_1_port": {"convert": str},
                  "measurer_2_port": {"convert": str},
                  "mux_port": {"convert": str},
                  "product_name": {"convert": str}}
        settings.beginGroup("Connection")
        self._write_parameters_to_settings(settings, params)
        settings.endGroup()

    def get_connection_params(self) -> Dict[str, str]:
        """
        :return: dictionary with port of the connected first and second IV-measurers, port of the connected multiplexer
        and name of the connected device.
        """

        return {"measurer_1_port": self.measurer_1_port,
                "measurer_2_port": self.measurer_2_port,
                "mux_port": self.mux_port,
                "product_name": self.product_name}

    def get_language(self) -> Language:
        """
        :return: the language that was set during the previous work.
        """

        language = Translator.get_language_value(self.language)
        if language is None:
            return Language.EN
        return language

    def get_measurement_settings(self, product: EyePointProduct) -> Optional[MeasurementSettings]:
        """
        :param product: product.
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

    @save_settings
    def save_connection_params(self, measurer_1_port: str, measurer_2_port: str, mux_port: str, product_name: str
                               ) -> None:
        """
        :param measurer_1_port: port of the connected first IV-measurer;
        :param measurer_2_port: port of the connected second IV-measurer;
        :param mux_port: port of the connected multiplexer;
        :param product_name: name of the connected device.
        """

        self.measurer_1_port = measurer_1_port
        self.measurer_2_port = measurer_2_port
        self.mux_port = mux_port
        self.product_name = product_name

    @save_settings
    def save_language(self, language: str) -> None:
        """
        :param language: new language for software.
        """

        self.language = language

    @save_settings
    def save_measurement_settings(self, options: Dict[EyePointProduct.Parameter, str]) -> None:
        """
        :param options: dictionary with new measurement settings.
        """

        self.frequency = options[EyePointProduct.Parameter.frequency]
        self.sensitive = options[EyePointProduct.Parameter.sensitive]
        self.voltage = options[EyePointProduct.Parameter.voltage]
