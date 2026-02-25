from typing import Any, Callable, Dict, Optional
from PyQt5.QtCore import QCoreApplication as qApp, QSettings
from epcore.elements import MeasurementSettings
from epcore.product import EyePointProduct
from window.language import Language
from window.utils import get_user_documents_path
from . import utils as ut
from .settingshandler import SettingsHandler


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
    board_window_geometry = None
    freeze_curve_a: bool = False
    freeze_curve_b: bool = False
    hide_curve_a: bool = False
    hide_curve_b: bool = False
    language: Language = ut.get_default_language()
    last_used_dir: str = get_user_documents_path()
    main_window_geometry = None
    max_optimal_voltage: float = 12
    measurer_1_port: str = None
    measurer_2_port: str = None
    mux_port: str = None
    pin_shift_warning_info: bool = True
    product_name: str = None
    sound: bool = False
    test_plan_path: str = None
    tolerance: float = 0.15

    def __copy__(self) -> "AutoSettings":
        """
        You only need to copy the attributes that are set through the "Settings" window.
        """

        new_obj = type(self)()
        for attr_name in ("auto_transition", "max_optimal_voltage", "pin_shift_warning_info", "tolerance"):
            value = getattr(self, attr_name, None)
            setattr(new_obj, attr_name, value)
        return new_obj

    def _read(self, settings: QSettings) -> None:
        """
        :param settings: object from which to read the basic application settings.
        """

        params = {"frequency": {"convert": ut.check_none},
                  "sensitive": {"convert": ut.check_none},
                  "voltage": {"convert": ut.check_none}}
        settings.beginGroup("MeasurementSettings")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

        params = {"max_optimal_voltage": {"convert": float}}
        settings.beginGroup("OptimalSearch")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()
        params = {"auto_transition": {"convert": ut.to_bool},
                  "freeze_curve_a": {"convert": ut.to_bool},
                  "freeze_curve_b": {"convert": ut.to_bool},
                  "hide_curve_a": {"convert": ut.to_bool},
                  "hide_curve_b": {"convert": ut.to_bool},
                  "language": {"convert": ut.get_language_from_str},
                  "last_used_dir": {"convert": ut.get_dir_path_from_str},
                  "pin_shift_warning_info": {"convert": ut.to_bool},
                  "sound": {"convert": ut.to_bool},
                  "tolerance": {"convert": float}}
        settings.beginGroup("Main")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

        params = {"measurer_1_port": {"convert": ut.check_none},
                  "measurer_2_port": {"convert": ut.check_none},
                  "mux_port": {"convert": ut.check_none},
                  "product_name": {"convert": ut.check_none}}
        settings.beginGroup("Connection")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

        params = {"test_plan_path": {}}
        settings.beginGroup("TestPlan")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

        params = {"main_window_geometry": {"convert": ut.convert_value_from_qsettings_to_geometry},
                  "board_window_geometry": {"convert": ut.convert_value_from_qsettings_to_geometry}}
        settings.beginGroup("Window")
        self._read_parameters_from_settings(settings, params)
        settings.endGroup()

    def _write(self, settings: QSettings) -> None:
        """
        :param settings: object in which to write the basic application settings.
        """

        params = {"frequency": {"convert": str},
                  "sensitive": {"convert": str},
                  "voltage": {"convert": str}}
        settings.beginGroup("MeasurementSettings")
        self._write_parameters_to_settings(settings, params)
        settings.endGroup()

        params = {"max_optimal_voltage": {"convert": ut.float_to_str}}
        settings.beginGroup("OptimalSearch")
        self._write_parameters_to_settings(settings, params)
        settings.endGroup()

        params = {"auto_transition": {},
                  "freeze_curve_a": {},
                  "freeze_curve_b": {},
                  "hide_curve_a": {},
                  "hide_curve_b": {},
                  "language": {"convert": ut.convert_language_to_str},
                  "last_used_dir": {"convert": str},
                  "pin_shift_warning_info": {},
                  "sound": {},
                  "tolerance": {"convert": ut.float_to_str}}
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

        params = {"test_plan_path": {"convert": str}}
        settings.beginGroup("TestPlan")
        self._write_parameters_to_settings(settings, params)
        settings.endGroup()

        params = {"main_window_geometry": {"convert": ut.convert_geometry_to_value_for_qsettings},
                  "board_window_geometry": {"convert": ut.convert_geometry_to_value_for_qsettings}}
        settings.beginGroup("Window")
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
    def save_measurement_settings(self, options: Dict[EyePointProduct.Parameter, str]) -> None:
        """
        :param options: dictionary with new measurement settings.
        """

        self.frequency = options[EyePointProduct.Parameter.frequency]
        self.sensitive = options[EyePointProduct.Parameter.sensitive]
        self.voltage = options[EyePointProduct.Parameter.voltage]

    @save_settings
    def save_param(self, **kwargs) -> None:
        """
        :param kwargs: kwarg parameters whose new values should be saved.
        """

        for name, value in kwargs.items():
            if not hasattr(self, name):
                raise AttributeError(qApp.translate("settings", 'Настройку "{}" нельзя сохранить. Пожалуйста, проверьте'
                                                                " корректность названия.").format(name))

            setattr(self, name, value)
