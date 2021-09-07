import os

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


def _log_Runtime(log, mes, err):
    """
    Function log error if err is False or raise error
    :param log:
    :param mes: message about error
    :param err: raise error if True
    :return:
    """
    # Logging to the error output of
    log(2, mes, 0)
    if err:
        raise RuntimeError(mes)


def _chek_con(file_name, log, port):
    """
    check right path to config file
    :param file_name: name of config file
    :param log:
    :param port: port of device
    :return:
    """
    # Check for a configuration file.
    file_name = os.curdir + "/" + file_name
    if not os.path.exists(file_name):
        _log_Runtime(log, "Try to open device on port " + port.decode() + ". Config file" + file_name + " not found:",
                     True)
    return file_name


def _read_conf(file_name, log, port):
    """
    Read config file and return his content, raise error if content is empty
    :param file_name: name of config file
    :param log:
    :param port: port of device
    :return:
    """
    # Read the project configuration file.
    config = configparser.ConfigParser()
    config.read(file_name)
    name = config.has_option("Global", "Name")
    if not name:
        _log_Runtime(log, "Try to open " + name + "-device on port " + port.decode() +
                     ". There is no Name field in the config file " + file_name, True)
    return config


def open_device_safe(device, conf, log):
    """
    Function open device safe: check versions of firmware, library and programm soft
    :param device: object
    :param conf: config file
    :param log: log level
    :return:
    """

    config = _read_conf(_chek_con(conf, log, device.uri), log, device.uri)  # Read config file

    # Load Lib version
    version = device.lib_version()  # Reading the library version

    Name = config.get("Global", "Name")
    mes1 = "Try to open " + Name + "-device on port " + device.uri.decode()
    if not config.has_section(version):  # Checking for a library partition
        _log_Runtime(log, mes1 + ". Library version error " + version, True)

    # Open device
    try:
        device.open()
    except Exception:
        _log_Runtime(log, mes1 + ". Device not found or cannot be opened.", True)

    s = ""  # Read controller_name # eyepoint-devices hasn't correct name!!!
    firmw = ""  # Software version.
    try:
        Identy = device.get_identity_information()  # Get identy inform
        for i in Identy._controller_name:  # _product_name:
            if (i != 0):
                s = s + chr(i)
        # Build version
        firmw = str(Identy._firmware_major) + "." + str(Identy._firmware_minor) + "." + str(Identy._firmware_bugfix)
    except Exception:
        _log_Runtime(log, mes1 + ". Undefined device. GINF command not implemented.", True)
    print(s.lower())
    if Name.lower() != s.lower():
        device.close()
        _log_Runtime(log, mes1 + ". The device is not open because it is " + s.lower(), True)

    # Build version
    ind = 0
    firms = []

    # Information comparison
    for opt in config.options(version):
        firms.append(config.get(version, opt))
        if config.get(version, opt) == firmw:
            ind = 1

    if ind == 0:
        device.close()
        mes = mes1 + "Version of the device " + firmw + "does not match the version of the library " + version
        _log_Runtime(log, mes, False)

    _log_Runtime(log, "Devise " + Name + " Lib " + version + " Firmware " + firmw, False)

    return ind, Name, version, firmw, firms
