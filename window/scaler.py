from PyQt5.QtCore import QCoreApplication as qApp


def get_scale_factor() -> float:
    """
    :return: scale factor for the current screen scale relative to the normal scale 96.
    """

    app = qApp.instance()
    for screen in app.screens():
        return screen.logicalDotsPerInch() / 96

    return 1
