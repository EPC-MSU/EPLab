import os
from typing import Any, Dict
from PyQt5.QtCore import pyqtSignal, QObject, QSettings
from . import utils as ut


class SettingsHandler(QObject):

    changed: pyqtSignal = pyqtSignal()

    def __init__(self, parent=None, *args, settings: QSettings = None, path: str = None) -> None:
        """
        :param parent: parent object;
        :param args:
        :param settings: object that will be used during work;
        :param path: path to the settings file.
        """

        super().__init__(parent=parent)
        if len(args) != 0:
            raise ValueError("Incorrect arguments")

        if settings is not None:
            self.__settings = settings
        elif path is not None:
            self.__settings = QSettings(path, QSettings.IniFormat)
        else:
            self.__settings = None

        if self.__settings is not None:
            self.read()

    @property
    def settings(self) -> QSettings:
        return self.__settings

    @settings.setter
    def settings(self, settings: QSettings) -> None:
        if settings is None:
            self.__settings = None
        else:
            self.read(settings=settings)

    @settings.deleter
    def settings(self) -> None:
        self.__settings = None

    @property
    def settings_path(self) -> str:
        """
        :return: path to the settings file.
        """

        return self.__settings.fileName()

    @settings_path.setter
    def settings_path(self, path: str) -> None:
        """
        :param path: new path to the settings file.
        """

        if path is None:
            self.__settings = None
        else:
            self.read(path=path)

    @settings_path.deleter
    def settings_path(self) -> None:
        self.__settings = None

    def _get_default_value(self, attribute_name: str) -> Any:
        """
        :param attribute_name: name of the attribute whose default value to get.
        :return: default value for a given attribute.
        """

        default = getattr(self, f"{attribute_name}_default", None)
        if default is None:
            default = getattr(self.__class__, attribute_name, None)
        return default

    def _read(self, settings: QSettings) -> None:
        """
        Performs parameters reading. Should be implemented in subclasses.
        :param settings: QSettings object from which parameter values need to be read.
        """

        raise NotImplementedError("Read not implemented")

    def _read_parameters_from_settings(self, settings: QSettings, parameters: Dict[str, Dict[str, Any]]) -> None:
        """
        :param settings: QSettings object from which parameter values need to be read;
        :param parameters: dictionary with parameters whose values need to be read.
        """

        for parameter_name, parameter_data in parameters.items():
            convert_function = parameter_data.get("convert", str)
            required = parameter_data.get("required", False)
            default = self._get_default_value(parameter_name)
            value = ut.get_parameter(settings, parameter_name, convert=convert_function, required=required,
                                     default=default)
            setattr(self, parameter_name, value)

    def _write(self, settings: QSettings) -> None:
        """
        Performs parameters writing. Should be implemented in subclasses.
        :param settings: QSettings object into which parameter values should be written.
        """

        raise NotImplementedError("Write not implemented")

    def _write_parameters_to_settings(self, settings: QSettings, parameters: Dict[str, Dict[str, Any]]) -> None:
        """
        :param settings: QSettings object into which parameter values should be written;
        :param parameters: dictionary with parameters whose values need to be written.
        """

        for parameter_name, parameter_data in parameters.items():
            value = getattr(self, parameter_name, None)
            convert_function = parameter_data.get("convert", None)
            if convert_function is not None:
                value = convert_function(value)
            ut.set_parameter(settings, parameter_name, value)

    def export(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Writes settings to QSettings or file and not binds to it.
        :param settings:
        :param path:
        """

        if len(args) != 0:
            raise ValueError("Incorrect arguments")

        if settings is not None:
            pass
        elif path is not None:
            settings = QSettings(path, QSettings.IniFormat)
        else:
            raise ValueError("Settings file not given")

        self._write(settings)
        settings.sync()

    def import_(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Reads settings from QSettings object or file and not binds to it.
        :param settings:
        :param path:
        """

        if len(args) != 0:
            raise ValueError("Incorrect arguments")

        if settings is not None:
            pass
        elif path is not None:
            if not os.path.isfile(path):
                raise LookupError(f"Settings file '{path}' not found")

            settings = QSettings(path, QSettings.IniFormat)
        else:
            raise ValueError("Settings file not given")

        settings.sync()
        self._read(settings)
        self.changed.emit()

        status = settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError(f"Failed to import settings from '{settings.fileName()}': access error")

        if status == QSettings.FormatError:
            raise RuntimeError(f"Failed to import settings from '{settings.fileName()}': format error")

    def read(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Reads settings from QSettings object or file and binds to it or reads from settings already bind.
        :param settings: QSettings object from which parameter values need to be read;
        :param path:
        """

        if len(args) != 0:
            raise ValueError("Incorrect arguments")

        if settings is not None:
            self.__settings = settings
        elif path is not None:
            if not os.path.isfile(path):
                raise LookupError(f"Settings file '{path}' not found")

            self.__settings = QSettings(path, QSettings.IniFormat)

        self.__settings.sync()
        self._read(self.__settings)
        self.changed.emit()

        status = self.__settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError(f"Failed to read settings from '{self.__settings.fileName()}': access error")

        if status == QSettings.FormatError:
            raise RuntimeError(f"Failed to read settings from '{self.__settings.fileName()}': format error")

    def set_default_values(self, **kwargs) -> None:
        """
        :param kwargs: dictionary with default values of attributes.
        """

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, f"{key}_default", value)

    def sync(self) -> None:
        if self.__settings is not None:
            self.__settings.sync()
            self.read()  # Settings can be updated by another application

    def write(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Writes settings to QSettings object or file and binds to it or writes to settings already bind.
        :param settings: QSettings object into which parameter values should be written;
        :param path:
        """

        if len(args) != 0:
            raise ValueError("Incorrect arguments")

        if settings is not None:
            self.__settings = settings
        elif path is not None:
            self.__settings = QSettings(path, QSettings.IniFormat)

        self._write(self.__settings)

        status = self.__settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError(f"Failed to write settings to '{self.__settings.fileName()}': access error")

        if status == QSettings.FormatError:
            raise RuntimeError(f"Failed to write settings to '{self.__settings.fileName()}': format error")

        self.__settings.sync()
