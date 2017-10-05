
from imasviz.gui_commands.AbstractCommand import AbstractCommand
import traceback

class LoadSelectedData(AbstractCommand):
    def __init__(self, view, occurrence=0, pathsList = None, async=True):
        AbstractCommand.__init__(self, view, None)
        self.occurrence = occurrence
        self.async = async
        self.pathsList = pathsList

    def execute(self):
        try:
            #Check if the data are already loaded
            if self.view.IDSNameSelected in self.view.idsAlreadyParsed:
                IDSDataLoaded = self.view.idsAlreadyParsed[self.view.IDSNameSelected]
                if IDSDataLoaded == 1:
                    return

            # Load the data for IDS
            self.view.dataSource.load(self.view, self.occurrence, self.pathsList, self.async)
        except :
            traceback.print_exc()
            self.view.log.error(traceback.format_exc())
            #self.view.log.error("An error has occured while loading " + self.view.IDSNameSelected + " IDS.")