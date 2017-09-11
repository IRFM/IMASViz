
from imasviz.gui_commands.AbstractCommand import AbstractCommand
import traceback

class ShotOverviewPlugin(AbstractCommand):
    def __init__(self, view, threadingEvent=None):
        AbstractCommand.__init__(self, view, None)
        self.threadingEvent = threadingEvent

    def execute(self):
        try:

            pass

        except :
            traceback.print_exc()
            self.view.log.error(traceback.format_exc())