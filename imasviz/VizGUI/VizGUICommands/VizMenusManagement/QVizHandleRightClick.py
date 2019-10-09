
#  Name   : QVizHandleRightClick
#
#          Container to handle right click events in PyQt5.
#          Note: The wxPython predecessor of this Python file is
#          HandleRightClick.py. 'HandleRightClickAndShiftDown' routine was
#          moved to separate file - QVizHandleShiftDownAndRightClick.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#****************************************************
#  TODO:
#
#    - class HandleRightClickAndShiftDown definition
#
#****************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#****************************************************

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizLoadDataHandling import QVizLoadDataHandling
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling import QVizSignalHandling
from imasviz.VizUtils.QVizGlobalValues import GlobalColors


class QVizHandleRightClick:
    """ Handle the mouse right click event on a PyQt5 QTreeWidget.
    TODO: currently the right click menu creation is done in QVizSignalHandling
          (as right click are currently performed only on signal nodes).
    """

    # def __init__(self, dataTreeView):
    #     """
    #     Arguments:
    #         dataTreeView (QTreeWidget) : QVizDataTreeView object.
    #     """
    #     self.dataTreeView = dataTreeView

    def execute(self, node, dataTreeView):
        """
        Arguments:
            node (QVizTreeNode) : Item (node) from in the QTreeWidget.
        """
        #self.test(dataTreeView)
        # Get the data source attached to the dataTreeView
        dataSource = dataTreeView.dataSource
        showPopUp = 0

        # Get the Python dictionary attached to the node
        dico = node.getInfoDict()

        if dico == None:
            # TODO
            # showPopUpMenu = PluginsHandler(self.dataTreeView, dico)
            # showPopUp = showPopUpMenu.showPopUpMenu(['overview'])
            return showPopUp

        dataName = dataSource.dataNameInPopUpMenu(dico)

        if not 'isSignal' in dico:
            return showPopUp

        isSignal = dico['isSignal']
        isIDSRoot = dico['isIDSRoot']

        # If the node is a signal, call showPopUpMenu function for plotting data
        if isSignal == 1 and node.isDataAvailable():
            showPopUpMenu = QVizSignalHandling(dataTreeView=dataTreeView)
            showPopUp = showPopUpMenu.showPopUpMenu(signalNodeName=dataName)
        else:
            # If the node is a IDS node, call showPopMenu for loading IDS data
            if isIDSRoot != None and isIDSRoot == 1:
                if dico['availableIDSData'] == 1:
                    showPopUpMenu = QVizLoadDataHandling()
                    showPopUp = showPopUpMenu.showPopUpMenu(dataName, dataTreeView)

        return showPopUp

    # def test(self, dataTreeView):
    #     # Check if necessary system variables are set
    #     from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
    #     QVizGlobalOperations.checkEnvSettings()
    #
    #     # Set Application Program Interface
    #     from imasviz.Viz_API import Viz_API
    #     from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
    #     api = Viz_API()
    #
    #     # Set data source retriever/factory
    #     dataSourceFactory = QVizDataSourceFactory()
    #
    #     from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues
    #     # Load IMAS database
    #     dataSource = dataSourceFactory.create(
    #         dataSourceName=QVizGlobalValues.IMAS_NATIVE,
    #         shotNumber=54178,
    #         runNumber=0,
    #         userName='imas_public',
    #         imasDbName='west')
    #
    #     # Build the data tree view frame
    #     #f = api.CreateDataTree(dataSource)
    #
    #     #api.LoadIDSData(self, 'magnetics', 0, 0)
    #     from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData import QVizLoadSelectedData
    #     QVizLoadSelectedData(dataTreeView, 'magnetics', 0, 0).execute()
    #     #self.show()
