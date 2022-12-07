#  Name   : QVizDataArrayHandle
#
#          Containers for IMAS arrays.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *******************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *******************************************************************************

class QVizDataArrayHandle:
    """QVizDataArrayHandle for handling IMAS arrays.
    """

    def __init__(self, arrayCoordinates, arrayValues, name, label, itimeValue=None):
        self.arrayCoordinates = arrayCoordinates
        self.arrayValues = arrayValues
        self.itimeValue = itimeValue
        self.label = label
        self.name = name

    def getCoordinateValues(self, dim):
        return self.arrayCoordinates.coordinatesValues[dim - 1]

    def getCoordinatePath(self, dim):
        return self.arrayCoordinates.coordinatesPath[dim - 1]

    def getArrayDimension(self):
        return len(self.arrayCoordinates.coordinatesPath)

    def getTimeCoordinateDim(self):
        return self.arrayCoordinates.timeCoordinateDim

    def getTimeCoordinateArray(self):
        if self.getTimeCoordinateDim() is None:
            return None
        return self.getCoordinateValues(self.getTimeCoordinateDim())

    def getCoordinateLabel(self, dim):
        return self.arrayCoordinates.coordinates_labels[dim - 1]

    def getName(self):
        return self.name

    def getLabel(self):
        return self.label


class ArrayCoordinates:
    def __init__(self, coordinatesPath=[], coordinatesValues=[],
                 timeCoordinateDim=None, coordinates_labels=[]):
        self.coordinatesPath = coordinatesPath
        self.coordinatesValues = coordinatesValues
        self.timeCoordinateDim = timeCoordinateDim
        self.coordinates_labels = coordinates_labels


class QVizTimedDataArrayHandle:
    def __init__(self, arrayValues, timeArray):
        self.arrayValues = arrayValues
        self.timeArray = timeArray
