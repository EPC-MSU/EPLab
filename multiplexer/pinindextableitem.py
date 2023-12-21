from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidgetItem


class PinIndexTableItem(QTableWidgetItem):

    def __init__(self, index: int) -> None:
        super().__init__(str(index + 1))
        self.setFlags(self.flags() ^ Qt.ItemIsEditable)
