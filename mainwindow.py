from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QPushButton, QWidget, QFileDialog, QLabel
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot
import epcore.filemanager as epfilemanager
from boardwindow import BoardWidget
from boardwindow import GraphicsManualPinItem
from ivviewer import Viewer as IVViewer


class EPLabWindow(QMainWindow):
    def __init__(self):
        super(EPLabWindow, self).__init__()

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.setWindowTitle("EPLab")
        self.setWindowIcon(QIcon("media/ico.png"))
        self.resize(250, 100)

        layout = QVBoxLayout(central_widget)

        self._load_board_btn = QPushButton("Load board")
        layout.addWidget(self._load_board_btn)
        self._load_board_btn.clicked.connect(self._on_load_board)

        self._board_view_btn = QPushButton("View board")
        layout.addWidget(self._board_view_btn)
        self._board_view_btn.clicked.connect(self._on_view_board)

        self._iv_view_btn = QPushButton("View IVC")
        layout.addWidget(self._iv_view_btn)
        self._iv_view_btn.clicked.connect(self._on_view_iv)

        self._point_data_lbl = QLabel()
        layout.addWidget(self._point_data_lbl)

        self._board_window = BoardWidget()
        self._board_window.resize(600, 600)
        self._board_window.setWindowIcon(QIcon("media/ico.png"))
        self._board_window.setWindowTitle("EPLab - Board")

        self._iv_window = IVViewer()
        self._iv_window.resize(200, 200)
        self._iv_window.setWindowIcon((QIcon("media/ico.png")))
        self._iv_window.setWindowTitle("EPLab - IVC")

    @pyqtSlot()
    def _on_load_board(self):
        dialog = QFileDialog()
        filename = dialog.getOpenFileName(self, "Open board", filter="JSON (*.json)")[0]
        if filename:
            self._board_window.set_board(epfilemanager.load_board_from_ufiv(filename))
            self._board_window.workspace.on_component_left_click.connect(self._on_component_click)

    @pyqtSlot()
    def _on_view_board(self):
        self._board_window.show()

    @pyqtSlot()
    def _on_view_iv(self):
        self._iv_window.show()

    @pyqtSlot(GraphicsManualPinItem)
    def _on_component_click(self, component: GraphicsManualPinItem):
        self._point_data_lbl.setText(f"Num: {component.number} x: {component.x()} y: {component.y()}")
