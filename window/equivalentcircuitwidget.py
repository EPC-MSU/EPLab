from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel


class EquivalentCircuitWidget(QFrame):
    """
    Class for displaying equivalent circuit.
    """

    def __init__(self, color: str, place_circuit_on_left: bool = True) -> None:
        """
        :param color: text color for displaying circuit parameters;
        :param place_circuit_on_left: if True, then you need to place the circuit to the left of the parameters,
        otherwise to the right.
        """

        super().__init__()
        self._color: str = color
        self._place_circuit_on_left: bool = place_circuit_on_left
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("background-color: black;")

        self._label_circuit: QLabel = QLabel()
        self._label_params: QLabel = QLabel()
        self._label_params.setStyleSheet(f"background-color: black; color: {self._color}")

        self._layout: QHBoxLayout = QHBoxLayout()
        if self._place_circuit_on_left:
            self._layout.addStretch(1)
            self._layout.addWidget(self._label_circuit)
            self._layout.addWidget(self._label_params)
        else:
            self._layout.addWidget(self._label_params)
            self._layout.addWidget(self._label_circuit)
            self._layout.addStretch(1)
        self.setLayout(self._layout)

    def _set_circuit_label(self, circuit_image_path: str) -> None:
        """
        :param circuit_image_path:
        """

        self._label_circuit.clear()
        if not circuit_image_path:
            return

        pixmap = QPixmap(circuit_image_path)
        self._label_circuit.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))

    def _set_circuit_params(self, **circuit_params) -> None:
        """
        :param circuit_params:
        """

        self._label_params.clear()
        text = ""
        for name, value in circuit_params.items():
            text += f"{name}: {value}\n"
        self._label_params.setText(text)

    def clear_circuit(self) -> None:
        self._label_circuit.clear()
        self._label_params.clear()

    def set_circuit(self, circuit_image_path: Optional[str], **circuit_params) -> None:
        """
        :param circuit_image_path: path to the image with the electrical circuit;
        :param circuit_params: circuit parameters.
        """

        self._set_circuit_label(circuit_image_path)
        self._set_circuit_params(**circuit_params)
