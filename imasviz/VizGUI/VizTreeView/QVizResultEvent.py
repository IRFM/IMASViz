# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

from PySide6.QtCore import QEvent


class QVizResultEvent(QEvent):
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
        # thread-safe
        super(QVizResultEvent, self).__init__(QEvent.Type(eventID))
        self.data = idsData
