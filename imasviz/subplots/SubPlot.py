import numpy as np

class SubPlot:
    def __init__(self, x, y, subplot_number, scatter=False, title=None, legend="test",
                 labelY="s(t)", labelX="t[s]",
                 xmin=None, xmax=None, ymin=None, ymax=None):

        self.subplot_number = subplot_number
        self.x = x
        self.y = y
        self.labelX = labelX
        self.labelY = labelY
        self.legend = legend
        self.legend_handle = None

        if xmin is not None:
            self.xmin = xmin
        else:
            self.xmin = np.amin(x)
        if xmax is not None:
            self.xmax = xmax
        else:
            self.xmax = np.amax(x)
        if ymin is not None:
            self.ymin = ymin
        else:
            self.ymin = np.amin(y)
        if ymax is not None:
            self.ymax = ymax
        else:
            self.ymax = np.amax(y)
        self.scatter = scatter
        self.title = title

    def setLegendHandle(self, legend_handle):
        self.legend_handle = legend_handle