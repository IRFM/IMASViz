from wxmplot import PlotPanel
import wx
from imasviz.view.Coord1Slider import Coord1Slider
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from wxmplot.plotpanel import wxCursor
from matplotlib.ticker import FuncFormatter


class IMASVIZPlotPanel(PlotPanel):
    def __init__(self, parent=None, size=None, axisbg=None, title=None,
                 signalHandling=None, **kws):
        if title is None:
            title = '2D Plot Frame'

        self.axisbg = axisbg
        self.signalHandling = signalHandling
        self.staticSliderLabelValue = ''

        PlotPanel.__init__(self, parent=parent, size=size,  axisbg=axisbg,
                           **kws)


    def __onPickEvent(self, event=None):
        """pick events"""
        legline = event.artist
        trace = self.conf.legend_map.get(legline, None)
        visible = True
        if trace is not None and self.conf.hidewith_legend:
            line, legline, legtext = trace
            visible = not line.get_visible()
            line.set_visible(visible)
            if visible:
                legline.set_zorder(10.00)
                legline.set_alpha(1.00)
                legtext.set_zorder(10.00)
                legtext.set_alpha(1.00)
            else:
                legline.set_alpha(0.50)
                legtext.set_alpha(0.50)

    def BuildPanel(self):
        """ Builds basic GUI panel and popup menu"""
        self.fig   = Figure(self.figsize, dpi=self.dpi)
        # 1 axes for now
        self.gridspec = GridSpec(1,1)
        self.axes  = self.fig.add_subplot(self.gridspec[0], axisbg=self.axisbg)

        self.canvas = FigureCanvas(self, -1, self.fig)

        self.printer.canvas = self.canvas
        self.set_bg()
        self.conf.canvas = self.canvas
        self.canvas.SetCursor(wxCursor(wx.CURSOR_CROSS))
        self.canvas.mpl_connect("pick_event", self.__onPickEvent)

        # overwrite ScalarFormatter from ticker.py here:
        self.axes.xaxis.set_major_formatter(FuncFormatter(self.xformatter))
        self.axes.yaxis.set_major_formatter(FuncFormatter(self.yformatter))

        # This way of adding to sizer allows resizing
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 2, wx.LEFT|wx.TOP|wx.BOTTOM|wx.EXPAND, 0)

        self.conf.show_legend = True

        self.addSlider(sizer)
        self.SetAutoLayout(True)
        self.autoset_margins()
        self.SetSizer(sizer)
        self.Fit()

        canvas_draw = self.canvas.draw
        def draw(*args, **kws):
            self.autoset_margins()
            canvas_draw(*args, **kws)
        self.canvas.draw = draw
        self.addCanvasEvents()

    def addSlider(self, sizer):

        self.staticSliderLabel = None
        # if self.signalHandling.timeSlider == True:
        #     self.staticSliderLabelValue = \
        #         'Time slider (' + self.signalHandling.nodeData['dataName'] + '):'
        # elif self.signalHandling.timeSlider == False:
        #     self.staticSliderLabelValue = \
        #         'Coordinate slider (' + self.signalHandling.nodeData['dataName'] + '):'

        if self.signalHandling.timeSlider == True:
            self.staticSliderLabelValue = 'Time slider:'
        elif self.signalHandling.timeSlider == False:
            self.staticSliderLabelValue = 'Coordinate slider:'

        self.staticSliderLabel = wx.StaticText(self, -1, self.staticSliderLabelValue)
        sizer.Add(self.staticSliderLabel, 0, wx.LEFT, 10)

        treeNode = \
            self.signalHandling.view.getNodeAttributes(
                self.signalHandling.nodeData['dataName'])

        if self.signalHandling.timeSlider == True:
            minValue = 0
            maxValue = int(treeNode.timeMaxValue()) - 1
            self.slider = Coord1Slider(parent=self,
                                       signalHandling=self.signalHandling,
                                       minValue=minValue,
                                       maxValue=maxValue)
            sizer.Add(self.slider, 0, wx.LEFT | wx.EXPAND, 10)
            sizerText = wx.BoxSizer(wx.HORIZONTAL)
            self.staticValueLabel = wx.StaticText(self, -1, 'Index value: ')
            self.sliderCurrentValue = \
                wx.TextCtrl(self, -1, str(minValue), size=(150, -1))
            sizerText.Add(self.staticValueLabel, 0, wx.LEFT | wx.EXPAND, 10)
            sizerText.Add(self.sliderCurrentValue, 0, wx.LEFT | wx.EXPAND, 10)
            sizer.Add(sizerText, 0, wx.LEFT | wx.EXPAND, 10)


        elif self.signalHandling.timeSlider == False:
            minValue = 0
            maxValue = \
                treeNode.coordinate1Length(self.signalHandling.nodeData,
                                           self.signalHandling.view.dataSource.ids) - 1
            self.slider = Coord1Slider(parent=self,
                                       signalHandling=self.signalHandling,
                                       minValue=minValue,
                                       maxValue=maxValue)
            sizer.Add(self.slider, 0, wx.LEFT | wx.EXPAND, 10)
            sizerText = wx.BoxSizer(wx.HORIZONTAL)
            self.staticValueLabel = wx.StaticText(self, -1, 'Index value: ')
            self.sliderCurrentValue = wx.TextCtrl(self, -1, str(minValue), size=(150, -1))
            sizerText.Add(self.staticValueLabel, 0, wx.LEFT | wx.EXPAND, 10)
            sizerText.Add(self.sliderCurrentValue, 0, wx.LEFT | wx.EXPAND, 10)
            sizer.Add(sizerText, 0, wx.LEFT | wx.EXPAND, 10)

class IMASVIZ_PreviewPlotPanel(PlotPanel):
    """Light version of IMASVIZPlotPanel class, used for simple plots
       (for plot preview etc.)
    """
    def __init__(self, parent=None, size=None, axisbg=None, title=None,
                 signalHandling=None, **kws):
        if title is None:
            title = 'Plot Frame'

        self.axisbg = axisbg
        self.signalHandling = signalHandling
        self.staticSliderLabelValue = ''

        PlotPanel.__init__(self, parent=parent, size=size,  axisbg=axisbg,
                           **kws)
    def BuildPanel(self):
        """ Builds basic GUI panel and popup menu"""
        self.fig   = Figure(self.figsize, dpi=self.dpi)
        # 1 axes for now
        self.gridspec = GridSpec(1,1)
        self.axes  = self.fig.add_subplot(self.gridspec[0], axisbg=self.axisbg)

        self.canvas = FigureCanvas(self, -1, self.fig)

        self.printer.canvas = self.canvas
        self.set_bg()
        self.conf.canvas = self.canvas

        # This way of adding to sizer allows resizing
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 2, wx.LEFT|wx.TOP|wx.BOTTOM|wx.EXPAND, 0)

        self.conf.show_legend = False

        self.SetAutoLayout(True)
        self.autoset_margins()
        self.SetSizer(sizer)
        self.Fit()

        canvas_draw = self.canvas.draw
        def draw(*args, **kws):
            self.autoset_margins()
            canvas_draw(*args, **kws)
        self.canvas.draw = draw
        # self.addCanvasEvents()
