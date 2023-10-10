import os
from PyQt5.QtCore import pyqtSignal, QObject, QSettings


class SettingsHandler(QObject):

    changed = pyqtSignal()

    def __init__(self, parent=None, *args, settings: QSettings = None, path: str = None) -> None:
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
        return self.__settings.fileName()

    @settings_path.setter
    def settings_path(self, path: str) -> None:
        if path is None:
            self.__settings = None
        else:
            self.read(path=path)

    @settings_path.deleter
    def settings_path(self) -> None:
        self.__settings = None

    def _read(self, settings: QSettings) -> None:
        """
        Perform parameters reading. Should be implemented in sub-classes.
        """

        raise NotImplementedError("Read not implemented")

    def _write(self, settings: QSettings) -> None:
        """
        Perform parameters writing. Should be implemented in sub-classes.
        """

        raise NotImplementedError("Write not implemented")

    def export(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Writes settings to QSettings or file and not binds to it.
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

    def import_(self, *args, settings=None, path=None) -> None:
        """
        Reads settings from QSettings object or file and not binds to it.
        """

        if len(args) != 0:
            raise ValueError("Incorrect arguments")

        if settings is not None:
            pass
        elif path is not None:
            if not os.path.isfile(path):
                raise LookupError("Settings file '{}' not found".format(path))

            settings = QSettings(path, QSettings.IniFormat)
        else:
            raise ValueError("Settings file not given")

        settings.sync()
        self._read(settings)
        self.changed.emit()

        status = settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError("Failed to import settings from '{}': access error".format(settings.fileName()))
        if status == QSettings.FormatError:
            raise RuntimeError("Failed to import settings from '{}': format error".format(settings.fileName()))

    def read(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Reads settings from QSettings object or file and binds to it or reads from settings already bind.
        """

        if len(args) != 0:
            raise ValueError("Incorrect arguments")

        if settings is not None:
            self.__settings = settings
        elif path is not None:
            if not os.path.isfile(path):
                raise LookupError("Settings file '{}' not found".format(path))

            self.__settings = QSettings(path, QSettings.IniFormat)

        self.__settings.sync()
        self._read(self.__settings)
        self.changed.emit()

        status = self.__settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError("Failed to read settings from '{}': access error".format(self.__settings.fileName()))
        if status == QSettings.FormatError:
            raise RuntimeError("Failed to read settings from '{}': format error".format(self.__settings.fileName()))

    def sync(self) -> None:
        if self.__settings is not None:
            self.__settings.sync()
            self.read()  # Settings can be updated by another application

    def write(self, *args, settings: QSettings = None, path: str = None) -> None:
        """
        Writes settings to QSettings object or file and binds to it or writes to settings already bind.
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
            raise RuntimeError("Failed to write settings to '{}': access error".format(self.__settings.fileName()))
        if status == QSettings.FormatError:
            raise RuntimeError("Failed to write settings to '{}': format error".format(self.__settings.fileName()))
        self.__settings.sync()
