import ctypes
import os
import sys
from argparse import ArgumentParser, Namespace
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Configuring font display at different screen sizes.
# First, we tell the OS not to interfere
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Adjusting the rounding behavior. This fixes the Device Pixel Ratio: 1.0 -> 1.25
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
# Additional flags
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # enable high dpi scaling
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # use high dpi icons

if True:
    # A trick to fix the flake8 "E402 module level import not at top of file" error
    from epcore.product import EyePointProduct
    from window import utils as ut
    from window.eplabwindow import EPLabWindow
    from window.exceptionhook import exception_hook, show_error_window
    from window.logger import set_logger

if getattr(sys, "frozen", False):
    import pyi_splash
    pyi_splash.close()

sys.excepthook = exception_hook


def increase_font_size_for_larger_view(app: QApplication) -> None:
    """
    Forcefully increase the font size by 1 point if the zoom level is greater than 100%.
    :param app: application.
    """

    if 1 < app.primaryScreen().devicePixelRatio():
        font = app.font()
        font.setPointSizeF(font.pointSize() + 1)
        app.setFont(font)


def launch_eplab(app: QApplication, args: Namespace) -> None:
    """
    :param app: application;
    :param args: arguments from command line.
    """

    window = EPLabWindow(EyePointProduct(ut.read_json(args.config)), args.test, args.ref, args.en, args.plan_path)
    window.show()
    app.exec()


if __name__ == "__main__":
    set_logger()

    parser = ArgumentParser(description="EyePoint Lab")
    parser.add_argument("plan_path", help="Path to the test plan to be opened", type=str, nargs="?", default=None)
    parser.add_argument("--config", help="Path to specific EPLab config file", default=None)
    parser.add_argument("--en", help="Use English version", action="store_true", default=False)
    parser.add_argument("--ref", help="Path to REF [additional] measurer (type 'virtual' for virtual mode)")
    parser.add_argument("--test", help="Path to TEST measurer (type 'virtual' for virtual mode)", default=None)
    parsed_args = parser.parse_args()

    app_ = QApplication(sys.argv)
    increase_font_size_for_larger_view(app_)

    try:
        launch_eplab(app_, parsed_args)
    except Exception:
        show_error_window(app_, *sys.exc_info())
