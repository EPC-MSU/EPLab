import ctypes
import os
import sys
from argparse import ArgumentParser, Namespace

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_FONT_DPI"] = "120"

# Указываем Windows, что наше приложение само управляет DPI
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    shcore = ctypes.windll.shcore
    # Получаем DPI главного экрана
    logical_dpi = shcore.GetScaleFactorForDevice(0) / 100
    print("___", logical_dpi)
except:
    logical_dpi = 1.25 # Резервное значение, если не удалось определить

# 2. Устанавливаем масштаб вручную
import os
os.environ["QT_SCALE_FACTOR"] = str(logical_dpi)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # enable high dpi scaling
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)  # use high dpi icons
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

from epcore.product import EyePointProduct
from window import utils as ut
from window.eplabwindow import EPLabWindow
from window.exceptionhook import exception_hook, show_error_window
from window.logger import set_logger


if getattr(sys, "frozen", False):
    import pyi_splash
    pyi_splash.close()


sys.excepthook = exception_hook


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
    try:
        launch_eplab(app_, parsed_args)
    except Exception:
        show_error_window(app_, *sys.exc_info())
