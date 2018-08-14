from PyQt5.QtCore import QEvent

class ResultEvent(QEvent):
    """ This function sets a custom QEvent.
    Note: used in ETNativeDataTree generated files. Upon creation of this
    event the QVizDataTreeViewFrame.onUpdate function gets run.
    """
    def __init__(self, idsData, eventID):
        """
        Arguments:
            idsData (obj) : Object holding IDS data
            eventID (int) : Custom even ID.
        """
        #thread-safe
        super(ResultEvent, self).__init__(eventID)
        self.data = idsData