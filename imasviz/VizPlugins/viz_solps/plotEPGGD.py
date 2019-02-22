#! /usr/bin/env python3

import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, \
                            QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, \
                            QSpacerItem, QSizePolicy, QPushButton, QDialog, \
                            QFormLayout, QDialogButtonBox, QComboBox
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import QSize, pyqtSlot

import logging
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import matplotlib.collections

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import numpy as np

from getEPGGD import getEPGGD, GetGGDVars

class plotEPGGD(QWidget):

    """Plot edge_profiles (EP) IDS GGD.
    """
    def __init__(self, parent=None, ids=None, *args, **kwargs):
        QWidget.__init__(self, parent)

        # Check if display is available (display is mandatory, as this is
        # PyQt5 widget)
        self.checkDisplay()
        # Set parent
        self.parent = parent

        self.gridSubsetDict = {}

        self.gs_id = 0
        self.qLabel = ''
        self.qValues = 0

        self.quantityValuesDict = {}

        self.ggdVars = {}
        for i in range(GetGGDVars.numOfParams):
            # At the begining clear all parameters
            self.ggdVars[i] = ''

        # Check if the widget is run from IMASViz or as standalone
        try:
            # Check if the correct DTV (from IMASViz) is available
            self.dataTreeView = self.parent.parent.parent
            if self.dataTreeView.objectName() == 'DTV':
                self.usingIMASViz = True
        except:
            self.usingIMASViz = False
            self.dataTreeView = None

        # Set IDS object
        self.ids = ids
        # Set layout
        self.setLayout(QVBoxLayout())
        # Set empty matplotlib canvas
        self.canvas = PlotCanvas(self, width=1, height=6)
        # Set matplotlib toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        # Add widgets to layout
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.toolbar)

    @pyqtSlot( )
    def checkDisplay(self):
        try:
            os.environ['DISPLAY']
        except:
            logging.error('No display available!')

    @pyqtSlot()
    def setEPIDS(self):
        """Set and read edge_profiles IDS.
        Check if either:
        1. IDS object was already provided.
        2. The plugin was run from IMASViz (checks for DTV). In this case the
           IDS parameters are taken from IMASViz DataTreeView and the
           corresponding IDS is opened ( 'get()' ) and IDS object is created
        3. If neither condition from the above is satisfied, run the plugin in
           standalone mode using Dialog for IDS parameters specification.
        """
        self.vars = {}
        # If IDS object is not provided, display dialog window where the IDS
        # parameters can be specified. Then open the specified IDS
        if self.ids != None:
            return
        elif self.usingIMASViz == True:
            self.getIDSfromIMASViz()
        else:
            from getIDS import GetIDSWrapper, GetIDSDialog, GetIDSVars
            for i in range(GetIDSVars.numOfParams):
                # At the beginning clear all parameters
                self.vars[i] = ''

            dialog = GetIDSDialog(self)
            dialog.prepareWidgets(self.vars)
            if dialog.exec_():
                self.vars = dialog.on_close()
            else:
                # Canceled!
                return self.ids == None
            # Set IDS with wrapper
            self.ids = GetIDSWrapper(self.vars).getIDS()

        logging.info('Getting IDS')
        # Read edge_profiles IDS
        self.ids.edge_profiles.get()

    @pyqtSlot()
    def setGGD(self):
        if self.ids == None:
            logging.warning('No IDS yet provided.')
            return False
        # Get dialog
        dialog = GetGGDDialog(self)
        # Get variable on dialog close
        dialog.prepareWidgets(self.ggdVars)
        if dialog.exec_():
            # Get GGD variables on dialog close
            self.ggdVars = dialog.on_close()
            return True
        else:
            # Canceled!
            return False

    @pyqtSlot()
    def getIDSfromIMASViz(self):
        """Get IDS object from IMASViz.
        """

        # if self.dataTreeView == None:
        #     self.dataTreeView = dictDataSource['imasviz_view']
        dataSource = self.dataTreeView.dataSource
        shot = dataSource.shotNumber
        run = dataSource.runNumber
        machine = dataSource.imasDbName
        user = dataSource.userName

        print('shot    =', shot)
        print('run     =', run)
        print('user    =', user)
        print('machine =', machine)
        print('Reading data...')

        # Open shot and run of machine
        occurrence = 0  # default occurrence
        try:
            self.ids = dataSource.ids[occurrence]
        except:
            self.ids = None
        if self.ids is None:
            dataSource.load(self.dataTreeView, IDSName='edge_profiles',
                            occurrence=0,
                            pathsList=None, async=False)
            self.ids = dataSource.ids[occurrence]

        if not self.dataTreeView.idsAlreadyFetched["edge_profiles"]:
            self.ids.edge_profiles.get()

    @pyqtSlot()
    def getQuantityValues(self):
        return self.ggdVars['quantityValues']

    @pyqtSlot()
    def getQuantityLabel(self):
        return self.ggdVars['quantityLabel']

    @pyqtSlot()
    def getGridSubsetID(self):
        return self.ggdVars['gridSubsetId']

    @pyqtSlot()
    def getGGDVars(self):
        return self.ggdVars

    @pyqtSlot()
    def plotData(self):
        """Populate (plot) the canvas.
        """
        if self.ids == None:
            return

        # Clear canvas figure if it already exists (to avoid plot overlapping)
        if self.canvas.figure != None:
            self.canvas.figure.clear()

        # Set edge_profiles objectž
        self.ep = self.ids.edge_profiles
        # Get GGD variables
        ggdVars = self.getGGDVars()
        # Extract array of quantity values
        qValues = ggdVars['quantityValues']
        # Set getGGD object
        getGGD = getEPGGD(self.ep)
        # Get array of nodes coordinates, quad connectivity array and array of
        # quantity values (corresponding to the specified grid subset)
        nodes, quad_conn_array = getGGD.getGSGridGeometry(ggdVars)
        # Plot canvas with the data
        self.canvas.plotData(nodes, quad_conn_array, qValues,
                             title=ggdVars['quantityLabel'])

    @pyqtSlot()
    def clearPlot(self):
        """Clear canvas plot.
        """

        self.canvas.figure.clear()

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):

        self.parent = parent

        self.figure = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.figure)

        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    @pyqtSlot()
    def plotData(self, nodes, quad_conn_array, qValues, title='Plot'):
        """Plots edge data to 2D VTK.
        """

        self.title = title

        if len(nodes) < 1:
            logging.warning('Array of nodes coordinates is empty!')
            return

        if len(quad_conn_array) < 1:
            logging.warning('Quad connectivity array is empty!')
            return

        if len(qValues) < 1:
            logging.warning('Array of quantity values is empty!')
            return

        self.showMeshPlot(nodes, quad_conn_array, qValues)

    def showMeshPlot(self, nodes, elements, values):
        """Arrange the nodes, elements and values as needed and plot them to
        matplotlib canvas as PolyCollection.

        Arguments:
            nodes (2D array)    : Array of node/point coordinates
            elements (4D array) : Connectivity array for quad elements
            values (1D array)   : Quantities corresponding to the quad elements
        """

        y = nodes[:,0]
        z = nodes[:,1]

        def quatplot(y,z, quatrangles, values, ax=None, **kwargs):

            if not ax: ax=plt.gca()
            yz = np.c_[y,z]
            verts= yz[quatrangles]
            white = (1,1,1,1)
            pc = matplotlib.collections.PolyCollection(verts,
                                                       edgecolor=white,
                                                       linewidths=(0.1,),
                                                       **kwargs)
            pc.set_array(values)
            ax.add_collection(pc)
            ax.autoscale()
            return pc

        self.ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(right=0.85)
        self.ax.set_aspect('equal')

        pc = quatplot(y,z, np.asarray(elements), values, ax=self.ax,
                      cmap="plasma")
        self.figure.colorbar(pc, ax=self.ax)
        # self.ax.plot(y,z, marker="o", ls="", color="crimson")
        self.ax.plot(y,z, ls="", color="crimson")
        # Set background
        self.ax.set_facecolor((0.75, 0.75, 0.75))

        self.ax.set(title=self.title, xlabel='R[m] ', ylabel='Z[m]')

        self.draw()

