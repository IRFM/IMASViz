
from imasviz.gui_commands.plot_commands.PlotSignal import PlotSignal
from imasviz.gui_commands.plot_commands.PlotSelectedSignals import PlotSelectedSignals
from imasviz.plotframes.IMASVIZMultiPlotFrame import IMASVIZMultiPlotFrame
from imasviz.util.GlobalOperations import GlobalOperations
import matplotlib.pyplot as plt
import wxmplot
import wx
import traceback
import sys


class PlotSelectedSignalsWithWxmplot(PlotSelectedSignals):
    def __init__(self, view, selectedsignals, numfig=0, update=0):
        PlotSelectedSignals.__init__(self, view, selectedsignals, numfig=0, update=0)

    def getFrame(self, numfig, rows=1, cols=1):
        api = self.view.imas_viz_api
        if numfig in api.figureframes:
            frame = api.figureframes[numfig]
        else:
            frame = IMASVIZMultiPlotFrame(view=self.view,rows=rows, cols=cols, panelsize=(400, 300))
            frame .SetTitle(title='Figure ' + str(numfig + 1))
            frame.panel.toggle_legend(None, True)
            api.figureframes[numfig] = frame
        return frame

    # Plot the set of 1D signals selected by the user as a function of time
    def plot1DSelectedSignals(self, numfig=0, update=0):

        try:
            selectedsignals = self.view.selectedSignals

            selectedsignalsList = GlobalOperations.getListFromDict(selectedsignals)
            selectedsignalsList.sort(key=lambda x: x[2])


            api = self.view.imas_viz_api
            fig = self.getFigure(numfig)
            fig.add_subplot(111)

            rows = 2
            cols = 3

            frame = self.getFrame(numfig, rows, cols)

            def lambda_f(evt, i=numfig, api=api):
                self.onHide(api, i)

            frame.Bind(wx.EVT_CLOSE, lambda_f)

            n = 0 #number of plots

            maxNumberOfPlots = rows*cols;

            #self.view.imas_viz_api.multiPlotsFrames[self.framesKey] = []

            #self.view.imas_viz_api.multiPlotsFrames[self.framesKey].append(frame)
            if frame not in self.view.imas_viz_api.multiPlotsFrames:
                self.view.imas_viz_api.multiPlotsFrames.append(frame)

            for tupleElement in selectedsignalsList:

                if n + 1 > maxNumberOfPlots:
                    break

                signalNodeData = tupleElement[1]

                key = self.view.dataSource.dataKey(signalNodeData)
                tup = (self.view.dataSource.shotNumber, signalNodeData)
                api.addNodeToFigure(numfig, key, tup)

                s = PlotSignal.getSignal(self.view, signalNodeData)
                t = PlotSignal.getTime(s)

                v = PlotSignal.get1DSignalValue(s)

                shotNumber = tupleElement[0]

                nbRows = v.shape[0]

                label, xlabel, ylabel, title = PlotSignal.plotOptions(self.view, signalNodeData, shotNumber)


                for j in range(0, nbRows):
                    u = v[j]
                    ti = t[0]
                    #print signalNodeData['Path']
                    a = n//cols
                    b = n - (n//cols)*cols
                    frame.plot(ti, u, panel=(a, b), xlabel=xlabel, ylabel=ylabel, label=label, labelfontsize=5, show_legend=True, legend_loc='uc', legendfontsize=5, legend_on=False)
                    n = n + 1

                frame.Center()
                frame.Show()

        except:
            traceback.print_exc(file=sys.stdout)
            raise ValueError("Error while plotting 1D selected signal(s).")

