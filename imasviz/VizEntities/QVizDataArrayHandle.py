# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

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
