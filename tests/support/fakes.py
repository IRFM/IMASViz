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

from imasviz.VizUtils import QVizGlobalValues
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


class FakeDocItem:
    """Enough of QVizTreeNode for the node documentation panel.

    The panel reads a node's name, its documentation, which kind of data it
    holds, and the dictionary attributes it displays. Driving it through a real
    node means building a real tree, which means a case and a data dictionary;
    the panel's own contract -- what it shows, and what it hides when the
    dictionary says nothing -- is the same either way.
    """

    def __init__(self, name='rho_tor', dataName='rho_tor', documentation='doc',
                 dataType='FLT_0D', content='2.42', lifecycleStatus=None,
                 is0D=True, is1D=False, is2DOrLarger=False, isDynamic=False,
                 isStatic=False, isIDSRoot=False, path='tf.rho_tor'):
        self._name = name
        self._dataName = dataName
        self._documentation = documentation
        self._dataType = dataType
        self._is0D = is0D
        self._is1D = is1D
        self._is2DOrLarger = is2DOrLarger
        self._isDynamic = isDynamic
        self._isStatic = isStatic
        self._isIDSRoot = isIDSRoot
        self._path = path
        self.infoDict = {'0D_content': content}
        if lifecycleStatus is not None:
            self.infoDict['lifecycle_status'] = lifecycleStatus

    def getName(self):
        return self._name

    def getDataName(self):
        return self._dataName

    def getDocumentation(self):
        return self._documentation

    def getDataType(self):
        return self._dataType

    def getPath(self):
        return self._path

    def getData(self):
        return self.infoDict

    def getInfoDict(self):
        return self.infoDict

    def isIDSRoot(self):
        return self._isIDSRoot

    def isDynamicData(self):
        return self._isDynamic

    def isStaticData(self):
        return self._isStatic

    def is0D(self):
        return self._is0D

    def is1D(self):
        return self._is1D

    def is2DOrLarger(self):
        return self._is2DOrLarger

    def evalPath(self, expression):
        return None


class FakeAxesNode:
    """Enough of QVizTreeNode for the axes model and a data access.

    A quantity held by arrays of structures needs what QVizDataTreeViewBuilder
    copies onto a real node: the parametrized path, the index of the dynamic
    array, the current index and length of each enclosing array, the leaf
    coordinates and the data type. Nothing Qt, and no case to open -- which is
    how a rank 3 quantity gets tested at all, when no reference case holds one
    with values in it.
    """

    def __init__(self, idsRef, idsName, parametrizedPath, dataType, name='value',
                 itimeIndex=-1, coordinates=(), indices=None, lengths=None,
                 units='', coordinateUnits=None, infoDict=None, timeIndex=0,
                 alongTime=True):
        self._idsRef = idsRef
        self._idsName = idsName
        self._parametrizedPath = parametrizedPath
        self._dataType = dataType
        self._name = name
        self._itimeIndex = itimeIndex
        self._units = units
        self._coordinateUnits = coordinateUnits or {}
        self._infoDict = infoDict or {}
        self._timeIndex = timeIndex
        self._alongTime = alongTime
        self.coordinates = list(coordinates)
        self.parameters_values = dict(indices or {})
        self.parameters_max_values = dict(lengths or {})

    def getIDSRef(self):
        return self._idsRef

    def getIDSName(self):
        return self._idsName

    def getName(self):
        return self._name

    getDataName = getName

    def getParametrizedPath(self):
        return self._parametrizedPath

    def getParametrizedDataPath(self):
        return self._parametrizedPath + '.' + self._name

    def getItimeIndex(self):
        return self._itimeIndex

    def getDataType(self):
        return self._dataType

    def getUnits(self):
        return self._units

    def getCoordinateUnits(self, coordinateNumber):
        return self._coordinateUnits.get(coordinateNumber)

    def getInfoDict(self):
        return self._infoDict

    def getDataSource(self):
        return None

    def timeValue(self):
        """The index the tree carries for the dynamic array, as QVizTreeNode does.

        The read takes this as the time slice while the axes model takes
        parameters_values for the same array, so a stub where the two disagree
        would hide a drift the real node cannot have.
        """
        letter = QVizGlobalValues.indices.get(str(self.getItimeIndex() + 1))
        value = self.parameters_values.get(letter)
        return self._timeIndex if value is None else value

    def isPlotToPerformAlongTimeAxis(self, plotWidget=None):
        return self._alongTime

    def evaluateCoordinateAt(self, coordinateNumber, itimeValue):
        """The coordinate path, spelled from the IDS.

        A real node substitutes the loop placeholders of a coordinate that moves
        with time; a stub spells its coordinates from the IDS level and holds
        arrays of the same name there, so there is nothing to substitute.
        """
        return self._idsName + '.' + self.coordinates[coordinateNumber - 1]

    def labels(self, plotWidget, coordinateNumber, coordinate_index, time_index):
        """(quantity, figure label, coordinate label) as QVizTreeNode spells them.

        Reading a two-dimension leaf takes its numbers from the tensor and its
        words from the node, so a stub that reaches that path has to answer.
        """
        quantity = self._name
        if self._units:
            quantity += '[' + self._units + ']'
        coordinate = self.coordinates[coordinateNumber - 1]
        units = self.getCoordinateUnits(coordinateNumber)
        coordinateLabel = self._idsName + '.' + coordinate
        if units:
            coordinateLabel += '[' + units + ']'
        return quantity, self.getParametrizedDataPath(), coordinateLabel
