from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QAction


class ActionWithDisabledHotkeys(QAction):
    """
    A QAction subclass in which hotkeys are disabled. Hotkeys only appear in the menu, but do nothing.
    """

    def event(self, event: QEvent) -> bool:
        """
        Method handles events in the widget. The widget should ignore hotkeys that are defined on this widget
        :param event: event that occurred in the action widget.
        :return: True if the event was recognized and processed.
        """

        if event.type() == QEvent.Shortcut:
            return False

        return super().event(event)
