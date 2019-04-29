import traceback

from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizLoadSelectedData(QVizAbstractCommand):
    def __init__(self, dataTreeView, IDSName, occurrence=0, async=True):
        QVizAbstractCommand.__init__(self, dataTreeView, None)
        self.occurrence = occurrence
        self.async = async
        self.IDSName = IDSName

    def execute(self):
        try:
            self.dataTreeView.dataSource.load(self.dataTreeView, self.IDSName, self.occurrence,
                                           self.async)


        except :
            traceback.print_exc()
            self.dataTreeView.log.error(traceback.format_exc())
