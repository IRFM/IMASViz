import traceback

from imasviz.VizGUI.VizGUICommands.AbstractCommand import AbstractCommand


class LoadSelectedData(AbstractCommand):
    def __init__(self, dataTreeView, occurrence=0, pathsList = None, async=True):
        AbstractCommand.__init__(self, dataTreeView, None)
        self.occurrence = occurrence
        self.async = async
        self.pathsList = pathsList

    def execute(self):
        try:
            self.dataTreeView.dataSource.load(self.dataTreeView, self.occurrence,
                                           self.pathsList, self.async)

        except :
            traceback.print_exc()
            self.dataTreeView.log.error(traceback.format_exc())
