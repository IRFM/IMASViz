#  Name   :IDSTree
#
#          Container to handle data loading.
#          Note: The wxPython predecessor of this Python file is
#          LoadDataHandling.py
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#  TODO:
#
#    - Function definitions (from LoadDataHandling class)
#       def popUpMenuHandler
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury,X. Li, D. Penko
# *****************************************************************************

from functools import partial

from PyQt5.QtCore import QObject

from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData import QVizLoadSelectedData


class QVizLoadDataHandling(QObject):
    """Setting the popup menu: Load the contents of the selected IDS.
    """

    def __init__(self):
        """
        Arguments:
            dataTreeView (QTreeWidget) : DataTreeView object of the QTreeWidget.
        """
        super(QVizLoadDataHandling, self).__init__()

    def updateMenu(self, rootNode, dataTreeView, subMenu):
        """Show the pop up menu for loading IDS.

        Arguments:
            rootNode    (QVizTreeNode) : selected node
            dataTreeView : current selected view
            subMenu : menu to update
        """
        api = dataTreeView.imas_viz_api
        availableOccurrences = api.GetAllOccurrencesUnloadedWithAvailableData(dataTreeView, rootNode)
        if availableOccurrences is None:
            return

        for i in availableOccurrences:
            action_GET_IDS_OCC_DATA = \
                            subMenu.addAction('Occurrence ' + str(i))
            # - Connect action to function using partial
            #   Note: PyQt5 lambda method is not a good way to pass the
            #         function arguments. The use of partial is better
            #         and more bulletproof
            action_GET_IDS_OCC_DATA.triggered.connect(partial(self.loadSelectedData,
                                                              dataTreeView,
                                                              rootNode.getIDSName(), i, True))

    def loadSelectedData(self, dataTreeView, IDSName, occurrence=0,
                         threadingEvent=None):
        """Load data of selected IDS and its occurrence.

        Arguments:
            occurrence     (int) : IDS occurrence number (0-9).
            threadingEvent ()    : Event.
        """
        QVizLoadSelectedData(dataTreeView,
                             IDSName,
                             occurrence,
                             threadingEvent).execute()
