# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The two sub-menus that start a load: which occurrence, which slices.

`QVizLoadDataHandling` did both. Measured on the reference case:

* `updateMenu` asked the case for the occurrences still to load through
  `Viz_API.GetAllOccurrencesUnloadedWithAvailableData`, which raises
  `AttributeError: module 'imas' has no attribute '<ids>'` -- the method exists,
  it has no body that can answer -- so the menu was built empty and the entry
  that opens it was already unreachable: `hasAvailableData()` raises the same
  way one line earlier. The guard under it, `if availableOccurrences is None:
  return`, was dead code, that helper having no path that returns None;
* `buildingViewMenu` listed the four slice choices in the order 3, 2, 1, 4 --
  the order of the names against the identifiers they map to -- and reached the
  dialog for the fourth through `if viewLoadingStrategy.getIdentifier() == 4`,
  so nothing else in that method knew what was being asked;
* a cancelled dialog logged `Bad input from user.` as an error, saying neither
  what was bad nor that nothing had been loaded.

What is here instead builds both menus from what the case and the view answer
today, and asks the one question the fourth choice needs -- parented to the view
that owns the dialog, bounded by the number of slices the occurrence in memory
actually holds when that number is known.
"""

import logging
from functools import partial

from PySide6.QtWidgets import QInputDialog

from imasviz.VizDataAccess.VizTimeSlices import (
    QVizTimeSliceSelection, atIndex, dynamicArrayCount, menuSelections)
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence


class QVizOccurrenceMenu:
    """Fills the pop-up menus that load an occurrence or add a view of one."""

    def buildOccurrencesMenu(self, node, dataTreeView, menu):
        """One entry per occurrence this case holds and this view has not built.

        `node` is the IDS root of the empty shot view: the occurrences are asked
        of the case, and the ones already on screen are dropped by the view.
        """
        unloaded = dataTreeView.occurrences.unloaded(
            node.getIDSName(), dataTreeView.loadedOccurrences(node.getIDSName()))
        for occurrence in unloaded:
            menu.addAction('Occurrence %d' % occurrence).triggered.connect(
                partial(self.loadOccurrence, dataTreeView, node.getIDSName(),
                        occurrence, None))
        if not unloaded:
            # The entry that opens this menu is only offered when the IDS holds
            # data, so an empty menu can only mean every occurrence is already
            # displayed -- which is worth saying rather than hiding.
            menu.addAction('all occurrences of %s are already displayed'
                           % node.getIDSName()).setEnabled(False)

    def buildViewsMenu(self, node, dataTreeView, menu):
        """One entry per slice choice, for an occurrence already on screen."""
        for selection in menuSelections():
            menu.addAction(selection.menuLabel()).triggered.connect(
                partial(self.loadOccurrence, dataTreeView, node.getIDSName(),
                        node.getOccurrence(), selection))

    def loadOccurrence(self, dataTreeView, idsName, occurrence, sliceSelection):
        """Run the load the menu entry stands for, reporting why it did not run.

        A selection that still needs an index gets the question first; a
        declined question loads nothing and says so.
        """
        if sliceSelection is not None and sliceSelection.asksForAnIndex():
            index = self.askTimeSliceIndex(dataTreeView, idsName)
            if index is None:
                logging.getLogger(dataTreeView.uri).info(
                    'No time slice index was given: occurrence %d of the %s IDS '
                    'is displayed as it is, no new view was added.'
                    % (occurrence, idsName))
                return
            sliceSelection = atIndex(index)
        try:
            QVizLoadOccurrence(dataTreeView=dataTreeView, idsName=idsName,
                               occurrence=occurrence,
                               sliceSelection=sliceSelection).execute()
        except ValueError as error:
            logging.getLogger(dataTreeView.uri).error(error)

    @staticmethod
    def askTimeSliceIndex(dataTreeView, idsName):
        """Ask which element of the dynamic array to keep, or None if declined.

        The dialog belongs to the shot view that asked for it: measured, the old
        one was built with no parent at all, so it opened unowned and unbounded.
        The upper bound is the number of elements the occurrence already in
        memory holds -- measured at 49 for the reference `equilibrium` -- which
        an IDS not loaded yet cannot give; then the spin box stays open and the
        walk refuses an index past the end, naming how many there are.
        """
        count = dynamicArrayCount(dataTreeView.loadedIds(idsName))
        box = QInputDialog(dataTreeView)
        index, accepted = box.getInt(
            dataTreeView, 'Add a view of the %s IDS' % idsName,
            'Time slice index:', 0, 0,
            count - 1 if count else QVizTimeSliceSelection.LARGEST_INDEX)
        return index if accepted else None
