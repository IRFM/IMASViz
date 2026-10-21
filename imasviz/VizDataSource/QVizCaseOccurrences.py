# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Which occurrences of which IDSs the opened case actually holds.

Everything that loads an IDS asks this question first: the tree that colours the
IDS names, the double click and the Return key, the "Get … data for occurrence"
menu. It used to be asked of the data dictionary --
`eval("imas." + idsName + "().getMaxOccurrences()")`, at five places in the
application. That module attribute does not exist on the IMAS-Python this repo
runs on: measured, `hasattr(imas, 'equilibrium')` is False and the expression
answers `AttributeError: module 'imas' has no attribute 'equilibrium'`, and
because the first of those five sites sits at the top of `containsData`, outside
its `try`, **building a shot view of the reference case fails on its first IDS**
(`AttributeError: module 'imas' has no attribute 'amns_data'`). The other four
follow: `hasAvailableData()` on a root, and the three occurrence helpers of
`Viz_API`, all measured raising. So the occurrence could not be chosen at all.

The case answers the question directly. `DBEntry.list_all_occurrences` names the
occurrences that hold data: measured on the reference case, `equilibrium` gives
`[0, 1, 2, 3]`, `pulse_schedule` `[0]`, `magnetics` `[0, 1]` and `core_sources`
`[]`; over all 55 IDS names of this data dictionary the whole inventory costs
**0.10 s**. Reading each IDS to answer the same question costs **336 s** on that
case, so this asks the entry and never reads an IDS.
"""


class QVizCaseOccurrences:
    """The occurrences of an IDS that this case holds, from the case itself.

    The data source is asked through, never cached: the entry it holds may be
    closed and rebuilt between two questions, and an inventory kept across that
    would name occurrences of a case that is no longer open.
    """

    def __init__(self, dataSource):
        self.dataSource = dataSource

    def occurrencesOf(self, idsName):
        """The occurrence numbers of `idsName` that hold data, ascending."""
        try:
            occurrences = self.dataSource.db_entry.list_all_occurrences(idsName)
        except Exception as error:
            # An IDS the case does not know at all is an IDS with nothing to
            # load -- said here, because the caller shows this in the log panel
            # and a traceback there teaches the user nothing.
            raise ValueError('Cannot ask the case for the occurrences of %r: '
                             '%s: %s' % (idsName, type(error).__name__, error))
        return sorted(int(occurrence) for occurrence in occurrences)

    def holdsIds(self, idsName):
        """Whether this case holds anything at all for `idsName`."""
        return bool(self.occurrencesOf(idsName))

    def unloaded(self, idsName, loadedOccurrences):
        """The occurrences with data that this view has not built yet."""
        return [occurrence for occurrence in self.occurrencesOf(idsName)
                if occurrence not in loadedOccurrences]

    def nextUnloaded(self, idsName, loadedOccurrences):
        """The lowest such occurrence, or None when there is no other to load.

        None is an answer, not a failure: it says every occurrence this case
        holds is already on screen, which is what the double click and the
        Return key need to know before they load anything.
        """
        remaining = self.unloaded(idsName, loadedOccurrences)
        return remaining[0] if remaining else None