class GetGGDDialog(QDialog):
    """Dialog Demanding the grid_ggd and ggd slice together with grid
    subset and quantity (for edge_profiles IDS).
    """

    def __init__(self, parent=None):
        super(GetGGDDialog, self).__init__(parent)

        # Set IDS object (from parent)
        self.ids = parent.ids

        if self.ids == None:
            return
        # Set empty dictionaries
        self.gridSubsetDict = {}
        self.quantityDict = {}
        # Set edge_profiles object
        self.ep = self.ids.edge_profiles
        self.getGGD = getEPGGD(self.ep)

        # Get GGD properties
        # - Number of GGD slices
        self.nGGDSlices = len(self.ep.ggd)
        # - Number of GGD grid slices
        self.nGridGGDSlices = len(self.ep.grid_ggd)

    def prepareWidgets(self, parameters, title='Set GGD Variables'):
        """Set dialog widgets (line edit etc.).

        Arguments:
            title (str) : Dialog title.

        """
        self.setModal(True)
        # Set window title
        self.setWindowTitle(title)
        # Set layout
        formLayout = QFormLayout(self)

        # Set line edit for grid_ggd slice
        self.g1_LineEdit = QLineEdit()
        self.g1_LineEdit.setText(GetGGDVars.names[0])
        self.g1_LineEdit.setText(str(GetGGDVars.defaultValues['gridGGDSlice']))
        self.g1_LineEdit.setValidator(QIntValidator())
        formLayout.addRow(GetGGDVars.names[0], self.g1_LineEdit)

        # Set line edit for ggd slice
        self.g2_LineEdit = QLineEdit()
        self.g2_LineEdit.setText(GetGGDVars.names[1])
        self.g2_LineEdit.setText(str(GetGGDVars.defaultValues['GGDSlice']))
        self.g2_LineEdit.setValidator(QIntValidator())
        formLayout.addRow(GetGGDVars.names[1], self.g2_LineEdit)

        # Set combo boxes
        self.combobox_gridSubset = QComboBox()
        self.combobox_quantity = QComboBox()

        self.populateComboBoxGS()
        self.populateComboBoxQ()

        self.g1_LineEdit.textChanged.connect(self.populateComboBoxGS)

        self.combobox_gridSubset.currentTextChanged.connect(
            self.populateComboBoxQ)

        formLayout.addRow('Grid Subset', self.combobox_gridSubset)
        formLayout.addRow('Grid Subset Quantity', self.combobox_quantity)

        # Adding the Ok and Cancel button.
        dialog_button_box = QDialogButtonBox()
        dialog_button_box.setStandardButtons(QDialogButtonBox.Ok |
                                             QDialogButtonBox.Cancel)
        dialog_button_box.accepted.connect(self.accept)
        dialog_button_box.rejected.connect(self.reject)
        formLayout.addRow(dialog_button_box)

    def populateComboBoxGS(self):
        """Populate grid subset combobox with choices
        corresponding to set grid_ggd and ggd indices.
        """

        self.combobox_gridSubset.clear()

        if self.g1_LineEdit.text().isdigit() != True:
            return

        gg = int(self.g1_LineEdit.text())

        # Get number of GGD grid subsets
        try:
            self.nGridSubsets = self.getGGD.getNGridSubset(gg)
        except:
            logging.error('The specified IDS does not contain any grid '
                          'subsets! Aborting.')
            return

        for i in range(self.nGridSubsets):
            # Only 2D grid subsets supported for now (first object dimension
            # parameter = 3 (fortan notation, 2D -> 2+1 = 3)
            if self.getGGD.getGridSubsetDim(gridId=gg, gsId=i) == 3:
                gs_name = self.getGGD.getGridSubsetName(gridId=gg, gsId=i)
                self.combobox_gridSubset.addItem(gs_name)
                self.gridSubsetDict[gs_name] = i + 1 # Fortran notation in IDS

    def populateComboBoxQ(self):
        """Populate grid subset combobox with choices
        corresponding to set grid_ggd and ggd indices and grid subset.
        """

        self.combobox_quantity.clear()

        if self.g1_LineEdit.text().isdigit() != True:
            return

        if self.g2_LineEdit.text().isdigit() != True:
            return

        gg = int(self.g1_LineEdit.text())
        g = int(self.g2_LineEdit.text())
        gs_name = self.combobox_gridSubset.currentText()
        gs_id = self.gridSubsetDict[gs_name]

        ggd = self.ep.ggd[g]

        self.quantityDict = \
            self.getGGD.getQuantityDict(ggd=ggd, gridSubsetId=gs_id)

        for qLabel in self.quantityDict:
            self.combobox_quantity.addItem(qLabel)

    def on_close(self):
        # Returning a dictionary of values. The values are defined in
        # enumerator class GetGGDVars.

        variables = {}

        variables['gridGGDSlice'] = self.g1_LineEdit.text()
        variables['GGDSlice'] = self.g2_LineEdit.text()
        variables['gridSubsetId'] = self.gridSubsetDict[self.combobox_gridSubset.currentText()]
        variables['quantityLabel'] = self.combobox_quantity.currentText()
        variables['quantityValues'] = self.quantityDict[variables[
            'quantityLabel']]['values']

        # Checking if validating Integers.
        try:
            variables['gridGGDSlice'] = int(variables['gridGGDSlice'])
            variables['GGDSlice'] = int(variables['GGDSlice'])
            variables['gridSubsetId'] = int(variables['gridSubsetId'])
        except ValueError as e:

            variables['gridGGDSlice'] = -1
            variables['GGDSlice'] = -1
            variables['gridSubsetId'] = -1

        return variables

