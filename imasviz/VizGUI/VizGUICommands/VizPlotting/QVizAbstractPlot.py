
class QVizAbstractPlot:

    def __init__(self, plotWidget):
        self.plotWidget = plotWidget

    def updateSlider(self):
        if self.plotWidget.addTimeSlider or self.plotWidget.addCoordinateSlider:
            self.plotWidget.sliderGroup.setSlider()
