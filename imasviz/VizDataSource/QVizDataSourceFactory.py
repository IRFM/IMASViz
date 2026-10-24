# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizUtils import QVizGlobalValues


# A factory for creating native data-source for IMAS.
#
# An URI is the whole description of a case. The factory used to take the five
# "legacy parameters" Access Layer 4 needed to build an entry, and to refuse
# without them; the Access Layer has answered 5 for its major version on every
# stack this application has run on, so that refusal never fired and the
# parameters it collected were read by nothing.
class QVizDataSourceFactory:

    def create(self, uri):
        return QVizIMASDataSource(QVizGlobalValues.IMAS_NATIVE, uri)
