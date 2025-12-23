import os.path
from typing import Any, Dict, Optional
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QResizeEvent
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget
from circuit_detector import CircuitClassifier, predict_circuit_class_for_signature
from epcore.elements import IVCurve, MeasurementSettings
from ivviewer import Curve
from . import utils as ut
from .scaler import update_scale_of_class


@update_scale_of_class
class EquivalentCircuitWidget(QFrame):
    """
    Class for displaying equivalent circuit.
    """

    MARGIN: int = 5
    MAX_IMAGE_SIZE: int = 100
    PARAMS_LABEL_WIDTH: int = 100

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

    @property
    def min_width_with_image(self) -> int:
        """
        :return: minimum width of the widget with the equivalent circuit image.
        """

        return 3 * self.MARGIN + self.MAX_IMAGE_SIZE + self.PARAMS_LABEL_WIDTH

    def _init_ui(self) -> None:
        self.setStyleSheet("background-color: black;")

        self._label_circuit: QLabel = QLabel()
        self._label_params: QLabel = QLabel()
        self._label_params.setFixedWidth(self.PARAMS_LABEL_WIDTH)
        self._label_params.setStyleSheet(f"background-color: black; color: {self._color}")

        self._layout: QHBoxLayout = QHBoxLayout()
        self._layout.setContentsMargins(self.MARGIN, self.MARGIN, self.MARGIN, self.MARGIN)
        self._layout.setSpacing(self.MARGIN)
        if self._place_circuit_on_left:
            self._layout.addStretch(1)
            self._layout.addWidget(self._label_circuit)
            self._layout.addWidget(self._label_params)
        else:
            self._layout.addWidget(self._label_params)
            self._layout.addWidget(self._label_circuit)
            self._layout.addStretch(1)
        self.setLayout(self._layout)

    def _set_circuit_label(self, circuit_image: Optional[QPixmap]) -> None:
        """
        :param circuit_image: image of the equivalent circuit.
        """

        self._label_circuit.clear()
        if not circuit_image:
            return

        self._label_circuit.setPixmap(circuit_image)

    def _set_circuit_params(self, circuit_params: Dict[str, Any]) -> None:
        """
        :param circuit_params: dictionary with the circuit parameters.
        """

        self._label_params.clear()
        text = ""
        for name, value in circuit_params.items():
            text += f"{name}: {value}\n"
        self._label_params.setText(text)

    def clear_circuit(self) -> None:
        self._label_circuit.clear()
        self._label_params.clear()

    def hide_circuit_image(self) -> None:
        if self._label_circuit.isVisible():
            self._label_circuit.hide()

    def set_circuit(self, circuit_params: Dict[str, Any], circuit_image: Optional[QPixmap]) -> None:
        """
        :param circuit_params: dictionary with the circuit parameters;
        :param circuit_image: image of the equivalent circuit;
        """

        self._set_circuit_label(circuit_image)
        self._set_circuit_params(circuit_params)

    def show_circuit_image(self) -> None:
        if not self._label_circuit.isVisible():
            self._label_circuit.show()


class EquivalentCircuitsWidget(QWidget):
    """
    A widget with two widgets that display equivalent circuits for the current and reference signatures.
    """

    MAX_IMAGE_SIZE: int = 100
    SPACING: int = 5
    WIDGET_HEIGHT: int = 150

    def __init__(self, color_for_current_signature: str, color_for_reference_signature: str) -> None:
        """
        :param color_for_current_signature: color for the current signature;
        :param color_for_reference_signature: color for the reference signature.
        """

        super().__init__()
        self._color_for_current_signature: str = color_for_current_signature
        self._color_for_reference_signature: str = color_for_reference_signature
        self._current_curve_backup: Optional[IVCurve] = None
        self._dir_path: str = os.path.join(ut.DIR_MEDIA, "circuit_detector")
        self._reference_curve_backup: Optional[IVCurve] = None

        self._create_classifier()
        self._load_circuit_class_images()
        self._init_ui()

    def _create_classifier(self) -> None:
        model_path = os.path.join(self._dir_path, "model.pkl")
        self._classifier: CircuitClassifier = CircuitClassifier.load(model_path)

    def _init_ui(self) -> None:
        self._current_circuit_widget: EquivalentCircuitWidget = EquivalentCircuitWidget(
            self._color_for_current_signature)
        self._reference_circuit_widget: EquivalentCircuitWidget = EquivalentCircuitWidget(
            self._color_for_reference_signature, place_circuit_on_left=False)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.SPACING)
        layout.addWidget(self._current_circuit_widget)
        layout.addWidget(self._reference_circuit_widget)

        self.setFixedHeight(self.WIDGET_HEIGHT)
        self.setLayout(layout)

    def _load_circuit_class_images(self) -> None:
        self._circuit_class_images: Dict[str, QPixmap] = dict()
        dir_with_images = os.path.join(self._dir_path, "circuit_classes")
        for file_name in os.listdir(dir_with_images):
            file_path = os.path.join(dir_with_images, file_name)
            if os.path.isfile(file_path):
                class_name = os.path.splitext(os.path.basename(file_path))[0]
                pixmap = QPixmap(file_path).scaled(self.MAX_IMAGE_SIZE, self.MAX_IMAGE_SIZE, Qt.KeepAspectRatio)
                self._circuit_class_images[class_name] = pixmap

    def _update_curve(self, curve: Optional[Curve], curve_backup: Optional[Curve],
                      settings: Optional[MeasurementSettings], circuit_widget: EquivalentCircuitWidget) -> None:
        """
        :param curve: signature for which an equivalent circuit must be constructed;
        :param curve_backup: a signature for which an equivalent circuit has already been constructed;
        :param settings: measurement settings at which signatures were measured;
        :param circuit_widget: a widget that displays an equivalent circuit.
        """

        if not curve:
            circuit_widget.clear_circuit()
        elif curve != curve_backup and settings:
            params = predict_circuit_class_for_signature(IVCurve(curve.currents, curve.voltages), settings,
                                                         self._classifier)
            circuit_class_name = params.get("class_name", "")
            circuit_class_image = self._circuit_class_images.get(circuit_class_name, None)
            print(circuit_class_image)
            circuit_widget.set_circuit(params, circuit_class_image)

    def clear_circuits(self) -> None:
        self._current_circuit_widget.clear_circuit()
        self._reference_circuit_widget.clear_circuit()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        :param event: resize event.
        """

        if self.width() < 2 * self._current_circuit_widget.min_width_with_image:
            self._current_circuit_widget.hide_circuit_image()
            self._reference_circuit_widget.hide_circuit_image()
        else:
            self._current_circuit_widget.show_circuit_image()
            self._reference_circuit_widget.show_circuit_image()

        super().resizeEvent(event)

    def update_circuits(self, current_curve: Optional[Curve], reference_curve: Optional[Curve],
                        settings: Optional[MeasurementSettings]) -> None:
        """
        :param current_curve: current signature for which an equivalent circuit must be constructed;
        :param reference_curve: reference signature for which an equivalent circuit must be constructed;
        :param settings: measurement settings at which signatures were measured.
        """

        self._update_curve(current_curve, self._current_curve_backup, settings, self._current_circuit_widget)
        self._current_curve_backup = current_curve

        self._update_curve(reference_curve, self._reference_curve_backup, settings, self._reference_circuit_widget)
        self._reference_curve_backup = reference_curve
