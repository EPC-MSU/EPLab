from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QPushButton, QWidget, QFileDialog, QLabel
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot
from PyQt5 import uic
import epcore.filemanager as epfilemanager
from boardwindow import BoardWidget
from boardwindow import GraphicsManualPinItem
from ivviewer import Viewer as IVViewer


class EPLabWindow(QMainWindow):
    def __init__(self):
        super(EPLabWindow, self).__init__()

        uic.loadUi("gui/mainwindow.ui", self)  # Load the .ui file

        self._board_window = BoardWidget()
        self._board_window.resize(600, 600)
        self._board_window.setWindowIcon(QIcon("media/ico.png"))  # TODO: don't duplicate base configurations
        self._board_window.setWindowTitle("EPLab - Board")        # TODO: don't duplicate base configurations

        self._iv_window = IVViewer()
        self._iv_window.resize(600, 600)
        self._iv_window.setWindowIcon((QIcon("media/ico.png")))   # TODO: don't duplicate base configurations
        self._iv_window.setWindowTitle("EPLab - IVC")             # TODO: don't duplicate base configurations

        self.setCentralWidget(self._iv_window)

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
