from ivviewer import Viewer
from epcore.elements import MeasurementSettings


class IVViewerParametersAdjuster:
    def __init__(self, viewer: Viewer):
        self._viewer = viewer

        # Dictionary? TODO: universal parameters adjuster
        self._volt_min_borders = {  # Voltage [V] -> Minimum border [V]
            1.2: 0.4,
            3.3: 1.0,
            5.0: 1.5,
            12.0: 4.0
        }

        # TODO: mA?
        self._curr_min_borders = {  # Resistance [Omh] -> Minimum border [mA]
            47500.0: 0.05,
            4750.0: 0.5,
            475.0: 5.0
        }
        # Dictionary? TODO: universal parameters adjuster
        self._scale_adjuster = {  # _scale_adjuster[V][Omh] -> Scale for x,y
            1.2: {
                47500.0: (1.5, 0.04),
                4750.0: (1.5, 0.4),
                475.0: (1.5, 4.0)
            },
            3.3: {
                47500.0: (4.0, 0.15),
                4750.0: (4.0, 1.0),
                475.0: (4.0, 10.0)
            },
            5.0: {
                47500.0: (6.0, 0.18),
                4750.0: (6.0, 1.5),
                475.0: (6.0, 15.0)
            },
            12.0: {
                47500.0: (14.0, 0.35),
                4750.0: (14.0, 2.8),
                475.0: (14.0, 28.0)
            }
        }

    def adjust_parameters(self, settings: MeasurementSettings):
        self._viewer.plot.set_scale(*self._scale_adjuster[settings.max_voltage][settings.internal_resistance])
        self._viewer.plot.set_min_borders(self._volt_min_borders[settings.max_voltage],
                                          self._curr_min_borders[settings.internal_resistance])
