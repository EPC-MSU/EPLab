import os

from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QSettings


__all__ = ["SettingsHandler"]


class SettingsHandler(QObject):
    changed = QtCore.pyqtSignal()

    def __init__(self, parent=None, *args, settings=None, path=None):
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
    def settings(self):
        return self.__settings

    @settings.setter
    def settings(self, settings):
        if settings is None:
            self.__settings = None
        else:
            self.read(settings=settings)

    @settings.deleter
    def settings(self):
        self.__settings = None

    @property
    def settings_path(self):
        return self.__settings.fileName()

    @settings_path.setter
    def settings_path(self, path):
        if path is None:
            self.__settings = None
        else:
            self.read(path=path)

    @settings_path.deleter
    def settings_path(self):
        self.__settings = None

    def read(self, *args, settings=None, path=None):
        """Reads settings from QSettings object or file and binds to it or reads from settings already bind."""

        if len(args) != 0:
            raise ValueError("Incorrect arguments")

        if settings is not None:
            self.__settings = settings
        elif path is not None:
            if not os.path.isfile(path):
                raise LookupError("Settings file not found: {}".format(path))

            self.__settings = QSettings(path, QSettings.IniFormat)

        self.__settings.sync()
        self._read(self.__settings)
        self.changed.emit()

        status = self.__settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError("Can\'t read settings from \"{}\": Access error".format(self.__settings.fileName()))
        elif status == QSettings.FormatError:
            raise RuntimeError("Can\'t read settings from \"{}\": Format error".format(self.__settings.fileName()))

    def import_(self, *args, settings=None, path=None):
        """Reads settings from QSettings object or file and not binds to it."""

        if len(args) != 0:
            raise ValueError("Incorrect arguments")

        if settings is not None:
            pass
        elif path is not None:
            if not os.path.isfile(path):
                raise LookupError("Settings file not found: {}".format(path))

            settings = QSettings(path, QSettings.IniFormat)
        else:
            raise ValueError("Settings file not given")

        settings.sync()
        self._read(settings)
        self.changed.emit()

        status = settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError("Can\'t import settings from \"{}\": Access error".format(settings.fileName()))
        elif status == QSettings.FormatError:
            raise RuntimeError("Can\'t import settings from \"{}\": Format error".format(settings.fileName()))

    def write(self, *args, settings=None, path=None):
        """Writes settings to QSettings object or file and binds to it or writes to settings already bind."""

        if len(args) != 0:
            raise ValueError("Incorrect arguments")

        if settings is not None:
            self.__settings = settings
        elif path is not None:
            self.__settings = QSettings(path, QSettings.IniFormat)

        self._write(self.__settings)

        status = self.__settings.status()
        if status == QSettings.AccessError:
            raise RuntimeError("Can\'t write settings to \"{}\": Access error".format(self.__settings.fileName()))
        elif status == QSettings.FormatError:
            raise RuntimeError("Can\'t write settings to \"{}\": Format error".format(self.__settings.fileName()))

        self.__settings.sync()

    def export(self, *args, settings=None, path=None):
        """Writes settings to QSettings or file and not binds to it."""

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

    def sync(self):
        if self.__settings is not None:
            self.__settings.sync()
            self.read()  # Settings can be updated by another application

    def _read(self, settings):
        """Perform parameters reading. Should be implemented in sub-classes."""

        raise NotImplementedError("Read not implemented")

    def _write(self, settings):
        """Perform parameters writing. Should be implemented in sub-classes."""

        raise NotImplementedError("Write not implemented")
