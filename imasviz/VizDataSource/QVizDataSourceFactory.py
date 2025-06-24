# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import os

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizUtils import QVizGlobalValues


# A factory for creating native data-source for IMAS
class QVizDataSourceFactory:

    def __init__(self, legacy_attributes=None):
        if QVizIMASDataSource.getVersion() == 4:
            if legacy_attributes is None or len(legacy_attributes) == 0:
                raise ValueError("Creating a datasource using AL4 required legacy parameters in the datasource factory.")
        self.legacy_attributes = legacy_attributes

    def create(self, uri):
        dataSource = QVizIMASDataSource(QVizGlobalValues.IMAS_NATIVE, uri)
        if QVizIMASDataSource.getVersion() == 4:
            if self.legacy_attributes is not None and len(self.legacy_attributes) > 0:
                dataSource.legacy_attributes = self.legacy_attributes
        return dataSource

