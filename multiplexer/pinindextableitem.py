from PyQt5.QtWidgets import QTableWidgetItem


class PinIndexTableItem(QTableWidgetItem):

    def __init__(self, index: int) -> None:
        super().__init__(str(index + 1))
