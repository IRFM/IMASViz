# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from imasviz.VizDataAccess.QVizTSDataAccess import QVizTSDataAccess

from imasviz.VizDataAccess.QVizTensorDataAccess import QVizTensorDataAccess
from imasviz.VizUtils import QVizGlobalValues


class QVizDataAccessFactory:

    def __init__(self, dataSource):
        self.dataSource = dataSource

    def create(self):
        if self.dataSource.name == QVizGlobalValues.TORE_SUPRA:
            return QVizTSDataAccess(self.dataSource)

        elif self.dataSource.name == QVizGlobalValues.IMAS_NATIVE or \
                self.dataSource.name == QVizGlobalValues.IMAS_UDA:
            # Both IMAS sources answer the same GetSignal contract, local or
            # remote. A preference used to choose a second reader here so a plot
            # could be compared between the two; that one read the path to a
            # quantity by evaluating it as an expression, and answered nothing at
            # all for a quantity of three axes or more. The comparison is over
            # and the reader with it.
            return QVizTensorDataAccess(self.dataSource)
