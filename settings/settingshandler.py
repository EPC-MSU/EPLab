import os
from PyQt5.QtCore import pyqtSignal, QObject, QSettings


class SettingsHandler(QObject):

    changed: pyqtSignal = pyqtSignal()

    def __init__(self, parent=None, *args, settings=None, path: str = None) -> None:
        """
        :param parent: parent object;
        :param args:
        :param settings: new settings;
        :param path: path to file with new settings.
        """

        super().__init__(parent=parent)
        self._check_args(args)

        self.__settings: QSettings = None
        if settings is not None or path is not None:
            self.read(settings=settings, path=path)

    @property
    def settings(self) -> QSettings:
        """
        :return: settings.
        """

        return self.__settings

    @settings.setter
    def settings(self, settings: QSettings) -> None:
        """
        :param settings: new settings.
        """

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
        :return: path where settings written.
        """

        return self.__settings.fileName()

    @settings_path.setter
    def settings_path(self, path: str) -> None:
        """
        :param path: path to file with new settings.
        """

        if path is None:
            self.__settings = None
        else:
            self.read(path=path)

    @settings_path.deleter
    def settings_path(self) -> None:
        self.__settings = None

    @staticmethod
    def _check_args(args) -> None:
        if len(args) != 0:
            raise ValueError("Incorrect arguments. Keyword arguments 'settings' and 'path' can be passed")

    @staticmethod
    def _check_settings_and_path(settings: QSettings, path: str, path_required: bool = True) -> QSettings:
        if settings is None and path is not None:
            if not os.path.isfile(path) and path_required:
                raise FileNotFoundError("Settings file '{}' not found".format(path))
            settings = QSettings(path, QSettings.IniFormat)
        elif settings is None and path is None:
            raise ValueError("Settings and settings file not given")
        return settings

    def _read(self, settings: QSettings) -> None:
        """
        Performs parameters reading. Should be implemented in sub-classes.
        :param settings:
        """

        raise NotImplementedError("Read not implemented")

    def _write(self, settings: QSettings) -> None:
        """
        Performs parameters writing. Should be implemented in sub-classes.
        :param settings:
        """

        raise NotImplementedError("Write not implemented")

    def export(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Writes settings to QSettings or file and not binds to it.
        :param settings:
        :param path:
        """

        self._check_args(args)
        settings = self._check_settings_and_path(settings, path, False)
        self._write(settings)
        settings.sync()

    def import_(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Reads settings from QSettings object or file and not binds to it.
        :param settings: new settings;
        :param path: path to file with new settings.
        """

        self._check_args(args)
        settings = self._check_settings_and_path(settings, path)
        settings.sync()
        self._read(settings)
        self.changed.emit()

        status = settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError("Failed to read settings from '{}'. Access error.".format(self.__settings.fileName()))
        if status == QSettings.FormatError:
            raise RuntimeError("Failed to read settings from '{}'. Format error.".format(self.__settings.fileName()))

    def read(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Reads settings from QSettings object or file and binds to it or reads from settings already bind.
        :param settings: new settings;
        :param path: path to file with new settings.
        """

        self._check_args(args)
        self.__settings = self._check_settings_and_path(settings, path)
        self.__settings.sync()
        self._read(self.__settings)
        self.changed.emit()

        status = self.__settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError("Failed to read settings from '{}'. Access error.".format(self.__settings.fileName()))
        if status == QSettings.FormatError:
            raise RuntimeError("Failed to read settings from '{}'. Format error.".format(self.__settings.fileName()))

    def sync(self) -> None:
        if self.__settings is not None:
            self.__settings.sync()
            self.read()

    def write(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Writes settings to QSettings object or file and binds to it or writes to settings already bind.
        :param settings:
        :param path:
        """

        self._check_args(args)
        self.__settings = self._check_settings_and_path(settings, path, False)
        self._write(self.__settings)

        status = self.__settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError("Failed to write settings to '{}'. Access error.".format(self.__settings.fileName()))
        if status == QSettings.FormatError:
            raise RuntimeError("Failed to write settings to '{}'. Format error.".format(self.__settings.fileName()))
        self.__settings.sync()
