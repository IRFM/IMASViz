# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The entries that draw a selection, and the frames they land in.

Selecting signals and asking for a figure is how a user compares quantities, so
this is the entry whose failures are the most expensive -- and measured here on
real tree nodes, the legacy path failed three ways at once. A quantity the
dictionary ranks above 1D made `plot1DSelectedSignals` `return` from inside the
loop over the selection: three nodes selected, **one curve drawn**, the node
after the refused one never read, and a window left on screen to close by hand.
The window was opened by `GetPlotWidget` and embedded in the MDI area before
anything was read, so a refusal cost a window. And an empty selection -- the
selection emptied between the menu being built and the click, which is exactly
what `updateMenuNodeSelection` rebuilds it against -- died with
`UnboundLocalError: cannot access local variable 'e'`, raised out of the menu
handler by the `logging.getLogger(...).error(str(e))` line that sat outside any
`except`.

What it drew was no better: a 1D quantity held by a dynamic array came back with
the four coordinate values along the abscissa and its time element pinned at the
index the tree happened to carry, under an empty title and with nothing on the
figure naming that element. The gate that hid the entry, `shareSameCoordinates`,
answered `True` for two nodes whose first coordinates differ, because it asked
the legacy predicates and the legacy frame factory rather than the axes. The
window factory and that gate are gone with the frames behind them.

So the entries are re-pointed at `QVizPlotAsSlices`, which already draws the
selection through the tensor read for the other menu entry, and the two entries
merge into one: the user selects quantities, the command picks the frame.

