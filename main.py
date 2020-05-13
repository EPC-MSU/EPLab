from PyQt5.QtWidgets import QApplication
import sys
import logging
from epsound import WavPlayer

from mainwindow import EPLabWindow


if __name__ == "__main__":

    logging.basicConfig(level=logging.ERROR)

    player = WavPlayer()
    player.add_sound("media/beep.wav", "beep")
    try:
        player.play("beep")  # Example
    except RuntimeError:  # TODO: epsound must have method like "is_driver_available" or custom error class
        logging.error("Unable to play sound")
        pass  # TODO: epsound must have method like "mute" to mute all sound in case of driver error

    app = QApplication(sys.argv)
    window = EPLabWindow()
    window.resize(1200, 600)
    window.show()
    app.exec()
