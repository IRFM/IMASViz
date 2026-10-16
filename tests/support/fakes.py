# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Stand-ins for the collaborators components expect.

Plot widgets and data access take a tree node and a data source. Building real
ones needs a data dictionary and an opened case, so most component tests drive
the widgets through these instead.
"""

import numpy as np

from imasviz.VizEntities.QVizDataArrayHandle import ArrayCoordinates, QVizDataArrayHandle


def make_2d_array_handle(name='test', x_size=100, y_size=200, timeCoordinateDim=2):
    """A synthetic 2D array: no IMAS case and no data dictionary required."""
    coordinatesPath = [name + '.x', name + '.y']
    coordinatesValues = [np.linspace(0., 100., num=x_size),
                         np.linspace(10., 33., num=y_size)]
    coordinatesLabels = ['x_label', 'y_label']
    arrayCoordinates = ArrayCoordinates(coordinatesPath, coordinatesValues,
                                        timeCoordinateDim, coordinatesLabels)

    sinX = np.sin(coordinatesValues[0] / 50.)
    cosY = np.cos(coordinatesValues[1] / 20.)
    arrayValues = np.zeros((x_size, y_size))
    for i in range(x_size):
        arrayValues[i, :] = sinX[i] * cosY

    return QVizDataArrayHandle(arrayCoordinates, arrayValues, name,
                               'label of ' + name)


class FakeTreeNode:
    """Enough of QVizTreeNode for the widgets and the data access layer."""

    def __init__(self, name='node', idsName='equilibrium', path='equilibrium:0',
                 occurrence=0):
        self._name = name
        self._idsName = idsName
        self._path = path
        self._occurrence = occurrence

    def getName(self):
        return self._name

    def getIDSName(self):
        return self._idsName

    def getPath(self):
        return self._path

    def getOccurrence(self):
        return self._occurrence

    def getDataSource(self):
        return None

    def isPlotToPerformAlongTimeAxis(self, plotWidget=None):
        return False

    def timeValue(self):
        return 0


class FakeTreeView:
    """Enough of QVizDataTreeView for the view parser contract.

    The parser writes into IDSNameSelected, reads parent.eventResultId when
    asynchronous, and delivers the tree through updateView.
    """

    class _Parent:
        eventResultId = 999

    def __init__(self, uri=''):
        self.IDSNameSelected = {}
        self.parent = FakeTreeView._Parent()
        self.uri = uri
        self.roots = {}

    def updateView(self, idsName, ids_instance, occurrence, idsData, strategy):
        self.roots[(idsName, occurrence)] = idsData
