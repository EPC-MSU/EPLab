from enum import Enum, auto
from epcore.ivmeasurer.ivm10.ivm import UrpcDeviceUndefinedError
from epcore.ivmeasurer.asa10.asa import AsaConnectionError, AsaServerResponseError


class WorkMode(Enum):
    compare = auto()
    write = auto()
    test = auto()


class DeviceErrorsHandler:
    """
    All uRPC actions should be wrapped with that context manager. In case of
    device errors (for example: device disconnected) context object will change
    "all_ok" state. For example:

    # Anywhere in initialization method...
    _device_context = DeviceErrorsHandler()
    ...
    # Anywhere in any method...
    with _device_context:
      settings = device.get_settings()
      gui.set_settings(settings)  # in case of device error that method will not be called
    print("Soft still work")  # ... but that method will
    ...
    # Some periodic task in event loop:
    def _periodic():
      if _device_context.all_ok:
        # do some usual staff with device
        with _device_context:
          device.do_measure()
          # ...
      else:  # last device call was failed - device is not OK
        # Try reconnect
        if device.reconnect():
          # Success! Reset error state
          _deice_context.reset_error()
    """

    _device_errors = (OSError, RuntimeError, AsaConnectionError, AsaServerResponseError,
                      UrpcDeviceUndefinedError)

    def __init__(self):
        self._all_ok = True
        self._in_context = False

    @property
    def all_ok(self):
        return self._all_ok

    def reset_error(self):
        self._all_ok = True

    def __enter__(self):
        if self._in_context:
            raise ValueError("You should not use more than one nesting level")
        self._in_context = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._in_context = False
        if not exc_type:
            return True  # No exceptions, all is OK
        if exc_type in self._device_errors:
            self._all_ok = False
            return True  # Device exception occurred, ignore
        return False  # Here are some other exceptions, raise
