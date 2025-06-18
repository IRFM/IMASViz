# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

import traceback, logging

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizLoadSelectedData(QVizAbstractCommand):

    Lock = {}

    def __init__(self, dataTreeView, IDSName, occurrence=0, viewLoadingStrategy=None, asynch=True):
        QVizAbstractCommand.__init__(self, dataTreeView, None)
        self.occurrence = occurrence
        self.asynch = asynch
        self.IDSName = IDSName
        self.viewLoadingStrategy = viewLoadingStrategy
        QVizLoadSelectedData.Lock[self.IDSName] = False

    def execute(self):
        try:
            if QVizLoadSelectedData.Lock[self.IDSName]:
                return

            QVizLoadSelectedData.Lock[self.IDSName] = True
            self.dataTreeView.dataSource.load(self.dataTreeView,
                                              self.IDSName,
                                              self.occurrence,
                                              self.viewLoadingStrategy,
                                              self.asynch)
            QVizLoadSelectedData.Lock[self.IDSName] = False

        except:
            QVizLoadSelectedData.Lock[self.IDSName] = False
            traceback.print_exc()
            logging.getLogger(self.dataTreeView.uri).error(traceback.format_exc())
