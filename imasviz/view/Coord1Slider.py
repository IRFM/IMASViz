import wx

class Coord1Slider(wx.Slider):
    def __init__(self, parent=None, signalHandling=None,
                 minValue=0, maxValue=None, *args, **kwargs):
        super(Coord1Slider, self).__init__(parent, *args, **kwargs)
        self.parent = parent #this is a IMASVIZPlotPanel instance
        self.SetValue(0)
        self.SetMin(minValue)
        self.SetMax(maxValue)

        self.signalHandling = signalHandling
        self.Bind(wx.EVT_SCROLL_THUMBRELEASE , self.OnSliderScrollThumbRelease)
        self.Bind(wx.EVT_SCROLL, self.OnSliderScroll)

    def OnSliderScrollThumbRelease(self, e):
        obj = e.GetEventObject()
        val = obj.GetValue()
        currentFigureKey = self.parent.parent.GetTitle() #title of the IMASVIZPlotFrame is the figure key in the dict. figureframes (attribute of Browser_API class)
        if self.signalHandling.timeSlider:
            self.signalHandling.plotSelectedSignalVsCoordAtTimeIndex(val, currentFigureKey)
        else:
            self.signalHandling.plotSelectedSignalVsTimeAtIndex(val, currentFigureKey)
        e.Skip()

    def OnSliderScroll(self, e):

        obj = e.GetEventObject()
        val = obj.GetValue()
        if self.signalHandling.timeSlider:
            self.parent.sliderCurrentValue.SetValue(str(val))
        else:
            self.parent.sliderCurrentValue.SetValue(str(val))
        e.Skip()