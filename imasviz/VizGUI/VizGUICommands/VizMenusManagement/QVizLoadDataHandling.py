#          Commands to handle data loading.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr
#
# *****************************************************************************

# *****************************************************************************
#     Copyright(c) 2016- L. Fleury,X. Li, D. Penko
# *****************************************************************************

from functools import partial
import logging
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QInputDialog

from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadSelectedData import QVizLoadSelectedData


class QVizLoadDataHandling(QObject):
    """Setting the popup menu: Load the contents of the selected IDS.
    """

    def __init__(self):
        super(QVizLoadDataHandling, self).__init__()

    def updateMenu(self, rootNode, dataTreeView, subMenu, viewLoadingStrategy=None):
        """Show the pop-up menu for loading IDS.

        Arguments:
            rootNode    (QVizTreeNode) : selected node
            dataTreeView : current selected view
            subMenu : menu to update
            :param rootNode:
            :param subMenu:
            :param dataTreeView:
            :param viewLoadingStrategy:
        """
        from imasviz.VizGUI.VizTreeView.QVizViewLoadingStrategy import QVizViewLoadingStrategy
        if viewLoadingStrategy is None:
            viewLoadingStrategy = QVizViewLoadingStrategy.getDefaultStrategy()

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
                                                              rootNode.getIDSName(), i, viewLoadingStrategy, True))

    def buildingViewMenu(self, rootNode, dataTreeView, subMenu):
        """Show the pop-up menu for building a new view to the IDS data.

        Arguments:
            rootNode    (QVizTreeNode) : selected node
            dataTreeView : current selected view
            subMenu : menu to update
        """
        from imasviz.VizGUI.VizTreeView.QVizViewLoadingStrategy import QVizViewLoadingStrategy
        viewLoadingStrategies = QVizViewLoadingStrategy.getAllStrategies()
        for viewLoadingStrategy in viewLoadingStrategies:
            action_GET_IDS_OCC_DATA = \
                subMenu.addAction(viewLoadingStrategy.getName())
            # - Connect action to function using partial
            #   Note: PyQt5 lambda method is not a good way to pass the
            #         function arguments. The use of partial is better
            #         and more bulletproof
            action_GET_IDS_OCC_DATA.triggered.connect(partial(self.loadSelectedData,
                                                              dataTreeView,
                                                              rootNode.getIDSName(), rootNode.getOccurrence(),
                                                              viewLoadingStrategy, True))

    def loadSelectedData(self, dataTreeView, IDSName, occurrence=0, viewLoadingStrategy=None,
                         threadingEvent=None):
        """Load data of selected IDS and its occurrence.

        Arguments:
            occurrence     (int) : IDS occurrence number (0-9).
            threadingEvent ()    : Event.
            :param threadingEvent:
            :param viewLoadingStrategy:
            :param occurrence:
            :param IDSName:
            :param dataTreeView:
        """
        from imasviz.VizGUI.VizTreeView.QVizViewLoadingStrategy import QVizViewLoadingStrategy
        if viewLoadingStrategy is None:
            viewLoadingStrategy = QVizViewLoadingStrategy.getDefaultStrategy()

        if viewLoadingStrategy.getIdentifier() == 4:
            user_input = QInputDialog()
            minLimit, ok = user_input.getInt(None, 'Enter time slice index value to be displayed', 'Time slice index:',
                                             value=0, min=0)
            if not ok:
                logging.error('Bad input from user.')
                return
            viewLoadingStrategy.setTimeIndex(minLimit)

        QVizLoadSelectedData(dataTreeView=dataTreeView,
                             IDSName=IDSName,
                             occurrence=occurrence,
                             viewLoadingStrategy=viewLoadingStrategy,
                             asynch=threadingEvent).execute()
