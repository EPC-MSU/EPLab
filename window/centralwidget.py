from PyQt5.QtCore import QCoreApplication as qApp, Qt
from PyQt5.QtGui import QResizeEvent
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from ivviewer import Viewer
from settings import SettingsPanel


class CentralWidget(QWidget):
    """
    The central widget contains the signature display widget. Current settings are also displayed in the upper left
    corner.
    """

    def __init__(self, iv_viewer: Viewer) -> None:
        """
        :param iv_viewer: a widget that draws signatures.
        """

        super().__init__()
        self._init_ui(iv_viewer)

    @property
    def settings_panel(self) -> SettingsPanel:
        """
        :return: widget with current settings.
        """

        return self._settings_panel

    def _init_ui(self, iv_viewer: Viewer) -> None:
        """
        :param iv_viewer: a widget that draws signatures.
        """

        self._iv_viewer: Viewer = iv_viewer
        self._iv_viewer.setFocusPolicy(Qt.ClickFocus)
        self._iv_viewer.layout().setContentsMargins(0, 0, 0, 0)
        self._iv_viewer.plot.enable_context_menu()
        self._iv_viewer.plot.localize_widget(add_cursor=qApp.translate("t", "Добавить метку"),
                                             export_ivc=qApp.translate("t", "Экспортировать сигнатуры в файл"),
                                             remove_all_cursors=qApp.translate("t", "Удалить все метки"),
                                             remove_cursor=qApp.translate("t", "Удалить метку"),
                                             save_screenshot=qApp.translate("MainWindow", "Сохранить скриншот"))

        self._settings_panel: SettingsPanel = SettingsPanel(self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._iv_viewer)
        self.setLayout(layout)
        self._settings_panel.raise_()

    def adjust_plot(self, x_scale: float, y_scale: float) -> None:
        """
        :param x_scale: X axis scale;
        :param y_scale: Y axis scale.
        """

        self._iv_viewer.plot.set_scale(x_scale, y_scale)
        self._iv_viewer.plot.set_min_borders(x_scale, y_scale)

    def clear_settings_and_remove_all_cursors(self) -> None:
        self._iv_viewer.plot.remove_all_cursors()
        self._settings_panel.clear_panel()

    def clear_central_text(self) -> None:
        self._iv_viewer.plot.clear_center_text()

    def exit_state_for_adding_or_removing_cursor(self) -> None:
        self._iv_viewer.plot.set_state_adding_cursor(False)
        self._iv_viewer.plot.set_state_removing_cursor(False)

    def redraw_cursors(self) -> None:
        self._iv_viewer.plot.redraw_cursors()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        :param event: resize event.
        """

        self._settings_panel.move(0, 0)
        self._settings_panel.adjustSize()

    def set_path_to_directory(self, dir_path: str) -> None:
        """
        :param dir_path: path to the directory that will be used by default when saving a screenshot and exporting
        signatures to a file.
        """

        self._iv_viewer.plot.set_path_to_directory(dir_path)

    def set_settings(self, **kwargs) -> None:
        """
        :param kwargs: keyword arguments with all parameters that are displayed on the settings panel.
        """

        self._settings_panel.set_all_parameters(**kwargs)
        self._settings_panel.adjustSize()

    def show_disconnection_text(self) -> None:
        self._iv_viewer.plot.set_center_text(qApp.translate("t", "НЕТ ПОДКЛЮЧЕНИЯ"))
