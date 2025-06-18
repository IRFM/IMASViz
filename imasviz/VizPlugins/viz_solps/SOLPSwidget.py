# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

#  Name   : SOLPSwidget
#
#          A PyQt5 widget, embedding Matplotlib canvas (plot space). It contains
#          also defined PyQt5 slots for setting the edge_profiles IDS, GGD
#          parameters and a slot (function) for executing the plot procedure,
#          populating/filling the Matplotlib canvas.
#
#  Author :
#         Dejan Penko
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#     Copyright(c) 2019- D. Penko

import sys
import os
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout
from PySide6.QtCore import Slot

import logging
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from src.quadPlotCanvas import QuadPlotCanvas
from src.GGDDialog import GetGGDDialog
from src.getEPGGD import getEPGGD, GetGGDVars


class SOLPSwidget(QWidget):

    """Plot edge_profiles (EP) IDS GGD.
    """
    def __init__(self, parent=None, ids=None, *args, **kwargs):
        QWidget.__init__(self, parent)

        # Check if display is available (display is mandatory, as this is
        # PyQt5 widget)
        self.checkDisplay()
        # Set object name
        # self.setObjectName('QtDesignerWidget')

        self.gridSubsetDict = {}

        self.gs_id = 0
        self.qLabel = ''
        self.qValues = 0

        self.quantityValuesDict = {}

        self.ggdVars = {}
        for i in range(GetGGDVars.numOfParams):
            # At the begining clear all parameters
            self.ggdVars[i] = ''

        # Set IDS object
        self.ids = ids

        # Set layout
        self.setLayout(QVBoxLayout())
        # Set empty matplotlib canvas
        self.canvas = QuadPlotCanvas(self, width=1, height=6)
        # Set matplotlib toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        # Add widgets to layout
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.toolbar)

    @Slot()
    def checkDisplay(self):
        try:
            os.environ['DISPLAY']
        except:
            logging.error('No display available!')

    def setIDS(self, ids):
        self.ids = ids

    @Slot()
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
        else:
            from src.getIDS import GetIDSWrapper, GetIDSDialog, GetIDSVars
            for i in range(GetIDSVars.numOfParams):
                # At the beginning clear all parameters
                self.vars[i] = ''

            dialog = GetIDSDialog(self)
            # Set note
            note = 'Note: this plugin should be used \nonly with IDSs which ' \
                   + 'contain \npopulated edge_profiles IDS!'
            dialog.prepareWidgets(self.vars, note=note)
            if dialog.exec_():
                self.vars = dialog.on_close()
            else:
                # Canceled!
                return self.ids == None
            # Set IDS with wrapper
            self.ids = GetIDSWrapper(self.vars).getIDS()

        logging.info('Getting IDS')
        # Read edge_profiles IDS
        self.ids.get('edge_profiles')

    @Slot()
    def setGGDdata(self):
        """Show dialog for setting GGD parameters.
        """
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

    @Slot()
    def getQuantityValues(self):
        return self.ggdVars['quantityValues']

    @Slot()
    def getQuantityLabel(self):
        return self.ggdVars['quantityLabel']

    @Slot()
    def getGridSubsetID(self):
        return self.ggdVars['gridSubsetId']

    @Slot()
    def getGGDVars(self):
        return self.ggdVars

    @Slot()
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

    @Slot()
    def clearPlot(self):
        """Clear canvas plot.
        """

        self.canvas.figure.clear()

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
        # Set IDS object, open it and provide it as an argument to SOLPSwidget
        # Vars = {0: 122264, 1: 1, 2: 'penkod', 3: 'iter', 4: '3'}

        # For launching python script directly from terminal with python command
        Vars = {}
        Help = """
                This is used for testing the plotting data from an edge_profilesIDS.

                In order to run this plugin, shot, run, user, device and version must
                be defined. Example (terminal):

                python3 SOLPSwidget.py --shot=122264 --run=1 --user=penkod \
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
            plotWidget = SOLPSwidget(ids)

        except Exception:
            print('Supplied option not recognized!')
            print('For help: -h / --help')
            # sys.exit(2)
            print('Switching to dialog window')
            plotWidget = SOLPSwidget()


        if len(Vars) < GetIDSVars.numOfParams:
            print('Not enough variables defined!')
            print('For help: -h / --help')
            # sys.exit(2)
            print('Switching to dialog window')
            plotWidget = SOLPSwidget()
        elif len(Vars) > GetIDSVars.numOfParams:
            print('Too many variables defined!')
            print('For help: -h / --help')
            # sys.exit(2)
            print('Switching to dialog window')
            plotWidget = SOLPSwidget()

    else:
        # Open IDS (specify parameters using dialog)
        plotWidget = SOLPSwidget()

    plotWidget.setEPIDS()
    plotWidget.setGGDdata()

    plotWidget.plotData()

    title = 'Plot edge_profiles GGD'

    mainWindow.setWindowTitle(title)

    widget =  QWidget(mainWindow)
    mainWindow.setCentralWidget(plotWidget)
    mainWindow.show()

    sys.exit(app.exec_())