Nothing here opens a case: a filled leaf inside arrays of structures needs a case
whose arrays are filled, and no reference case on this checkout has them.
"""

import numpy as np
import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea, QMenu

from imasviz.VizUtils import FigureTypes
from imasviz.Viz_API import Viz_API
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot

from support.fakes import FakeAxesNode
from support.ownership import keep

RHO = [0., 1., 2., 3.]
THETA = [0., .25, .5, .75]
TIMES = [0., 1., 2., 3., 4.]
TREE_TIME = 1

AOS, LEAF = 'AOS', 'LEAF'
TIME_SLICE = (AOS, 'foo', 'time_slice')
RADIAL = (LEAF, 'foo', 'rho_tor')


def vectorValues(timeIndex):
    return [100. * timeIndex + 10. * i for i in range(len(RHO))]


def _ids():
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    ids.rho_tor = list(RHO)
    ids.theta_poloidal = list(THETA)
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = TIMES[timeIndex]
        timeSlice.vector = vectorValues(timeIndex)
        timeSlice.other_vector = [v + 1 for v in vectorValues(timeIndex)]
        # Rows along rho_tor, columns along theta_poloidal: a coordinate array
        # whose length disagrees with the shape it names makes the picture and
        # its axes disagree, which is what the read exists to avoid.
        timeSlice.matrix = [[100. * timeIndex + 10. * row + column
                             for column in range(len(THETA))]
                            for row in range(len(RHO))]
        ids.time_slice.append(timeSlice)
    return ids


def _inTime(name='vector', coordinates=('rho_tor',)):
    """A 1D quantity held by the dynamic array: time is one axis to pin or draw."""
    return FakeAxesNode(_ids(), 'foo', 'foo.time_slice[itime]', 'FLT_1D',
                        name=name, units='K', itimeIndex=0,
                        coordinates=coordinates,
                        coordinateUnits={1: 'm'},
                        indices={'i': str(TREE_TIME)},
                        lengths={'i': str(len(TIMES))})


def _emptyInTime():
    """The same quantity, holding nothing: the read cannot answer for it."""
    ids = _ids()
    for timeSlice in ids.time_slice:
        timeSlice.vector = []
    return FakeAxesNode(ids, 'foo', 'foo.time_slice[itime]', 'FLT_1D',
                        name='vector', units='K', itimeIndex=0,
                        coordinates=('rho_tor',), coordinateUnits={1: 'm'},
                        indices={'i': str(TREE_TIME)},
                        lengths={'i': str(len(TIMES))})


def _image():
    """A quantity of two axes: the legacy entry refuses it outright."""
    return FakeAxesNode(_ids(), 'foo', 'foo.time_slice[itime]', 'FLT_2D',
                        name='matrix', units='Pa', itimeIndex=0,
                        coordinates=('rho_tor', 'theta_poloidal'),
                        coordinateUnits={1: 'm', 2: 'rad'},
                        indices={'i': str(TREE_TIME)},
                        lengths={'i': str(len(TIMES))})


@pytest.fixture
def view(qapp):
    """One shot view holding a selection, and the api it reports its figures to."""

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

    shot = FakeView()
    # The MDI area owns the windows the entries open, so it has to outlive the
    # call that builds it: the api holds it as its Qt parent. And the entries
    # *show* the frames they open (QVizPlotAsSlices shows the frame it drew), so
    # this shot, its mdi and the frames registered in its api must outlive the
    # test too -- see support/ownership.py.
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    return keep(shot)


def select(view, *nodes):
    view.selectedSignalsDict = {node.getParametrizedDataPath():
                                {'QTreeWidgetItem': node} for node in nodes}
    view.selectedItem = nodes[0] if nodes else None
    return view


def entry(view):
    """The entries as the menu fires them."""
    return QVizSignalHandling(dataTreeView=view, treeNode=view.selectedItem)


@pytest.fixture
def bar(qapp):
    """A menu to hang the selection menu on.

    The entry builds its menu as a child of the one it is handed, and Qt deletes
    children along with their parent: a parent left as an unnamed temporary takes
    the whole selection menu down before the test can read a single title.
    """
    return QMenu()


def frames(view, frameClass):
    return [frame for frame in view.imas_viz_api.figureframes.values()
            if isinstance(frame, frameClass)]


def curveData(frame, index=0):
    x, y = frame.curves()[index].getData()
    return np.asarray(x), np.asarray(y)


def subMenu(menu, title):
    for action in menu.actions():
        if action.text() == title:
            return action.menu()
    raise AssertionError('no %r submenu in %r' %
                         (title, [action.text() for action in menu.actions()]))


def titles(menu):
    return [action.text() for action in menu.actions()]


# ---------------------------------------------------------------------------
# The entry, and what a refusal costs.

@pytest.mark.ui
def test_a_selection_of_two_quantities_draws_two_curves(view):
    select(view, _inTime('vector'), _inTime('other_vector'))

    entry(view).plotSelectedSignals(all_DTV=False)

    frame = frames(view, QVizCurvePlot)[0]
    # Both quantities are held by the dynamic array, so the curve runs along
    # time: comparing two quantities means comparing their histories, which is
    # what a selection is for. The coordinate they share is pinned, and the
    # figure says where (test_the_curve_says_which_element...).
    assert frame.curveCount() == 2
    np.testing.assert_allclose(curveData(frame, 0)[0], TIMES)
    np.testing.assert_allclose(curveData(frame, 0)[1],
                               [100. * t for t in TIMES])
    np.testing.assert_allclose(curveData(frame, 1)[1],
                               [100. * t + 1 for t in TIMES])


@pytest.mark.ui
def test_a_quantity_of_two_axes_in_the_selection_costs_nothing_to_the_others(view):
    # The legacy command logs 'Plots dimension larger than 1D are currently not
    # supported.' and returns out of the loop: three nodes selected, one curve
    # drawn, the node after the refused one never read. A picture frame exists,
    # and a user selects quantities rather than figure types.
    select(view, _inTime('vector'), _image(), _inTime('other_vector'))

    entry(view).plotSelectedSignals(all_DTV=False)

    curves = frames(view, QVizCurvePlot)[0]
    assert curves.curveCount() == 2
    pictures = frames(view, QVizImagePlot)
    assert len(pictures) == 1
    assert pictures[0].imageCount() == 3


@pytest.mark.ui
def test_an_empty_selection_answers_with_a_reason_and_lets_the_menu_finish(view,
                                                                          caplog):
    select(view)

    entry(view).plotSelectedSignals(all_DTV=False)

    # The legacy entry raised UnboundLocalError out of the menu handler, because
    # the message line reads str(e) outside any except.
    assert view.imas_viz_api.figureframes == {}
    assert 'selection' in caplog.text.lower()


@pytest.mark.ui
def test_a_selection_that_reads_as_nothing_costs_no_window(view, caplog):
    select(view, _emptyInTime())

    entry(view).plotSelectedSignals(all_DTV=False)

    assert view.imas_viz_api.figureframes == {}
    assert 'foo.time_slice[itime].vector' in caplog.text


# ---------------------------------------------------------------------------
# The frames are the ones the api can manage, in one namespace.

@pytest.mark.ui
def test_the_windows_are_recorded_under_the_keys_their_titles_carry(view):
    select(view, _inTime('vector'), _image())

    entry(view).plotSelectedSignals(all_DTV=False)

    assert view.imas_viz_api.GetFiguresKeys(
        figureType=FigureTypes.CURVEPLOTTYPE) == ['SlicesPlot1']
    assert view.imas_viz_api.GetFiguresKeys(
        figureType=FigureTypes.IMAGEPLOTTYPE) == ['SlicesImage1']
    assert sorted(view.imas_viz_api.figToNodes['SlicesPlot1']) == \
           ['foo.time_slice[itime].vector']
    assert sorted(view.imas_viz_api.figToNodes['SlicesImage1']) == \
           ['foo.time_slice[itime].matrix']


@pytest.mark.ui
def test_the_selection_entry_keeps_the_legacy_figure_namespace_out(view):
    select(view, _inTime('vector'))

    entry(view).plotSelectedSignals(all_DTV=False)

    # A second namespace for one kind of window is two Show/Hide menus and one
    # window the "add to" entries cannot fill.
    assert not [key for key in view.imas_viz_api.figureframes
                if key.startswith('Figure:')]


@pytest.mark.ui
def test_the_curve_says_which_element_of_the_pinned_axis_it_answered(view):
    # The legacy figure drew the four coordinate values under an empty title,
    # with the time element fixed at the index the tree carried and nothing on
    # the screen naming it. Two quantities held by the same dynamic array are
    # histories, so the new figure runs along time and pins the coordinate the
    # two happen to share -- naming, on the figure, where it pinned it.
    select(view, _inTime('vector'))

    entry(view).plotSelectedSignals(all_DTV=False)

    frame = frames(view, QVizCurvePlot)[0]
    assert list(frame.sliceControls.keys()) == [RADIAL]
    assert [row.nameLabel.text() for row in frame.sliceControls.rows()] == \
           ['rho_tor:']
    assert frame.sliceControls.rows()[0].slider.maximum() == len(RHO) - 1
    np.testing.assert_allclose(curveData(frame)[0], TIMES)


# ---------------------------------------------------------------------------
# Adding the selection to a figure that is already open.

@pytest.mark.ui
def test_the_selection_lands_in_the_figure_that_is_already_open(view):
    select(view, _inTime('vector'))
    entry(view).plotSelectedSignals(all_DTV=False)
    select(view, _inTime('other_vector'))

    entry(view).addSelectedSignalsPlotToFig(1, all_DTV=False)

    assert view.imas_viz_api.GetFiguresKeys(
        figureType=FigureTypes.CURVEPLOTTYPE) == ['SlicesPlot1']
    frame = frames(view, QVizCurvePlot)[0]
    assert frame.curveCount() == 2
    assert sorted(view.imas_viz_api.figToNodes['SlicesPlot1']) == \
           ['foo.time_slice[itime].other_vector',
            'foo.time_slice[itime].vector']


@pytest.mark.ui
def test_a_quantity_the_open_figure_cannot_show_is_refused_with_a_reason(view,
                                                                        caplog):
    select(view, _inTime('vector'))
    entry(view).plotSelectedSignals(all_DTV=False)
    select(view, _image())

    entry(view).addSelectedSignalsPlotToFig(1, all_DTV=False)

    # A picture needs its own colour scale and its own window; the curve figure
    # keeps what it can show and says what it turned down.
    assert frames(view, QVizCurvePlot)[0].curveCount() == 1
    assert frames(view, QVizImagePlot) == []
    assert 'foo.time_slice[itime].matrix' in caplog.text


# ---------------------------------------------------------------------------
# One entry per intent, not two.

@pytest.mark.ui
def test_the_menu_offers_one_figure_entry_for_the_selection(view, bar):
    select(view, _inTime('vector'))

    menu = entry(view).menuPlotSelectedSignalNodes(parentMenu=bar)

    # The two entries drew the same selection through two paths and keyed the
    # windows in two namespaces; the command picks the frame, so one is enough.
    assert 'Curves and images with slice controls' not in titles(menu)
    figureMenu = subMenu(menu, 'Figure')
    newMenu = subMenu(figureMenu, 'New')
    assert titles(newMenu) == ['This IMAS Database', 'All IMAS Databases']


@pytest.mark.ui
def test_the_menu_lists_the_figures_the_entry_can_fill(view, bar):
    select(view, _inTime('vector'))
    entry(view).plotSelectedSignals(all_DTV=False)

    menu = entry(view).menuPlotSelectedSignalNodes(parentMenu=bar)
    figureMenu = subMenu(menu, 'Figure')

    assert titles(figureMenu) == ['New', 'SlicesPlot1']
    assert titles(subMenu(figureMenu, 'SlicesPlot1')) == \
           ['This IMAS Database', 'All IMAS Databases']


@pytest.mark.ui
def test_the_menu_offers_no_figure_entry_for_an_empty_selection(view, bar):
    select(view)

    menu = entry(view).menuPlotSelectedSignalNodes(parentMenu=bar)

    assert 'Figure' not in titles(menu)


@pytest.mark.ui
def test_two_quantities_on_different_coordinates_are_both_drawn(view, bar):
    # The gate the figure entries were hidden behind asked the legacy predicates
    # and the legacy frame factory, and hid the entry with no reason when it
    # answered False. Here each quantity carries its own controls, so there is
    # nothing to gate: a right click and a click are all the user asked.
    select(view, _inTime('vector', coordinates=('rho_tor',)),
           _inTime('other_vector', coordinates=('theta_poloidal',)))

    menu = entry(view).menuPlotSelectedSignalNodes(parentMenu=bar)
    assert titles(subMenu(subMenu(menu, 'Figure'), 'New')) == \
           ['This IMAS Database', 'All IMAS Databases']
    entry(view).plotSelectedSignals(all_DTV=False)

    assert frames(view, QVizCurvePlot)[0].curveCount() == 2
