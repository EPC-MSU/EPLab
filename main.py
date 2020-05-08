from PyQt5.QtWidgets import QApplication
import sys

from mainwindow import EPLabWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EPLabWindow()
    window.show()
    app.exec()
