#  Name   : Viz_API
#
#          IMASViz Application Programming Interface.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# ****************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
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
            tup = (dataTreeView.dataSource.shotNumber, vizTreeNode)
            #self.api.AddNodeToFigure(self.figureKey, key, tup)

             # Get signal properties and values
            s = api.GetSignal(dataTreeView, vizTreeNode, plotWidget=None)

            if isinstance(s, QVizDataArrayHandle):

                data_features.append(s)

            elif len(s) == 2:
                label, xlabel, ylabel, title = vizTreeNode.plotOptions(dataTreeView, vizTreeNode.getShotNumber(),
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



