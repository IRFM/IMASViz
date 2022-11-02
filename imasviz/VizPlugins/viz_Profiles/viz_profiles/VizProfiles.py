#  Name   : EdgeProfilesViz
#
#           Main EdgeProfilesViz code source.
#
#  Author :
#         Ludovic Fleury
#  E-mail :
#         ludovic.fleury@cea.fr
#
# ****************************************************
#     Copyright(c) 2022- L. Fleury

# Standard library imports
import logging
import sys
import inspect
from functools import partial

# Third party imports
import matplotlib
import numpy as np
import imas
from PyQt5.QtWidgets import (QWidget, QTabWidget, QApplication, QMainWindow,
                             QSlider, QLabel, QSpinBox, QCheckBox, QPushButton,
                             QLineEdit, QHBoxLayout, QVBoxLayout, QMenuBar,
                             QAction, QFrame, QScrollArea)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QDoubleValidator

from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues
from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizPlugins.viz_Profiles.viz_profiles.QVizTablePlotViewForPlugin import QVizTablePlotViewForPlugin

from imasviz.VizPlugins.viz_Profiles.viz_profiles.tabQt import QVizTab

class VizProfiles(QMainWindow):

    def __init__(self, viz_api, IDS_parameters, data_entry, dataTreeView, request):
        """
        Arguments:
            IDS_parameters (Dictionary) : Dictionary containing IDS parameters
                                          (shot, run, user, database)
            ids            (obj)        : IDS object
        """
        super(QMainWindow, self).__init__()

        # Set log parser
        self.log = logging.getLogger(__name__)
        self.log.addHandler(logging.StreamHandler())

        # Get app
        self.app = QApplication.instance()
        if self.app is None:
            # if it does not exist then a QApplication is created
            self.app = QApplication([])
        title = "'" + request.ids_related + "'" + " IDS (0D/1D data visualization"
        if request.strategy == 'COORDINATE1':
           title += " along coordinate1 axis)"
        elif request.strategy == 'TIME':
           title += " along time axis)"
        else:
            raise ValueError("Unexpected strategy")
            
        figureKey = viz_api.GetNextKeyForProfilesPlotView()
        
        self.setWindowTitle(title + ' [' + str(figureKey) +']')
        self.data_entry = data_entry
        self.ids_related = request.ids_related
        self.IDS_parameters = IDS_parameters
        self.dataTreeView = dataTreeView
        
        self.strategy = request.strategy
        self.request = request

        self.imas_viz_api = viz_api
        
        # Set initial time slice
        self.time_index = 0
        
        key = dataTreeView.dataSource.dataKey2(figureKey)
        tup = (dataTreeView.dataSource.shotNumber, None)
        viz_api.AddNodeToFigure(figureKey, key, tup)
        viz_api.figureframes[figureKey] = self

        # Set user interface of the main window
        self.setUI()

    def getLogger(self):
        return self.log
        
    def setTabs(self):
        filter_index = 0
        for str_filter_only in self.request.list_of_filters:
            #print("str_filter_only-->", str_filter_only)
            nodes_id, dtv_nodes = self.imas_viz_api.getAll1DNodes(self.ids_related, \
            self.dataTreeView, self.dataTreeView.IDSRoots[self.ids_related], None, None, errorBars=False, str_filter_only=str_filter_only)
            w = GlobalPlotWidget(plotStrategy=self.strategy)
            self.plottable_signals = self.imas_viz_api.getAllPlottable1DSignals(dtv_nodes, self.dataTreeView, w) #return tuple (node, signal)
            
            ncurves_per_page = 6
            remaining_page = 0
            if (len(self.plottable_signals) % ncurves_per_page) != 0:
                remaining_page = 1
            
            ntabs = int((len(self.plottable_signals) / ncurves_per_page)) + remaining_page
            self.tabs = []
             
            for i in range(ntabs):
                tab_name= self.request.tab_names[filter_index] +  ' (' +  str(i + 1) + '/' + str(ntabs) + ')'
                tab = QVizTab(parent=self, tab_page_name=tab_name)
                last_index = (i + 1)*ncurves_per_page
                if last_index > ntabs*ncurves_per_page:
                    last_index = ntabs*ncurves_per_page
                multiPlots = QVizTablePlotViewForPlugin(self.imas_viz_api, self.dataTreeView)
                tab.setTabUI(multiPlots=multiPlots, signals=self.plottable_signals[i*ncurves_per_page:last_index], plotWidget=w)
                self.tabs.append(tab)
                
            filter_index+=1

    def setUI(self):
        """Set user interface of the main window
        """
        self.mainWidget = QWidget(parent=self)
        self.mainWidget.setLayout(QVBoxLayout())
        self.tabWidget = QTabWidget(parent=self)

        # Add menu bar
        self.addMenuBar()

        # Set tabs
        self.setTabs()
        
        # Position widgets
        self.mainWidget.layout().addWidget(self.tabWidget)
        
        if self.strategy == 'COORDINATE1':
            
            # Set time slider
            self.label_slider_tmin = QLabel("t<sub>min</sub>", parent=self)
            self.label_slider_tmax = QLabel("t<sub>max</sub>", parent=self)
            self.slider_time = self.setTimeSlider()
        
            # Set time slice index label
            self.time_indexLabel = QLabel("Time slice index: ")
            self.time_indexLabel.setFixedWidth(120)
            # Set spinbox
            self.spinBox_timeIndex = self.setTimeSpinBox()

            # Set time value label
            self.label_timeValue = QLabel("Time value: ")
            self.label_timeValue.setFixedWidth(120)
            # Set time value line edit
            self.lineEdit_timeValue = self.setTimeValueLineEdit()

            # Set buttons
            self.plotButton = QPushButton("Plot", parent=self)
            self.plotButton.setFixedWidth(120)
            self.plotButton.clicked.connect(self.onPlotClicked)

            # Set check box
            self.checkBox_instant_label = QLabel("Refresh plot(s) automatically on time "
                                                 "index change: ")
            self.checkBox_instant_label.setFixedWidth(350)
            self.checkBox_instant = QCheckBox(parent=self)
            self.checkBox_instant.setChecked(False)

            whbox1 = QWidget(self)
            whbox1.setLayout(QHBoxLayout())
            whbox1.layout().setContentsMargins(0, 0, 0, 0)
            whbox1.layout().addWidget(self.label_slider_tmin)
            whbox1.layout().addWidget(self.slider_time)
            whbox1.layout().addWidget(self.label_slider_tmax)
            self.mainWidget.layout().addWidget(whbox1)

            whbox2 = QWidget(self)
            whbox2.setLayout(QHBoxLayout())
            whbox2.layout().setContentsMargins(0, 0, 0, 0)
            whbox2.layout().addWidget(self.time_indexLabel)
            whbox2.layout().addWidget(self.spinBox_timeIndex)
            whbox2.layout().addStretch()
            self.mainWidget.layout().addWidget(whbox2)

            whbox3 = QWidget(self)
            whbox3.setLayout(QHBoxLayout())
            whbox3.layout().setContentsMargins(0, 0, 0, 0)
            whbox3.layout().addWidget(self.label_timeValue)
            whbox3.layout().addWidget(self.lineEdit_timeValue)
            whbox3.layout().addStretch()
            self.mainWidget.layout().addWidget(whbox3)

            whbox4 = QWidget(self)
            whbox4.setLayout(QHBoxLayout())
            whbox4.layout().setContentsMargins(0, 0, 0, 0)
            whbox4.layout().addWidget(self.plotButton)
            whbox4.layout().addWidget(self.checkBox_instant_label)
            whbox4.layout().addWidget(self.checkBox_instant)
            whbox4.layout().addStretch()
            self.mainWidget.layout().addWidget(whbox4)

        self.setCentralWidget(self.mainWidget)

        # set status bar
        self.setStatusBar()
        #self.setStatusBarText_1(text="OK")

        # Set initial window size
        dh = self.app.desktop().availableGeometry().height()
        dw = self.app.desktop().availableGeometry().width()
        self.height = dh*0.8
        self.width = dw*0.65

        # Move window to the center of the screen
        self.setFixedWidth(self.width)
        # Note: for actually resizing the window the SizeHint is required.
        #       fixed dimensions are set here so that they are properly
        #       rezognized by the self.frameGeometry() command
        self.setFixedHeight(self.height)
        qtRectangle = self.frameGeometry()
        centerPoint = self.app.desktop().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

        # On tab change update the tab-containing plots
        self.tabWidget.currentChanged.connect(partial(
            self.updatePlotOfCurrentTab))
        
        #self.spinBox_timeIndex.valueChanged.connect(self.onTimeIndexChanged)

    def sizeHint(self):
        """Set initial window size.
        Note: Qt calls this routine automatically by default when creating this
              window/widget.
        """
        return QSize(self.width, self.height)

    def addMenuBar(self):
        """Create and configure the menu bar.
        """
        # Main menu bar
        # menuBar = QMenuBar(self)
        # options = menuBar.addMenu('Options')
        # Set menu bar
        # self.setMenuBar(menuBar)

    def toggleDebugMode(self, state):
        """ Toggle debug mode.
        """
        if state:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)

    def getTimeIndex(self):
        return self.time_index

    def getTimeValueForTimeIndex(self, time_index):
        """ Get time value for given time index.
        """
        if time_index < 0:
            time_index = 0
        time_profiles0 = eval("self.data_entry." + self.ids_related + "." +  self.request.slices_aos_name + "[0].time")
        time_slices_count = eval("len(self.data_entry." + self.ids_related + ".time)")
        
        if time_profiles0 == -9e+40:
            if time_slices_count > time_index:
                time_value = eval("self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + ".time[time_index]")
        else:
            time_value = eval("self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + "[time_index].time")

        #print('time_index=', time_index)
        #print('time_value=', time_value)
        return time_value

    def getCurrentTab(self):
        """Get currently selected tab.
        """
        return self.tabWidget.currentWidget()

    def updatePlotOfCurrentTab(self):
        """Update plot of current tab.
        """
        from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotSignal \
        import QVizPlotSignal
        qvizTab =  self.getCurrentTab()
        multiplots = qvizTab.layout().itemAt(0).widget() #returns a QVizTablePlotViewForPlugin
        w = GlobalPlotWidget(plotStrategy=self.strategy)
        updated_signals = self.imas_viz_api.updateAllPlottable1DSignals(qvizTab.signals, self.time_index, plotWidget=w)
        multiplots.updatePlot(updated_signals)

    def setTimeSlider(self):
        # Set time slider
        slider_time = QSlider(Qt.Horizontal, self)
        slider_time.setValue(0)
        slider_time.setMinimum(0)
        time_slices_count = eval("len(self.data_entry." + self.ids_related + ".time)")
        slider_time.setMaximum(time_slices_count-1)
        # self.slider_time.adjustSize()
        # self.slider_time.setMinimumWidth(600)
        # Set slider event handling
        self.updateTimeSliderTminTmaxLabel()
        slider_time.sliderReleased.connect(self.onSliderChange)
        return slider_time


    def updateTimeSliderTminTmaxLabel(self):
        """ Update tmin and tmax label/values.
        """
        ntimevalues = eval("len(self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + ")")
        tmin = eval("self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + "[0].time")
        tmax = eval("self.data_entry." + self.ids_related + "." + self.request.slices_aos_name + "[-1].time")

        # Check if empty time values were read
        # (-9e+40 is default value == empty)
        if tmin == -9e+40 or tmax == -9e+40:
            tmin = eval("self.data_entry." + self.ids_related + ".time[0]")
            tmax = eval("self.data_entry." + self.ids_related + ".time[-1]")
            ntimevalues = eval("len(self.data_entry." + self.ids_related + ".time)")
            
        self.label_slider_tmin.setText(f"n<sub>t</sub> = {ntimevalues}; "
                                       f"t<sub>min</sub> = {tmin:.2f}")
        self.label_slider_tmax.setText(f"t<sub>max</sub> = {tmax:.2f}")

    def setTimeSpinBox(self):
        spinBox_timeIndex = QSpinBox(parent=self)
        spinBox_timeIndex.setValue(0)
        spinBox_timeIndex.setMinimum(0)
        maxIndex = eval("len(self.data_entry." + self.ids_related + ".time) - 1")
        spinBox_timeIndex.setMaximum(maxIndex)
        spinBox_timeIndex.setFixedWidth(65)
        spinBox_timeIndex.valueChanged.connect(self.onSpinBoxChange)
        #spinBox_timeIndex.editingFinished.connect(partial(
        #    self.updatePlotOfCurrentTab, time_index=self.time_index))
        return spinBox_timeIndex

    @pyqtSlot()
    def onSpinBoxChange(self, event=None):
        # Update global time_index value (auto spinbox value update)
        #print('onSpinBoxChange')
        self.time_index = self.spinBox_timeIndex.value()
        #print('--->self.time_index =', self.time_index)
        self.lineEdit_timeValue.setText(
            f"{self.getTimeValueForTimeIndex(time_index=self.time_index)}")
        if self.time_index != self.slider_time.value():
           self.slider_time.setValue(self.time_index)
        if self.checkBox_instant.isChecked():
            # Update plots
            self.updatePlotOfCurrentTab()
       
    def onSliderChange(self, event=None):
        """ PyQt slot: on change of the slider value.
        """
        self.time_index = self.slider_time.value()
        self.lineEdit_timeValue.setText(
            f"{self.getTimeValueForTimeIndex(time_index=self.time_index)}")
        if self.time_index != self.spinBox_timeIndex.value():
            self.spinBox_timeIndex.setValue(self.time_index)
            
    def onPlotClicked(self,event=None):
        self.updatePlotOfCurrentTab()
        
    def setTimeValueLineEdit(self):
        lineEdit_timeValue = QLineEdit("", parent=self)
        self.onlyDouble = QDoubleValidator()
        lineEdit_timeValue.setValidator(self.onlyDouble)
        lineEdit_timeValue.setFixedWidth(200)
        lineEdit_timeValue.setText(
            f"{self.getTimeValueForTimeIndex(time_index=0)}")
        lineEdit_timeValue.editingFinished.connect(
            self.onTimeValueLineEditEditingFinished)

        return lineEdit_timeValue

    @pyqtSlot()
    def onTimeValueLineEditEditingFinished(self, event=None):
        """ When finished editing the time value line edit (pressing enter etc.)
        find the closest value (and its array index -> time index) based on the
        inserted value.
        """

        # A simple routine to find the nearest value (and its index) based on
        # given value
        def find_nearest(array, value):
            array = np.asarray(array)
            idx = (np.abs(array - value)).argmin()
            return array[idx], idx

        value = float(self.lineEdit_timeValue.text())

        time_values = 0
        time_profiles0 = 0
        time = None
        ntimevalues = 0
        time_profiles0 = eval("self.data_entry." + self.ids_related + "." + self.slices_aos_name + "[0].time")
        ttime = eval("self.data_entry." + self.ids_related + ".time")
        ntimevalues = len(eval("self.data_entry." + self.ids_related + "." + self.slices_aos_name))
        time_values = None
        
        if time_profiles0 == -9e+40:
            time_values = time
        else:
            time_values = [0]*ntimevalues
            for i in range(len(time_values)):
                time_values[i] = eval("self.data_entry." + self.ids_related + "."  + self.slices_aos_name + "[i].time")
                
        closest_value, index = find_nearest(time_values, value)
        self.spinBox_timeIndex.setValue(index)
        if self.checkBox_instant.isChecked():
           self.updatePlotOfCurrentTab()

    def setStatusBar(self):
        self.statusBar_text_1 = QLabel("")
        self.statusBar_text_1.setStyleSheet('border: 0; color:  green;')
        self.setStatusBarTexts()
        VertLine = QFrame(self)
        VertLine.setFrameShape(VertLine.VLine | VertLine.Sunken)
        self.statusBar().addPermanentWidget(VertLine)
        self.statusBar().addPermanentWidget(self.statusBar_text_1)
        self.statusBar().show()

    def setStatusBarTexts(self, text=" "):

        self.statusBar().showMessage(f"USER={self.IDS_parameters['user']}; "
                                     f"DATABASE={self.IDS_parameters['database']}; "
                                     f"SHOT={self.IDS_parameters['shot']}; "
                                     f"RUN={self.IDS_parameters['run']} ")
        self.statusBar_text_1.setText(text)

        # self.status_text.repaint()
        # self.statusBar().show()

    # def setStatusBarText_1(self, text="", color="green"):
        # self.statusBar_text_1.setText(text)
        # self.statusBar_text_1.setStyleSheet(f'border: 0; color:  {color};')


def checkArguments():
    """ Check arguments when running plugin from the terminal (standalone).
    """

    if (len(sys.argv) > 1):
        import argparse
        from argparse import RawTextHelpFormatter
        description = """Edge profiles plugin. Example for running it from terminal:
>> python EdgeProfiles.py --shot=55650 --run=0 --user=imas_public --database=west
"""

        parser = argparse.ArgumentParser(description=description,
                                         formatter_class=RawTextHelpFormatter)

        parser.add_argument("-s", "--shot", type=int, required=True,
                            help="parameter: shot")
        parser.add_argument("-r", "--run", type=int, required=True,
                            help="parameter: run")
        parser.add_argument("-u", "--user", type=str, required=True,
                            help="parameter: username")
        parser.add_argument("-d", "--database", type=str, required=True,
                            help="parameter: database")

        args = parser.parse_args()
        IDS_parameters = {"shot": args.shot,
                          "run": args.run,
                          "user": args.user,
                          "database": args.database}
    else:
        # Default parameters
        print("Using default parameters")
        IDS_parameters = {"shot": 55650,
                          "run": 0,
                          "user": "imas_public",
                          "database": "west"}

    return IDS_parameters

class GlobalPlotWidget():
    
    def __init__(self, plotStrategy):
        super(GlobalPlotWidget, self).__init__()
        self.addTimeSlider = True
        self.addCoordinateSlider = False
        self.plotStrategy = plotStrategy
        self.sliderGroup = None
        
    def getStrategy(self):
        return self.plotStrategy
        
class Request():
    def __init__(self, ids_related, tab_names, list_of_filters, slices_aos_name, strategy):
        super(Request, self).__init__()
        self.ids_related = ids_related
        self.list_of_filters = list_of_filters
        self.tab_names = tab_names
        self.slices_aos_name = slices_aos_name
        self.strategy = strategy
        
        

if __name__ == "__main__":
    # Set mandatory arguments
    IDS_parameters = checkArguments()

    # Set object managing the PyQt GUI application's control flow and main
    # settings
    app = QApplication(sys.argv)

    # Check if necessary system variables are set
    QVizGlobalOperations.checkEnvSettings()

    # Set Application Program Interface
    api = Viz_API()

    # Set data source retriever/factory
    dataSourceFactory = QVizDataSourceFactory()

    #ok, shotNumber, runNumber, userName, database = QVizGlobalOperations.askForShot()

    # ~ if not ok:
        # ~ print("User input has failed. Example1 not executed.")
    # ~ else:
        # ~ # Load IMAS database
        # ~ dataSource = dataSourceFactory.create(
                                     # ~ dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                     # ~ shotNumber=shotNumber,
                                     # ~ runNumber=runNumber,
                                     # ~ userName=userName,
                                     # ~ imasDbName=database)

    shotNumber = 55650
    runNumber = 0
    userName = 'imas_public'
    database = 'west'
    occurrence = 0
    
    dataSource = dataSourceFactory.create(
                                 dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                 shotNumber=shotNumber,
                                 runNumber=runNumber,
                                 userName=userName,
                                 imasDbName=database)

    # Build the data tree view frame
    f = api.CreateDataTree(dataSource)
   
    
    # ids_name = 'equilibrium'
    # strategy = 'TIME'
    # slices_aos_name = 'time_slice'
    # list_of_filters = ['time_slice(0)']
    # tab_names = ['time_slice']
    
    ids_name = 'core_profiles'
    #strategy = 'COORDINATE1'
    strategy = 'TIME'
    slices_aos_name = 'profiles_1d'
    list_of_filters = ['profiles_1d(0)/grid', 'profiles_1d(0)/electrons', 'profiles_1d(0)/ions(0)', 'global_quantities']
    tab_names = ['profiles_1d/grid', 'profiles_1d/electrons', 'profiles_1d/ions', 'global_quantities']
    
    # ids_name = 'magnetics'
    # strategy = 'TIME'
    # slices_aos_name = 'flux_loop'
    # list_of_filters = ['flux_loop']
    # tab_names = ['flux_loop']
    
    api.LoadIDSData(f, ids_name, occurrence)
    #f.show()
    data_entry = dataSource.getImasEntry(occurrence)
   
    
    request = Request(ids_name, tab_names, list_of_filters, slices_aos_name, strategy)
    vep = VizProfiles(api, IDS_parameters, data_entry, f.dataTreeView, request)
    vep.show()
    sys.exit(app.exec_())
