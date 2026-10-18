# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from imasviz.VizDataAccess.QVizTSDataAccess import QVizTSDataAccess

from imasviz.VizDataAccess.QVizIMASNativeDataAccess import QVizIMASNativeDataAccess
from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizUtils import QVizGlobalValues, QVizPreferences


class QVizDataAccessFactory:

    def __init__(self, dataSource):
        self.dataSource = dataSource

    def create(self):
        if self.dataSource.name == QVizGlobalValues.TORE_SUPRA:
            return QVizTSDataAccess(self.dataSource)

        elif self.dataSource.name == QVizGlobalValues.IMAS_NATIVE or \
                self.dataSource.name == QVizGlobalValues.IMAS_UDA:
            # Both IMAS paths answer the same GetSignal contract, so the switch
            # is invisible to the widgets: it changes how many reads a plot
            # costs, not what a plot draws.
            if QVizPreferences.Tensor_based_reading:
                return QVizTensorDataAccess(self.dataSource)
            return QVizIMASNativeDataAccess(self.dataSource)
