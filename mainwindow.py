from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QPushButton, QWidget, QFileDialog
from PyQt5.QtGui import QIcon
import epcore.filemanager as epfilemanager
from boardwindow import BoardWidget


class EPLabWindow(QMainWindow):
    def __init__(self):
        super(EPLabWindow, self).__init__()

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.setWindowTitle("EPLab")
        self.setWindowIcon(QIcon("ico.png"))
        self.resize(250, 100)

        layout = QVBoxLayout(central_widget)

        self._load_board_btn = QPushButton("Load board")
        layout.addWidget(self._load_board_btn)
        self._load_board_btn.clicked.connect(self._on_load_board)

        self._board_view_btn = QPushButton("View board")
        layout.addWidget(self._board_view_btn)
        self._board_view_btn.clicked.connect(self._on_view_board)

        self._board_window = BoardWidget()
        self._board_window.resize(600, 600)
        self._board_window.setWindowIcon(QIcon("ico.png"))
        self._board_window.setWindowTitle("EyePoint Lab - Board")

    def _on_load_board(self):
        dialog = QFileDialog()
        filename = dialog.getOpenFileName(self, "Open board", filter="JSON (*.json)")[0]
        if filename:
            self._board_window.set_board(epfilemanager.load_board_from_ufiv(filename))

    def _on_view_board(self):
        self._board_window.show()
