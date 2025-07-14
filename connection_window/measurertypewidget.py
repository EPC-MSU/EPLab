"""
File with class to select measurer type.
"""

import os
from functools import partial
from typing import Dict, Optional
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QCoreApplication as qApp, Qt, QTimer
from PyQt5.QtWidgets import QGridLayout, QRadioButton, QScrollArea, QVBoxLayout, QWidget
from window.utils import DIR_MEDIA
from . import utils as ut
from .productname import MeasurerType, ProductName


class MeasurerTypeWidget(QWidget):
    """
    Class for widget to select measurer type.
    """

    ADDITIONAL_SCROLL_AREA_WIDTH: int = 25
    IMAGE_SIZES: Dict[str, int] = {ProductName.EYEPOINT_A2: 70,
                                   ProductName.EYEPOINT_H10: 100,
                                   ProductName.EYEPOINT_S2: 100,
                                   ProductName.EYEPOINT_U21: 80,
                                   ProductName.EYEPOINT_U22: 100,
                                   ProductName.EYEPOINT_U32: 80,
                                   ProductName.MK22: 80}
    TIME_TO_SHOW_INITIAL_PRODUCT_MS: int = 50
    WIDGET_HEIGHT: int = 200
    measurer_type_changed: pyqtSignal = pyqtSignal(MeasurerType, bool)

    def __init__(self, initial_product_name: ProductName = None) -> None:
        """
        :param initial_product_name: initial product name.
        """

        super().__init__()
        self.radio_buttons_products: Optional[Dict[ProductName, QRadioButton]] = None
        self._initial_product_name: ProductName = initial_product_name or ProductName.EYEPOINT_A2
        self._init_ui()
        self._timer: QTimer = QTimer()
        self._timer.timeout.connect(self._show_initial_product)
        self._timer.setSingleShot(True)
        self._timer.start(MeasurerTypeWidget.TIME_TO_SHOW_INITIAL_PRODUCT_MS)

    def _create_labels_and_radio_buttons_for_products(self) -> QGridLayout:
        """
        :return: layout, in which images and radio buttons of products are located.
        """

        grid_layout = QGridLayout()
        grid_layout.setSpacing(5)
        self.radio_buttons_products = dict()
        for row, product_name in enumerate(ProductName.get_product_names_for_platform()):
            radio_button = QRadioButton(ProductName.get_product_name_to_show_in_connection_window(product_name), self)
            measurer_type = ProductName.get_measurer_type_by_product_name(product_name)
            radio_button.toggled.connect(partial(self.select_measurer_type, measurer_type))
            label = ut.create_label_with_image(os.path.join(DIR_MEDIA, f"{product_name.name}.png"),
                                               MeasurerTypeWidget.IMAGE_SIZES[product_name],
                                               MeasurerTypeWidget.IMAGE_SIZES[product_name])
            grid_layout.addWidget(label, row, 0, Qt.AlignHCenter | Qt.AlignVCenter)
            grid_layout.addWidget(radio_button, row, 1, Qt.AlignVCenter)
            self.radio_buttons_products[product_name] = radio_button

        self.radio_buttons_products[self._initial_product_name].setChecked(True)
        return grid_layout

    def _get_width_hint(self) -> int:
        """
        :return: scroll area width hint.
        """

        grid_layout = self.scroll_area.widget().layout()
        max_width = None
        for row in range(grid_layout.rowCount()):
            row_width = 0
            for column in range(grid_layout.columnCount()):
                widget_width = grid_layout.itemAtPosition(row, column).sizeHint().width()
                row_width += widget_width

            if max_width is None or max_width < row_width:
                max_width = row_width

        margins = grid_layout.contentsMargins()
        max_width += (margins.left() + margins.right() + grid_layout.spacing() +
                      self.scroll_area.verticalScrollBar().sizeHint().width() +
                      MeasurerTypeWidget.ADDITIONAL_SCROLL_AREA_WIDTH)
        return max_width

    def _init_ui(self) -> None:
        """
        Method initializes widgets on main widget.
        """

        widget = QWidget()
        self.scroll_area: QScrollArea = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(widget)

        layout_with_products = self._create_labels_and_radio_buttons_for_products()
        widget.setLayout(layout_with_products)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)
        self.setToolTip(qApp.translate("connection_window", "Тип измерителя"))
        self.setFixedHeight(MeasurerTypeWidget.WIDGET_HEIGHT)
        self.adjustSize()

    @pyqtSlot()
    def _show_initial_product(self) -> None:
        """
        Slot scrolls the contents of the scroll area so that the initial product name is visible inside the viewport.
        """

        radio_button = self.radio_buttons_products[self._initial_product_name]
        self.scroll_area.ensureWidgetVisible(radio_button)

        width = self._get_width_hint()
        self.scroll_area.setFixedWidth(width)

    def get_product_name(self) -> Optional[ProductName]:
        """
        :return: checked product name.
        """

        for product_name, radio_button in self.radio_buttons_products.items():
            if radio_button.isChecked():
                return product_name

        return None

    @pyqtSlot(MeasurerType, bool)
    def select_measurer_type(self, measurer_type: MeasurerType, radio_button_status: bool) -> None:
        """
        Slot handles signal that new measurer type was selected.
        :param measurer_type: selected measurer type;
        :param radio_button_status: if True then radio button was checked.
        """

        if not radio_button_status:
            return

        show_two_channels = self.get_product_name() not in ProductName.get_single_channel_products()
        self.measurer_type_changed.emit(measurer_type, show_two_channels)

    def send_initial_values(self) -> None:
        """
        Method emits signal.
        """

        measurer_type = ProductName.get_measurer_type_by_product_name(self._initial_product_name)
        self.select_measurer_type(measurer_type, True)
