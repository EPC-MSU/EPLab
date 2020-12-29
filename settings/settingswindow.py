from PyQt5.QtWidgets import QDialog
import os
from PyQt5 import uic


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        uic.loadUi(os.path.join("gui", "settings.ui"), self)

        self.score_treshold_button_minus.clicked.connect(parent._on_threshold_dec)
        self.score_treshold_button_plus.clicked.connect(parent._on_threshold_inc)
        self.auto_calibration_push_button.clicked.connect(parent._on_auto_calibration)
        self.score_treshold_value_lineEdit.returnPressed.connect(parent._on_threshold_set_value)
        self.load_settings_push_button.clicked.connect(parent._on_open_settings)
        self.save_settings_push_button.clicked.connect(parent._save_settings_to_file)

