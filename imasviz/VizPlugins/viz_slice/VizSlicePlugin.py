# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The Slice entry: the IDS's 1D-profiles, at the slice the tree stands on.

One window per IDS, one curve per profile the case fills: the reader answers
which leaf holds a value and which reads empty, so an IDS that is only partly
filled draws the parts it holds and says how many it left, and an IDS that
holds nothing is refused by name rather than handed an empty figure.

The entry is offered on an **IDS** root, the way the Profiles entry is: the
question it answers is about the IDS, not about the node it was clicked on.
Interpolated value at an arbitrary time is the `plot_slice` tool; this one
draws the slice the case's tree is standing on.

Declared the same way as the rest of this pass: a `SCOPE` (any IDS root here)
and the one `ACTION` it offers, whose `run` is the work and whose `label`, of
the place it is offered on, reads "the equilibrium IDS" under one root and
"the wall IDS" under another.
"""

from imasviz.VizPlugins.VizPlugin import (IDS, QVizPluginAction,
                                          QVizPluginScope, VizPlugin)


class VizSlicePlugin(VizPlugin):

    def __init__(self):
        self.figureKey = None
        # Where this entry is offered: on any IDS root. A quantity has no IDS of
        # its own to stand on, and a case or the application is not what this
        # entry answers, so the scope is declared once instead of tested per node.
        self.SCOPE = QVizPluginScope(IDS)
        self.ACTIONS = (
            QVizPluginAction(
                0,
                # The same line reads "the equilibrium IDS" under one root and
                # "the wall IDS" under another -- a plugin whose answer is about
                # the IDS has to say which one it is drawn for.
                lambda ctx: 'Draw the slice of the %s IDS…' % ctx.idsName,
                run=self.draw,
                description='Draw the IDS\u2019s 1D-profiles at the slice the '
                            'tree is standing on, one curve each, in a single '
                            'figure.\n'
                            'Author: IMASViz team'),
        )

    def draw(self, context):
        """Draw this IDS's filled 1D-profiles at the slice the tree stands on.

        `context` carries the api, the case it was offered from, and the node it
        was offered on. `answers` is what a session replaying this already gave
        in the user's place (occurrence, figure key); from the menu it is None,
        and the first occurrence the case holds is the one drawn.
        """
        node = context.node
        view = context.view
        idsName = node.getIDSName()
        # Which occurrences exist is the opened case's answer, never the data
        # dictionary's -- the same rule the Profiles entry keeps.
        occurrences = view.occurrences.occurrencesOf(idsName)
        if not occurrences:
            raise ValueError(
                'the case holds no occurrence of the %s IDS, so there is no '
                'slice to draw.' % idsName)
        occurrence = (occurrences[0] if context.answers is None
                      else context.answers.occurrence)
        if occurrence not in occurrences:
            raise ValueError(
                'the case holds no occurrence %d of the %s IDS: it answers %s.'
                % (occurrence, idsName,
                   ' and '.join(str(one) for one in occurrences)))

        from imasviz.VizAgent.core import McpGuiCore
        core = McpGuiCore(api=context.api)
        answer = core.plot_slice_all(
            view.dataSource.uri, idsName, occurrence=occurrence)
        self.figureKey = answer['figure']
        return
