
from imasviz.gui_commands.AbstractCommand import AbstractCommand
import traceback

class LoadSelectedData(AbstractCommand):
    def __init__(self, dataTreeView, occurrence=0, pathsList = None, async=True):
        AbstractCommand.__init__(self, dataTreeView, None)
        self.occurrence = occurrence
        self.async = async
        self.pathsList = pathsList

    def execute(self):
        try:
            #Check if the data are already loaded and load the data source if required
            # IDSDataLoaded = self.dataTreeView.idsAlreadyFetched[self.dataTreeView.IDSNameSelected]
            # if IDSDataLoaded == 0:
            #     self.dataTreeView.dataSource.load(self.dataTreeView, self.occurrence,
            #                               self.pathsList, self.async)
            # else:
            #     self.dataTreeView.parent.updateView(self.dataTreeView.IDSNameSelected,
            #                                 self.occurrence,
            #                                 pathsList=self.pathsList)
            self.dataTreeView.dataSource.load(self.dataTreeView, self.occurrence,
                                           self.pathsList, self.async)

        except :
            traceback.print_exc()
            self.dataTreeView.log.error(traceback.format_exc())

    def refreshIDS(self):
        """Refresh the source IDS and its data.
        """
        self.dataTreeView.dataSource.refreshIDS(self.dataTreeView.IDSNameSelected,
                                        self.occurrence)
