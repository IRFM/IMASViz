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

        self.grid_ggd_slice = 0
        self.ggd_slice = 0
        self.gridSubset_id = 0
        self.gridSubsetDict = {}
        self.num_gridSubsets = 0
        self.num_ggd_slices = 0
        self.num_grid_ggd_slices = 0

        self.gs_id = 0
        self.qLabel = ''
        self.qValues = 0

        self.quantityDict = {}

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
        # Set empty matplotliv canvas
        self.canvas = PlotCanvas(self, width=5, height=4)
        # Set matplotlib toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        # Add widgets to layout
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.toolbar)
        # Resize widget
        self.resize(200,200)

    @pyqtSlot( )
    def checkDisplay(self):
        try:
            os.environ['DISPLAY']
        except:
            logging.error('No display available!')

    @pyqtSlot()
    def checkIDS(self):
        """Check if either:
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
            from getIDS import GetIDSWrapper, GetDialog, GetIDSVars
            for i in range(GetIDSVars.numOfParams):
                # At the beginning clear all parameters
                self.vars[i] = ''

            dialog = GetDialog(self)
            dialog.prepareWidgets(self.vars)
            if dialog.exec_():
                self.vars = dialog.on_close()
            else:
                # Canceled!
                return self.ids == None

            self.ids = GetIDSWrapper(self.vars).getIDS()

        logging.info('Getting IDS')
        self.ids.edge_profiles.get()

    @pyqtSlot()
    def setGGD(self):
        if self.ids == None:
            logging.warning('No IDS yet provided.')
            return False
        dialog = GetGGDDialog(self)
        dialog.prepareWidgets(self.ggdVars)
        if dialog.exec_():
            self.ggdVars, self.gs_id, self.qLabel, self.qValues = \
                dialog.on_close()
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
        return self.qValues

    @pyqtSlot()
    def getQuantityLabel(self):
        return self.qLabel

    @pyqtSlot()
    def getGridSubsetID(self):
        return self.gs_id

    @pyqtSlot()
    def getGGDVars(self):
        return self.ggdVars

    @pyqtSlot()
    def plotData(self):
        """Populate (plot) the canvas.
        """
        self.canvas.plotData()

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):

        self.parent = parent

        self.figure = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.figure)

        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    @pyqtSlot()
    def plotData(self):
        """Plots edge data to 2D VTK.
        """

        self.ids = self.parent.ids
        if self.ids == None:
            return

        self.ep = self.ids.edge_profiles

        ggdVars = self.parent.getGGDVars()
        # TODO: Contains all possible arrays and values. Set that only the
        # one required is passed
        qValues = self.parent.getQuantityValues()
        qLabel = self.parent.getQuantityLabel()
        gs_id = self.parent.getGridSubsetID() -1

        gg = ggdVars[0] # grid_ggd index
        g = ggdVars[1]  # ggd index

        getGGD = getEPGGD(self.ep)

        self.num_obj_0D, self.num_obj_1D, self.num_obj_2D = \
            getGGD.getNObj(gridId=gg)

        # Reading IDS grid geometry and physics quantities array
        nodes = np.zeros(shape=(self.num_obj_0D, 2))
        # quad_conn_array = np.zeros(shape=(self.num_obj_2D, 4), dtype=np.int)
        nElements = len(self.ep.grid_ggd[gg].grid_subset[gs_id].element)
        quad_conn_array = np.zeros(shape=(nElements, 4), dtype=np.int)

        # List of nodes and corresponding coordinates (2D spade - x and y)
        for i in range(self.num_obj_0D):
            # X coordinate
            nodes[i][0] = \
                self.ep.grid_ggd[gg].space[0].objects_per_dimension[0].object[i].geometry[0]
            # Y coordinate
            nodes[i][1] = \
                self.ep.grid_ggd[gg].space[0].objects_per_dimension[0].object[i].geometry[1]
        #
        # # Connectivity array. Each quad is formed using 4 nodes/points
        # for i in range(self.num_obj_2D):
        #     for j in range(0,4):
        #         quad_conn_array[i][j] = \
        #             self.ep.grid_ggd[gg].space[0].objects_per_dimension[2].object[i].nodes[j] - 1

        for i in range(nElements):
            object = self.ep.grid_ggd[gg].grid_subset[gs_id].element[
                i].object[0]
            ind = object.index - 1
            s = object.space - 1
            d = object.dimension - 1

            for j in range(0,4):
                quad_conn_array[i][j] = \
                    self.ep.grid_ggd[gg].space[s].objects_per_dimension[
                        d].object[ind].nodes[j] - 1

        self.showMeshPlot(nodes, quad_conn_array, qValues)

    def showMeshPlot(self, nodes, elements, values):

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

        ax = self.figure.add_subplot(111)
        ax.set_aspect('equal')

        pc = quatplot(y,z, np.asarray(elements), values, ax=ax,
                      cmap="plasma")
        self.figure.colorbar(pc, ax=ax)
        # ax.plot(y,z, marker="o", ls="", color="crimson")
        ax.plot(y,z, ls="", color="crimson")
        # Set background
        ax.set_facecolor((0.75, 0.75, 0.75))

        ax.set(title='This is the plot for: quad', xlabel='Y Axis', ylabel='Z Axis')

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

        self.setModal(True)

        self.setWindowTitle(title)

        formLayout = QFormLayout(self)

        self.lineEditContainer = {}

        for i in range(GetGGDVars.numOfParams):
            currLineEdit = QLineEdit()
            currLineEdit.setText(GetGGDVars.names[i])
            currLineEdit.setObjectName(GetGGDVars.names[i])
            self.lineEditContainer[i] = currLineEdit
            if parameters[i]:
                currLineEdit.setText(parameters[i])
            else:
                currLineEdit.setText(GetGGDVars.defaultValues[i])

            formLayout.addRow(GetGGDVars.names[i], currLineEdit)

        # Setting integer validator for run and shot numbers.
        self.lineEditContainer[GetGGDVars.ggd_slice].setValidator(
            QIntValidator())
        self.lineEditContainer[GetGGDVars.grid_ggd_slice].setValidator(QIntValidator())

        # Set comboboxes
        self.combobox_gridSubset = QComboBox()
        self.combobox_quantity = QComboBox()

        self.gg_lineEdit = self.lineEditContainer[0]
        self.g_lineEdit = self.lineEditContainer[1]

        self.populateComboBoxGS()
        self.populateComboBoxQ()

        self.gg_lineEdit.textChanged.connect(self.populateComboBoxGS)

        self.combobox_gridSubset.currentTextChanged.connect(
            self.populateComboBoxQ)

        self.findChild(QLineEdit, 'grid_ggd_slice').text()
        self.findChild(QLineEdit, 'ggd_slice')

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

        if self.gg_lineEdit.text().isdigit() != True:
            return

        gg = int(self.gg_lineEdit.text())

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

        if self.gg_lineEdit.text().isdigit() != True:
            return

        if self.g_lineEdit.text().isdigit() != True:
            return

        gg = int(self.gg_lineEdit.text())
        g = int(self.g_lineEdit.text())
        gs_name = self.combobox_gridSubset.currentText()
        gs_id = self.gridSubsetDict[gs_name]

        ggd = self.ep.ggd[g]

        # Electron temperature
        for i in range(len(ggd.electrons.temperature)):
            if ggd.electrons.temperature[i].grid_subset_index == gs_id:
                qLabel = 'Electron Temperature'
                self.combobox_quantity.addItem(qLabel)
                self.quantityDict[qLabel] = ggd.electrons.temperature[i].values

        # Electron density
        for i in range(len(ggd.electrons.density)):
            if ggd.electrons.density[i].grid_subset_index == gs_id:
                qLabel = 'Electron Density'
                self.combobox_quantity.addItem(qLabel)
                self.quantityDict[qLabel] = ggd.electrons.density[i].values

    def getValue(self, Id):
        return self.lineEditContainer[Id].text()

    def on_close(self):
        # Returning a dictionary of values. The values are defined in
        # enumerator class GetGGDVars.

        variables = {}

        for i in range(GetGGDVars.numOfParams):
            variables[i] = self.getValue(i)

        # Checking if validating Integers.
        try:
            variables[GetGGDVars.grid_ggd_slice] = int(variables[GetGGDVars.grid_ggd_slice])
            variables[GetGGDVars.ggd_slice] = \
                int(variables[GetGGDVars.ggd_slice])
        except ValueError as e:
            variables[GetGGDVars.grid_ggd_slice] = -1
            variables[GetGGDVars.ggd_slice] = -1

        curr_quantity = self.combobox_quantity.currentText()
        curr_gridSubset_id = int(self.gridSubsetDict[
                                     self.combobox_gridSubset.currentText()])

        return variables, curr_gridSubset_id, curr_quantity, \
               self.quantityDict[curr_quantity]

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

    plotWidget.checkIDS()
    plotWidget.setGGD()

    plotWidget.plotData()

    title = 'Test: Plot edge_profiles GGD'

    mainWindow.setWindowTitle(title)

    widget =  QWidget(mainWindow)
    mainWindow.setCentralWidget(plotWidget)
    mainWindow.show()

    sys.exit(app.exec_())