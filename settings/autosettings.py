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
    sensitive: str = None
    voltage: str = None
    auto_transition: bool = False
    language: Language = Language.EN
    measurer_1_port: str = None
    measurer_2_port: str = None
    mux_port: str = None
    product_name: str = None

    def _read(self, settings: QSettings) -> None:

        params = {"frequency": {"convert": check_none},
                  "sensitive": {"convert": check_none},
                  "voltage": {"convert": check_none}}
        settings.beginGroup("MeasurementSettings")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

        params = {"auto_transition": {"convert": get_bool_from_str},
                  "language": {"convert": get_language_from_str}}
        settings.beginGroup("Main")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

        params = {"measurer_1_port": {"convert": check_none},
                  "measurer_2_port": {"convert": check_none},
                  "mux_port": {"convert": check_none},
                  "product_name": {"convert": check_none}}
        settings.beginGroup("Connection")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

    def _write(self, settings: QSettings) -> None:
        params = {"frequency": {"convert": str},
                  "sensitive": {"convert": str},
                  "voltage": {"convert": str}}
        settings.beginGroup("MeasurementSettings")
        self._write_parameters_to_settings(settings, params)
        settings.endGroup()

        params = {"auto_transition": {"convert": str},
                  "language": {"convert": convert_language_to_str}}
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

    def get_auto_transition(self) -> bool:
        """
        :return: auto transition mode is enabled or disabled during testing according to plan.
        """

        return self.auto_transition

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

        return self.language

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
    def save_auto_transition(self, auto_transition: bool) -> None:
        """
        :param auto_transition: auto transition mode is enabled or disabled during testing according to plan.
        """

        self.auto_transition = bool(auto_transition)

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
    def save_language(self, language: Language) -> None:
        """
        :param language: new language for software.
        """

        self.language = language if language is not None else Language.EN

    @save_settings
    def save_measurement_settings(self, options: Dict[EyePointProduct.Parameter, str]) -> None:
        """
        :param options: dictionary with new measurement settings.
        """

        self.frequency = options[EyePointProduct.Parameter.frequency]
        self.sensitive = options[EyePointProduct.Parameter.sensitive]
        self.voltage = options[EyePointProduct.Parameter.voltage]


def check_none(value: str) -> Optional[str]:
    return None if value and value.lower() == "none" else str(value)


def convert_language_to_str(language: Language) -> str:
    """
    :param language: language.
    :return: language value in string format.
    """

    return str(Translator.get_language_name(language))


def get_bool_from_str(value: str) -> bool:
    """
    :param value: string value to be converted to bool.
    :return: bool value.
    """

    return value.lower() == "true"


def get_language_from_str(value: str) -> Language:
    """
    :param value: language value in string format.
    :return: language.
    """

    language = Translator.get_language_value(value)
    return Language.EN if language is None else language
