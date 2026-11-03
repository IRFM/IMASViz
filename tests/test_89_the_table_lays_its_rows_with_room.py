# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The panels of a Table Plot View sit on a grid -- and a grid with no spacing
of its own lays them flush.

The vertical spacing of the row is now set by the window rather than inherited
from whatever style answers when it is never asked. The request was vertical --
the rows stack, the panels do not -- so the vertical spacing is the one moved,
and it is a little room, not a gap.
"""

import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot

from support import ownership

pytestmark = [pytest.mark.ui]


def test_the_panels_of_a_table_get_room_between_their_rows(qapp):
    """A line a style never chose: the row spacing is set, not inherited.

    The spacing a Qt layout answers when it is never asked (6 on this node)
    laid the panels of a table flush against each other, and a page of a panel
    of the Profiles plugin is exactly that table with a hundred of them. The
    complaint was room, and a gap is its own complaint: the row answers a
    little more than the style's own answer, and the window's grid carries that
    value on it.
    """
    table = ownership.keep(QVizTablePlot(title='TablePlotView:rows'))

    # The row the window lays its panels on is the one it names.
    assert table.grid.verticalSpacing() == QVizTablePlot.ROW_SPACING
    # A little more than the style's own answer (6) -- room, not a gap.
    assert 6 < QVizTablePlot.ROW_SPACING <= 16
