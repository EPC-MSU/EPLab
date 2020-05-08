from PyQt5.QtWidgets import QApplication
import sys
from epsound import WavPlayer

from mainwindow import EPLabWindow


if __name__ == "__main__":

    player = WavPlayer()
    player.add_sound("media/beep.wav", "beep")
    player.play("beep")  # Example

    app = QApplication(sys.argv)
    window = EPLabWindow()
    window.show()
    app.exec()
