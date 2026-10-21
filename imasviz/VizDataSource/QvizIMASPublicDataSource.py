# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import imas
from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource, caseLabel


class QVizIMASPublicDataSource(QVizIMASDataSource):

    def __init__(self, name, uri):

        super(QVizIMASPublicDataSource, self).__init__(name, uri)

    # This defines the unique key attached to each data which can be plotted
    def dataKey(self, vizTreeNode):
        return self.name + "::" + self.uri +  '::' + vizTreeNode.getPath()

    def getShortLabel(self):
        return caseLabel(self.uri, getattr(self, 'legacy_attributes', None))

    def getLongLabel(self):
        return "UDA URI:" + self.uri

    def open(self, data_entry):
        data_entry.open()
