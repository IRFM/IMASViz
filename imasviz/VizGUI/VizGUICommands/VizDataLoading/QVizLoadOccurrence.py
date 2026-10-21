# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Asking the case for one occurrence of one IDS, for one slice choice.

Two commands used to sit between a menu entry and the walk. `QVizLoadSelectedData`
held the request and a class attribute named `Lock`; `QVizLoadDataHandling.loadSelectedData`
built the request and, for the fourth slice choice, opened the dialog that names
a slice. Measured on the reference case:

* `Lock` is keyed by IDS name and lives on the class, so it is shared by every
  shot view: loading `equilibrium` in one view blocks the other. It is also
  self-defeating, because `__init__` writes `Lock[IDSName] = False` -- measured,
  `{'equilibrium': True}` straight after a load started, and `{'equilibrium':
  False}` again as soon as the next command object was constructed, before
  anything was asked of the case. So a double click never met a guard;
* the whole body sat in `try`, with a bare `except:` that printed a traceback on
  stdout and logged the same traceback: the reason a load failed never reached
  the log panel as a sentence;
* the slice dialog was built with no parent (`QInputDialog()`, then
  `getInt(None, ...)`) and its spin box accepted anything up to 2147483647, while
  the reference `equilibrium` occurrence holds 49 slices, so 0 to 48 are valid.
  A refusal came four seconds later, from inside the walk, in a message naming
  neither the count nor the bound.

So one command does the work, and the guard lives on the view that owns the
load: a view cannot be asked for the same occurrence twice at once, and another
view is free to load the same occurrence.
"""

import logging

from imasviz.VizDataAccess.VizTimeSlices import FIRST_SLICE
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand


class QVizLoadOccurrence(QVizAbstractCommand):
    """Load one occurrence of one IDS into one shot view.

    `sliceSelection` is the choice of how many elements of a dynamic array of
    structures the view keeps -- the object, never a number. None means the
    default the manual gives to a plain load: the first slice.
    """

    def __init__(self, dataTreeView, idsName, occurrence=0,
                 sliceSelection=None, asynch=True):
        QVizAbstractCommand.__init__(self, dataTreeView, None)
        self.idsName = idsName
        self.occurrence = occurrence
        self.sliceSelection = FIRST_SLICE if sliceSelection is None else sliceSelection
        self.asynch = asynch

    def execute(self):
        view = self.dataTreeView
        if self.sliceSelection.asksForAnIndex():
            # The menu entry that still has to ask is not a load request: the
            # menu asks, a script passes the index it wants. A dialog opened
            # from here would appear in the middle of a script.
            raise ValueError(
                'No time slice index was given for occurrence %d of the %s IDS: '
                'the menu asks the user for one, a script has to name it.'
                % (self.occurrence, self.idsName))
        if view.isLoadInFlight(self.idsName, self.occurrence):
            logging.getLogger(view.uri).info(
                'Occurrence %d of the %s IDS is already being loaded in this '
                'view: this request is ignored.'
                % (self.occurrence, self.idsName))
            return
        self.dataTreeView.dataSource.load(view, self.idsName, self.occurrence,
                                          self.sliceSelection, self.asynch)
