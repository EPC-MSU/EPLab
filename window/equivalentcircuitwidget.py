import os.path
from typing import Any, Dict, Optional
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QResizeEvent
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget
from circuit_detector import CircuitClassifier, detect_parameters, predict_circuit_class_for_iv_curve
from epcore.elements import IVCurve, MeasurementSettings
from ivviewer import Curve
from . import utils as ut
from .scaler import update_scale_of_class


@update_scale_of_class
class EquivalentCircuitWidget(QFrame):
    """
    Class for displaying equivalent circuit.
    """

    def __init__(self, color: str, margin: int, params_label_width: int, place_circuit_on_left: bool = True) -> None:
        """
        :param color: text color for displaying circuit parameters;
        :param place_circuit_on_left: if True, then you need to place the circuit to the left of the parameters,
        otherwise to the right.
        """

        super().__init__()
        self._color: str = color
        self._place_circuit_on_left: bool = place_circuit_on_left
        self._init_ui(margin, params_label_width)

    def _init_ui(self, margin: int, params_label_width: int) -> None:
        self.setStyleSheet("background-color: black;")

        self._label_circuit: QLabel = QLabel()
        self._label_params: QLabel = QLabel()
        self._label_params.setFixedWidth(params_label_width)
        self._label_params.setStyleSheet(f"background-color: black; color: {self._color}")

        self._layout: QHBoxLayout = QHBoxLayout()
        self._layout.setContentsMargins(margin, margin, margin, margin)
        self._layout.setSpacing(margin)
        if self._place_circuit_on_left:
            self._layout.addStretch(1)
            self._layout.addWidget(self._label_circuit)
            self._layout.addWidget(self._label_params, alignment=Qt.AlignmentFlag.AlignTop)
        else:
            self._layout.addWidget(self._label_params, alignment=Qt.AlignmentFlag.AlignTop)
            self._layout.addWidget(self._label_circuit)
            self._layout.addStretch(1)
        self.setLayout(self._layout)

    def clear_circuit(self) -> None:
        self._label_circuit.clear()
        self._label_params.clear()

    def hide_circuit_image(self) -> None:
        if self._label_circuit.isVisible():
            self._label_circuit.hide()

    def set_circuit_image(self, circuit_image: Optional[QPixmap]) -> None:
        """
        :param circuit_image: image of the equivalent circuit.
        """

        self._label_circuit.clear()
        if not circuit_image:
            return

        self._label_circuit.setPixmap(circuit_image)

    def set_circuit_params(self, circuit_params: Dict[str, Any]) -> None:
        """
        :param circuit_params: dictionary with the circuit parameters.
        """

        self._label_params.clear()
        text = ""
        for name, value in circuit_params.items():
            units = ut.get_units_of_measurement_for_physical_quantity(name)
            if units and isinstance(value, (int, float)):
                text += f"{ut.get_str_representation_of_physical_quantity(name, value, units)}\n"
            else:
                text += f"{name}: {value}\n"
        self._label_params.setText(text)

    def show_circuit_image(self) -> None:
        if not self._label_circuit.isVisible():
            self._label_circuit.show()

    def show_error(self, error: str) -> None:
        """
        :param error: error text.
        """

        self._label_params.setText(error)


class EquivalentCircuitsWidget(QWidget):
    """
    A widget with two widgets that display equivalent circuits for the current and reference signatures.
    """

    MARGIN: int = 5
    MAX_IMAGE_SIZE: int = 140
    PARAMS_LABEL_WIDTH: int = 100
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

    @property
    def min_width_with_images(self) -> int:
        """
        :return: minimum width of the widget with the equivalent circuit images.
        """

        return 2 * (3 * self.MARGIN + self._max_image_width + self.PARAMS_LABEL_WIDTH)

    def _create_classifier(self) -> None:
        model_path = os.path.join(self._dir_path, "model.pkl")
        self._classifier: CircuitClassifier = CircuitClassifier.load(model_path)

    def _init_ui(self) -> None:
        self._current_circuit_widget: EquivalentCircuitWidget = EquivalentCircuitWidget(
            self._color_for_current_signature, self.MARGIN, self.PARAMS_LABEL_WIDTH)
        self._reference_circuit_widget: EquivalentCircuitWidget = EquivalentCircuitWidget(
            self._color_for_reference_signature, self.MARGIN, self.PARAMS_LABEL_WIDTH, False)

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
        self._max_image_width: int = 0
        for file_name in os.listdir(dir_with_images):
            file_path = os.path.join(dir_with_images, file_name)
            if os.path.isfile(file_path):
                class_name = os.path.splitext(os.path.basename(file_path))[0]
                pixmap = QPixmap(file_path).scaledToHeight(self.MAX_IMAGE_SIZE,
                                                           Qt.TransformationMode.SmoothTransformation)
                self._max_image_width = max(pixmap.width(), self._max_image_width)
                self._circuit_class_images[class_name] = pixmap

    def _update_curve(self, curve: Optional[Curve], curve_backup: Optional[Curve],
                      settings: Optional[MeasurementSettings], comment: str, circuit_widget: EquivalentCircuitWidget
                      ) -> None:
        """
        :param curve: signature for which an equivalent circuit must be constructed;
        :param curve_backup: a signature for which an equivalent circuit has already been constructed;
        :param settings: measurement settings at which signatures were measured;
        :param comment: comment on the pin where the signatures were measured;
        :param circuit_widget: a widget that displays an equivalent circuit.
        """

        if curve == curve_backup:
            return

        circuit_widget.clear_circuit()
        if not curve:
            return

        try:
            results = predict_circuit_class_for_iv_curve(IVCurve(curve.currents, curve.voltages), settings,
                                                         self._classifier, comment)

            circuit_name = results["class_name"]
            circuit_image = self._circuit_class_images.get(circuit_name, None)
            circuit_widget.set_circuit_image(circuit_image)

            circuit_features = results["features"]
            circuit_features.class_name = circuit_name
            try:
                circuit_params = detect_parameters(circuit_features)
                circuit_widget.set_circuit_params(circuit_params)
            except NotImplementedError:
                circuit_widget.show_error("Not implemented")
            except ValueError:
                circuit_widget.show_error("Parameter detection failed")
        except Exception:
            circuit_widget.show_error("Recognition failed")

    def clear_circuits(self) -> None:
        self._current_circuit_widget.clear_circuit()
        self._reference_circuit_widget.clear_circuit()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        :param event: resize event.
        """

        if self.width() < self.min_width_with_images:
            self._current_circuit_widget.hide_circuit_image()
            self._reference_circuit_widget.hide_circuit_image()
        else:
            self._current_circuit_widget.show_circuit_image()
            self._reference_circuit_widget.show_circuit_image()

        super().resizeEvent(event)

    def update_circuits(self, current_curve: Optional[Curve], reference_curve: Optional[Curve],
                        settings: Optional[MeasurementSettings], comment: Optional[str] = "") -> None:
        """
        :param current_curve: current signature for which an equivalent circuit must be constructed;
        :param reference_curve: reference signature for which an equivalent circuit must be constructed;
        :param settings: measurement settings at which signatures were measured;
        :param comment: comment on the pin where the signatures were measured.
        """

        self._update_curve(current_curve, self._current_curve_backup, settings, comment, self._current_circuit_widget)
        self._current_curve_backup = current_curve

        self._update_curve(reference_curve, self._reference_curve_backup, settings, comment,
                           self._reference_circuit_widget)
        self._reference_curve_backup = reference_curve
