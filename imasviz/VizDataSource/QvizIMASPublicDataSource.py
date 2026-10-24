# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource, caseLabel


# A data source for the public databases of the IMAS reference installation:
# it differs from a native one by its label only, which drops the user name.
class QVizIMASPublicDataSource(QVizIMASDataSource):

    def getShortLabel(self):
        return caseLabel(self.uri)