if __name__ == '__main__':
    import getopt

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    root.addHandler(ch)

    app = QApplication(sys.argv)

    mainWindow = QMainWindow()

    # If any IDS parameters are given as an argument (via terminal), open the
    # specified IDS. Otherwise, open dialog where the parameters can be set
    if len(sys.argv) > 1:
        # Set IDS object, open it and provide it as an argument to plotEPGGD
        # Vars = {0: 122264, 1: 1, 2: 'penkod', 3: 'iter', 4: '3'}

        # For launching python script directly from terminal with python command
        Vars = {}
        Help = """
                This is used for testing the plotting data from an edge_profilesIDS.

                In order to run this plugin, shot, run, user, device and version must
                be defined. Example (terminal):

                python3 solpswidget.py --shot=122264 --run=1 --user=penkod \
                --device=iter --version=3

                """
        try:
            opts, args = getopt.getopt(sys.argv[1:], "srudvh", ["shot=",
                                                                "run=",
                                                                "user=",
                                                                "device=",
                                                                "version=",
                                                                "help"])

            for opt, arg in opts:
                # print opt, arg
                if opt in ("-s", "--shot"):
                    Vars[GetIDSVars.shot] = int(arg)
                elif opt in ("-r", "--run"):
                    Vars[GetIDSVars.run] = int(arg)
                elif opt in ("-u", "--user"):
                    Vars[GetIDSVars.user] = arg
                elif opt in ("-t", "--device"):
                    Vars[GetIDSVars.device] = arg
                elif opt in ("-v", "--version"):
                    Vars[GetIDSVars.version] = arg
                if opt in ("-h", "--help"):
                    print(Help % (os.environ['USER'], os.path.expanduser('~')))
                    sys.exit()

            ids = GetIDSWrapper(Vars).getIDS()
            plotWidget = plotEPGGD(ids)

        except Exception:
            print('Supplied option not recognized!')
            print('For help: -h / --help')
            # sys.exit(2)
            print('Switching to dialog window')
            plotWidget = plotEPGGD()


        if len(Vars) < GetIDSVars.numOfParams:
            print('Not enough variables defined!')
            print('For help: -h / --help')
            # sys.exit(2)
            print('Switching to dialog window')
            plotWidget = plotEPGGD()
        elif len(Vars) > GetIDSVars.numOfParams:
            print('Too many variables defined!')
            print('For help: -h / --help')
            # sys.exit(2)
            print('Switching to dialog window')
            plotWidget = plotEPGGD()

    else:
        # Open IDS (specify parameters using dialog)
        plotWidget = plotEPGGD()

    plotWidget.setEPIDS()
    plotWidget.setGGD()

    plotWidget.plotData()

    title = 'Test: Plot edge_profiles GGD'

    mainWindow.setWindowTitle(title)

    widget =  QWidget(mainWindow)
    mainWindow.setCentralWidget(plotWidget)
    mainWindow.show()

    sys.exit(app.exec_())