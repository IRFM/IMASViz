# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The profiles panel chooses how wide the pages it opens are.

« Proposer aussi le nombre de plots par ligne — cette valeur peut être saisie
dans la fenêtre du plugin. »  A page of the panel is a Table Plot View, and this
window's width had no input at all: it was `columnsFor(panel count)`, so a page
of 100 quantities came out in 3 columns, a page of 4 in 2, and the user who
wanted a page in one column or eight did not have one.

The width is now a choice the panel leaves on a combo — the choice is passed to
the command, and the command leaves it on the window it fills. What the choice
is not: a second width for the tree's own gesture, which keeps the width its
page size answers, and a width a saved configuration carries, which a file
already names the cells of and is re-laid at exactly those.

`columns=None` is the width told to nobody: the window answers `columnsFor` as
it has since the table was laid once for the whole table (`test_65`), and this
is the callers who pass no choice — the tree's gesture, a session put back, a
configuration applied — stay on.
"""

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea

from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable import \
    QVizPlotAsTable
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot
from imasviz.Viz_API import Viz_API

from test_65_the_table_lays_one_panel_per_cell import (URI, _quantities, cells,
                                                       fill, perRow)
from support.ownership import keep


@pytest.fixture
def view(qapp):
    """One shot view, and the api its figures are registered to.

    The same stand-in as `test_65` builds, because this file drives the table
    the way the gesture does and asks the layout the way that test asks it.
    """

    class FakeSource(QObject):
        def __init__(self, uri):
            super().__init__()
            self.uri = uri
            self.name = 'NATIVE'

        def dataKey(self, treeNode):
            return treeNode.getParametrizedDataPath()

    class FakeView(QObject):
        def __init__(self):
            super().__init__()
            self.uri = 'imas:hdf5?case=1'
            self.dataSource = FakeSource(self.uri)
            self.selectedItem = None
            self.selectedSignalsDict = {}
            self.signalsList = []

    shot = FakeView()
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    return keep(shot)


def fillWithColumns(view, nodes, columns):
    """Draw the selection, telling the command the width its window is to hold."""
    view.signalsList = list(nodes)
    view.selectedSignalsDict = {n.getParametrizedDataPath():
                                {'index': index,
                                 'QTreeWidgetItem': n,
                                 'uri': URI}
                                for index, n in enumerate(nodes)}
    view.selectedItem = nodes[0]
    frame = QVizPlotAsTable(view, plotAxis='TIME', columns=columns).execute()
    assert isinstance(frame, QVizTablePlot)
    return frame


def expectedLayout(count, columns):
    """{row: [columns]} a `count`-panel table laid `columns` wide, row by row."""
    full, remainder = divmod(count, columns)
    layout = {row: list(range(columns)) for row in range(full)}
    if remainder:
        layout[full] = list(range(remainder))
    return layout


# ---------------------------------------------------------------------------
# A width told to the window is the width its rows are laid at.

@pytest.mark.ui
@pytest.mark.parametrize('count, columns', [
    (9, 4),
    (10, 4),
    (6, 5),
    (5, 2),
    (4, 1),
    (100, 8),
])
def test_a_page_laid_at_the_width_it_was_told(view, count, columns):
    """A page of `count` in `columns` is `count // columns` full rows and the rest.

    This is the page the button opens: 100 quantities in 8 is thirteen rows of
    eight and a last row of two, and no row is wider than the choice the panel
    left on the combo -- where `columnsFor` would have laid it in three.
    """
    frame = fillWithColumns(view, _quantities(count), columns=columns)

    assert frame.columns() == columns
    assert perRow(frame) == expectedLayout(count, columns)
    assert len(set(cells(frame))) == count, 'two panels share a cell'


@pytest.mark.ui
def test_fewer_panels_than_the_choice_stay_on_one_row(view):
    """A choice wider than the page costs no empty rows, only the row itself."""
    frame = fillWithColumns(view, _quantities(3), columns=12)

    assert frame.columns() == 12
    assert perRow(frame) == {0: [0, 1, 2]}


@pytest.mark.ui
def test_a_width_below_one_is_refused_by_name(qapp):
    """One panel per row is the narrowest width, and there is no zero of it."""
    frame = QVizTablePlot()
    with pytest.raises(ValueError, match='at least one'):
        frame.setColumns(0)
    with pytest.raises(ValueError, match='at least one'):
        frame.setColumns(-1)
    assert frame.columns() is None


@pytest.mark.ui
def test_the_choice_can_be_taken_back_to_the_page_size(qapp):
    """None is the width told to nobody, and it puts the page size back.

    The combo's first entry *auto (from the page size)* carries None, so a
    choice left there -- or taken back to it -- leaves the window on the width
    it has always answered.
    """
    frame = QVizTablePlot()
    frame.setColumns(4)
    assert frame.columns() == 4
    frame.setColumns(None)
    assert frame.columns() is None


# ---------------------------------------------------------------------------
# The tree's gesture keeps what it has always had.

@pytest.mark.ui
def test_the_tree_gesture_keeps_the_width_of_the_page_size(view):
    """The choice is the panel's; the tree draws at the width the page answers.

    The request said the value may be entered in the panel's window -- not in
    the tree's right-click, whose width has been the page size since the table
    stops reading it per panel, and `test_65` pins that layout.
    """
    frame = fill(view, _quantities(8))

    assert frame.columns() is None
    assert perRow(frame) == expectedLayout(8, QVizTablePlot.columnsFor(8))


@pytest.mark.ui
def test_a_selection_of_few_still_lays_in_two_columns_the_way_it_always_has(view):
    """A selection of four was 2x2 before this, and it is still 2x2.

    The default is the page size, not one column: a selection drawn from the
    tree with no choice anywhere must not have started coming out in a column
    because the profiles panel learned to choose.
    """
    frame = fill(view, _quantities(4))

    assert frame.columns() is None
    assert perRow(frame) == {0: [0, 1], 1: [0, 1]}
