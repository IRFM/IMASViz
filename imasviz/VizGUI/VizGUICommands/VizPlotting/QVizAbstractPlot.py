
class QVizAbstractPlot:

    def __init__(self, plotWidget):
        self.plotWidget = plotWidget

    def updateSlider(self):
        if self.plotWidget.addTimeSlider:
            time_index = self.plotWidget.sliderGroup.slider.value()
            self.plotWidget.sliderGroup.setSlider()
        elif self.plotWidget.addCoordinateSlider:
            coordinate_index = self.plotWidget.sliderGroup.slider.value()
            self.plotWidget.sliderGroup.setSlider()
