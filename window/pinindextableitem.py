from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidgetItem


class PinIndexTableItem(QTableWidgetItem):
    """
    Table item for displaying pin indexes.
    """

    def __init__(self, index: int) -> None:
        """
        :param index: pin index.
        """

        super().__init__()
        self.setFlags(self.flags() ^ Qt.ItemIsEditable)
        self.set_index(index)

    def set_index(self, index: int) -> None:
        """
        :param index: pin index.
        """

        self.setText(str(index + 1))
