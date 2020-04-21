#  Name   : QVizDataArrayHandle
#
#          Containers for IMAS arrays.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#*******************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
#*******************************************************************************

import pyqtgraph as pg
import numpy as np
import logging

class QVizDataArrayHandle:
    """QVizDataArrayHandle for handling IMAS arrays.
    """
    def __init__(self, arrayCoordinates, arrayValues, itimeValue=None):
        self.arrayCoordinates = arrayCoordinates
        self.arrayValues = arrayValues
        self.itimeValue = itimeValue

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

    def getCoordinateLabels(self, dim):
        return self.arrayCoordinates.coordinate_labels[dim - 1]

class ArrayCoordinates:
    def __init__(self, coordinatesPath=[], coordinatesValues=[], timeCoordinateDim=None, coordinate_labels=[]):
        self.coordinatesPath = coordinatesPath
        self.coordinatesValues = coordinatesValues
        self.timeCoordinateDim = timeCoordinateDim
        self.coordinate_labels = coordinate_labels

class QVizTimedDataArrayHandle:
    def __init__(self, arrayValues, timeArray):
        self.arrayValues = arrayValues
        self.timeArray = timeArray


