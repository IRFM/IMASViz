import traceback, logging

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizLoadSelectedData(QVizAbstractCommand):
    def __init__(self, dataTreeView, IDSName, occurrence=0, asynch=True):
        QVizAbstractCommand.__init__(self, dataTreeView, None)
        self.occurrence = occurrence
        self.asynch = asynch
        self.IDSName = IDSName

    def execute(self):
        try:
            self.dataTreeView.dataSource.load(self.dataTreeView, self.IDSName, self.occurrence,
                                           self.asynch)


        except :
            traceback.print_exc()
            logging.error(traceback.format_exc())
