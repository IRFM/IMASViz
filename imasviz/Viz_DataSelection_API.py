# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.
# ****************************************************

import os
import logging

from imasviz.VizUtils import (QVizGlobalOperations, FigureTypes,
                              QVizGlobalValues, QVizPreferences)
from imasviz.VizGUI.VizTreeView import QVizDataTreeView
from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle, ArrayCoordinates

from imasviz.Viz_API import Viz_API

class Viz_DataSelection_API:

    def __init__(self, parent=None):

        self.parent = parent

    def GetSelectedDataFeatures(self, dataTreeView, plotWidget=None):
        """Returns AD array values of an IMAS node.

        :returns: array values
        """
        api = Viz_API()  # Creating IMASViz Application Programming Interface

        data_features = []
        for key in dataTreeView.selectedSignalsDict:

            v = dataTreeView.selectedSignalsDict[key]
            vizTreeNode = v['QTreeWidgetItem']

            key = dataTreeView.dataSource.dataKey(vizTreeNode)
            tup = (dataTreeView.dataSource.uri, vizTreeNode)
            #self.api.AddNodeToFigure(self.figureKey, key, tup)

             # Get signal properties and values
            s = api.GetSignal(dataTreeView, vizTreeNode, plotWidget=None)

            if isinstance(s, QVizDataArrayHandle):

                data_features.append(s)

            elif len(s) == 2:
                label, xlabel, ylabel, title = vizTreeNode.plotOptions(dataTreeView, vizTreeNode.getURI(),
                                                        plotWidget=None)
                x = s[0] #coordinate
                y = s[1] #1D array
                data_features.append((key, tup, x[0], y[0], label, xlabel, ylabel, title))
            #elif len(s) == 3:
                # x = s[0] #coordinates
                # y = s[1] #2D array
                # coordinate_of_time = s[2]
                # data_features.append((key, tup, x, y, label, xlabel, ylabel, title, coordinate_of_time))
            #    data_features.append(s)
            else:
                raise ValueError('Unexpected type returned by GetSignal')

        return data_features



