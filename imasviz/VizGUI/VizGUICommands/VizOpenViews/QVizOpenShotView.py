# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

import os
import logging
from imasviz.Viz_API import Viz_API
from imasviz.VizUtils import QVizGlobalValues


class QVizOpenShotView:
    def __init__(self, parent=None):
        self.api = Viz_API(parent)

    def Open(self, evt, uri, legacy_attributes=None):
                
        from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
        from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource

        try:
            print("QVizOpenShotView::legacy_attributes=", legacy_attributes)
            dataSource = QVizDataSourceFactory(legacy_attributes).create(uri)

            dtv = None
            if self.api.isDataSourceAlreadyOpened(dataSource):
                dtv = self.api.GetDTVFor(dataSource.getKey())
            else:
                dtv = self.api.CreateDataTree(dataSource)

            self.api.ShowDataTree(dtv)
            
        except ValueError as e :
            logging.getLogger('logPanel').error(str(e))
