from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMainWindow

from pyqtgraph.exporters.Matplotlib import Exporter
from pyqtgraph.parametertree import Parameter
from pyqtgraph.graphicsItems.PlotItem import PlotItem
from pyqtgraph import functions as fn


class QVizMatplotlibExporter(Exporter):
    """ The pyqtgraph 0.10.0 Matplotlib exporter has many issues, one of them are:
            1. When scientific notation is being used the labels any values
              do not match
            2. After closing the matplotlib window whole IMASViz closes (!).
    The issue 2 is already solved in the develop branch of the pyqtgraph
    library but it is unknown when there will be a new release.
    The issue 1 is being acknowledged but it is not yet present not even in the
    develop branch (3.10.2019: https://github.com/pyqtgraph/pyqtgraph/issues/1050#).

    To tackle those issues as general fix is needed now (modifying pyqtgraph
    source code on all HPC machines e.g. ITER HPC and GateWay is not good way
    of solving things), the patched Matplotlib Exporter was provided.

    When and if the required fixes will be released with next pyqtgraph release,
    delete all QVizMatplotlibExporter related code.
    """
    Name = "Matplotlib Window (v2)"
    windows = []

    def __init__(self, item):

        super(QVizMatplotlibExporter, self).__init__(item)

        # Set list of parameters
        self.params = Parameter(name='params', type='group', children=[
            {'name': 'Use scientific notation', 'type': 'bool', 'value': True}
        ])

    def parameters(self):
        """ In order to show parameters it is mandatory that this routine
        returns the paramaters (defined in __init__)
        """
        return self.params

    def cleanAxes(self, axl):
        if type(axl) is not list:
            axl = [axl]
        for ax in axl:
            if ax is None:
                continue
            #for loc, spine in ax.spines.iteritems():
            for loc, spine in list(ax.spines.items()):
                if loc in ['left', 'bottom']:
                    pass
                elif loc in ['right', 'top']:
                    spine.set_color('none')
                    # do not draw the spine
                else:
                    raise ValueError('Unknown spine location: %s' % loc)
                # turn off ticks when there is no spine
                ax.xaxis.set_ticks_position('bottom')

    def export(self, fileName=None):

        if isinstance(self.item, PlotItem):
            mpw = QVizMatplotlibWindow()
            QVizMatplotlibExporter.windows.append(mpw)

            stdFont = 'Arial'

            fig = mpw.getFigure()

            # Get title from the graphic item
            title = self.item.titleLabel.text

            # pyqtgraph by default uses scientific notation for large
            # values. Matplotlib values and label should reflect that too
            # (if enabled in the parameters).
            SIprefix_scale_default = 1.0 # default SI prefix scale value
            SIprefix_scale_bottom = SIprefix_scale_default
            SIprefix_scale_left = SIprefix_scale_default

            if self.params.param('Use scientific notation').value() == True:
                print("Using scientific notation (pyqtgraph default).")
                if self.item.axes['bottom']['item'].autoSIPrefix == True:
                    SIprefix_scale_bottom = self.item.axes['bottom']['item'].autoSIPrefixScale
                    xlabel = self.item.axes['bottom']['item'].label.toPlainText()
                if self.item.axes['left']['item'].autoSIPrefix == True:
                    SIprefix_scale_left = self.item.axes['left']['item'].autoSIPrefixScale
                    ylabel = self.item.axes['left']['item'].label.toPlainText()
            else:
                # labelText holds the label without scientific notation string
                # (if present) while toPlainText() gets label+scientific
                # notation string
                xlabel = self.item.axes['bottom']['item'].labelText
                ylabel = self.item.axes['left']['item'].labelText

            ax = fig.add_subplot(111, title=title)
            ax.clear()
            self.cleanAxes(ax)
            # ax.grid(True)
            for item in self.item.curves:
                x, y = item.getData()

                # pyqtgraph by default uses scientific notation for large
                # values. Matplotlib values and label should reflect that too
                # (if enabled in parameters).
                if SIprefix_scale_bottom != SIprefix_scale_default:
                    x = x * SIprefix_scale_bottom
                if SIprefix_scale_left != SIprefix_scale_default:
                    y = y * SIprefix_scale_left

                opts = item.opts
                pen = fn.mkPen(opts['pen'])
                if pen.style() == Qt.NoPen:
                    linestyle = ''
                else:
                    linestyle = '-'
                color = tuple([c/255. for c in fn.colorTuple(pen.color())])
                symbol = opts['symbol']
                if symbol == 't':
                    symbol = '^'
                symbolPen = fn.mkPen(opts['symbolPen'])
                symbolBrush = fn.mkBrush(opts['symbolBrush'])
                markeredgecolor = tuple(
                    [c/255. for c in fn.colorTuple(symbolPen.color())])
                markerfacecolor = tuple(
                    [c/255. for c in fn.colorTuple(symbolBrush.color())])
                markersize = opts['symbolSize']

                if opts['fillLevel'] is not None and opts['fillBrush'] is not None:
                    fillBrush = fn.mkBrush(opts['fillBrush'])
                    fillcolor = tuple(
                        [c/255. for c in fn.colorTuple(fillBrush.color())])
                    ax.fill_between(x=x, y1=y, y2=opts['fillLevel'],
                                    facecolor=fillcolor)

                pl = ax.plot(x, y, marker=symbol, color=color,
                             linewidth=pen.width(),
                             linestyle=linestyle,
                             markeredgecolor=markeredgecolor,
                             markerfacecolor=markerfacecolor,
                             markersize=markersize)
                xr, yr = self.item.viewRange()

                # pyqtgraph by default uses scientific notation for large
                # values. Matplotlib values and label should reflect that too
                # (if enabled in parameters).
                if SIprefix_scale_bottom != SIprefix_scale_default:
                    xr = [a*SIprefix_scale_bottom for a in xr]
                if SIprefix_scale_left != SIprefix_scale_default:
                    yr = [a*SIprefix_scale_left for a in yr]

                ax.set_xbound(*xr)
                ax.set_ybound(*yr)
            ax.set_xlabel(xlabel)  # place the labels.
            ax.set_ylabel(ylabel)
            mpw.draw()
        else:
            raise Exception("Matplotlib export currently only works with plot items")


QVizMatplotlibExporter.register()


class QVizMatplotlibWindow(QMainWindow):
    """Intended for QVizMatplotlibExporter.
    """
    def __init__(self):
        from pyqtgraph.widgets import MatplotlibWidget
        QMainWindow.__init__(self)
        self.mpl = MatplotlibWidget.MatplotlibWidget()
        self.setCentralWidget(self.mpl)
        self.show()

    def __getattr__(self, attr):
        return getattr(self.mpl, attr)

    def closeEvent(self, ev):
        QVizMatplotlibExporter.windows.remove(self)
        self.deleteLater()
