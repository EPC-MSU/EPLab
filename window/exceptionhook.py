import traceback
from PyQt5.QtCore import QCoreApplication as qApp
from PyQt5.QtWidgets import QApplication, QMessageBox
from . import utils as ut


def exception_hook(exc_type: Exception, exc_value: Exception, exc_traceback: "traceback") -> None:
    """
    Function handles unexpected errors.
    :param exc_type: exception class;
    :param exc_value: exception instance;
    :param exc_traceback: traceback object.
    """

    traceback.print_exception(exc_type, exc_value, exc_traceback)
    traceback_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    text = qApp.translate("t", "Что-то пошло не так, и произошла ошибка:")
    text = f'<font color="#003399" size="+1">{text}</font>'
    ut.show_message(qApp.translate("t", "Ошибка"), text, str(exc_value), detailed_text=traceback_text,
                    icon=QMessageBox.Critical)


def show_error_window(app: QApplication, exc_type: Exception, exc_value: Exception, exc_traceback: "traceback"):
    """
    Function shows window with error.
    :param app: application;
    :param exc_type: type of exception;
    :param exc_value: exception instance;
    :param exc_traceback: traceback object which encapsulates the call stack at
    the point where the exception originally occurred.
    """

    exception_hook(exc_type, exc_value, exc_traceback)
    app.exec_()
