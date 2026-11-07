# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The Slice entry: the IDS's 1D-profiles, at the slice the tree stands on.

One window per IDS, one curve per profile the case fills: the reader answers
which leaf holds a value and which reads empty, so an IDS that is only partly
filled draws the parts it holds and says how many it left, and an IDS that
holds nothing is refused by name rather than handed an empty figure.

The entry is offered on an IDS root, the way the Profiles entry is: the
question it answers is about the IDS, not about the node it was clicked on.
Interpolated value at an arbitrary time is the `plot_slice` tool; this one
draws the slice the case's tree is standing on.
"""

from imasviz.VizPlugins.VizPlugin import VizPlugin


class VizSlicePlugin(VizPlugin):

    def __init__(self):
        self.figureKey = None

    def isEnabled(self):
        return True

    def getEntries(self):
        """One entry, for any IDS root. What is in it is the case's answer."""
        return [0]

    def getAllEntries(self):
        return [(0, 'Draw the slice of the %s IDS…'
                 % self.selectedTreeNode.getIDSName())]

    def execute(self, vizAPI, pluginEntry, answers=None):
        """Draw this IDS's filled 1D-profiles at the standing slice.

        `answers` is what a session replaying this entry already gave in the
        user's place (occurrence, figure key); from the menu it is None, and
        the first occurrence the case holds is the one drawn.
        """
        view = self.dataTreeView
        idsName = self.selectedTreeNode.getIDSName()
        # Which occurrences exist is the opened case's answer, never the data
        # dictionary's -- the same rule the Profiles entry keeps.
        occurrences = view.occurrences.occurrencesOf(idsName)
        if not occurrences:
            raise ValueError(
                'the case holds no occurrence of the %s IDS, so there is no '
                'slice to draw.' % idsName)
        occurrence = occurrences[0] if answers is None else answers.occurrence
        if occurrence not in occurrences:
            raise ValueError(
                'the case holds no occurrence %d of the %s IDS: it answers %s.'
                % (occurrence, idsName,
                   ' and '.join(str(one) for one in occurrences)))

        from imasviz.VizAgent.core import McpGuiCore
        core = McpGuiCore(api=vizAPI)
        answer = core.plot_slice_all(
            view.dataSource.uri, idsName, occurrence=occurrence)
        self.figureKey = answer['figure']
        return

    def getDescription(self):
        return ('Draw the IDS\u2019s 1D-profiles at the slice the tree is '
                'standing on, one curve each, in a single figure.\n'
                'Author: IMASViz team')

    def getPluginsConfiguration(self):
        return None
