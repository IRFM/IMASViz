# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The two abscissae a quantity can be drawn along, both reachable from the tree.

A quantity held by the dynamic array answers two of them, and the manual
documents both as separate sections: the history along the clock, and the profile
along the coordinate the dictionary declares. Only one of them had an entry.
Measured on the reference case (WEST 54924, DD 3.35.0), right-clicking
**equilibrium.time_slice[0].profiles_1d.f**:

    the axes model          [TIME, ('coordinate', 'time_slice.profiles_1d.psi')]
    Plot ... to -> New      along time            (49 points, 32,13 s ... 48,55 s)
    Plot as function of time   along time         -- the same curve twice
    along psi               **no entry at all**

so the profile was unreachable from the pop-up while the preview panel docked
beside the tree drew it: that panel asks the read with `along_time=False` and
gets 101 points against `psi`. The command behind the menu accepted the reading
all along (`QVizPlotOneNode(alongTime=False)`, what the Profiles plugin's two
entries have always passed) -- the entry was simply never built.

What is pinned here:

    the two entries, side by side, each naming the abscissa it draws against
    each drawing the curve its title says, on the case as on the stubs
    one entry where a quantity has one abscissa -- a coordinate that *is* a time
    base is the same clock spelled differently, not a second curve to offer
    neither entry where the quantity has two axes to draw: that is a picture

The second half of the file is the entry that follows from these:
:guilabel:`Explore this tensor along <axis>` is now one per abscissa, because the
arrays a figure leaves out belong to the abscissa it runs against. The manual
promises a slider on **time_slice** on the figure drawn along `psi`; asked for one
abscissa only, the entry could not offer it on a fresh right click, and the
window it needed had no entry left to open it with.
"""

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea

from imasviz.Viz_API import Viz_API
from imasviz.VizDataAccess.QVizCurveAbscissa import TIME
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot

from support.fakes import FakeAxesNode

ALONG_GRID = 'Plot as function of its index'
ALONG_TIME = 'Plot as function of time'

TIMES = [32.13, 40.34, 48.55]
# Four points per slice, three slices: the profile is 4 points, the history 3.
PROFILE = [[10., 20., 30., 40.],
           [11., 21., 31., 41.],
           [12., 22., 32., 42.]]


def _ids(homogeneousTime=0):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = homogeneousTime
    ids.time = list(TIMES)
    ids.time_slice = []
    for index in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        # At homogeneous_time 0 the clock is spelled under the element that
        # carries the quantity -- which is what the reference case does for
        # `equilibrium`, where `time_slice[i].time` holds the same 49 values as
        # `equilibrium.time`. A stub leaving it empty reads NaN for the abscissa.
        timeSlice.time = TIMES[index]
        timeSlice.f = list(PROFILE[index])
        ids.time_slice.append(timeSlice)
    return ids


def _profileInTimeSlices():
    """One 1D leaf per element of the dynamic array -- the user's shape.

    `equilibrium.time_slice[i].profiles_1d.f` down to its axes: a leaf of one
    axis, held by the array that carries the clock. The dictionary leaves its
    coordinate unbounded here, which names the same second abscissa without
    needing the grid of the case.
    """
    return FakeAxesNode(_ids(), 'foo', 'foo.time_slice[itime]', 'FLT_1D',
                        name='f', itimeIndex=0, coordinates=('1..N',),
                        indices={'i': '0'}, lengths={'i': str(len(TIMES))})


def _timedByItsOwnCoordinate():
    """A 1D leaf whose own coordinate *is* the clock: one abscissa, not two.

    The shape `magnetics.flux_loop[i].flux.data` has on the case at
    `homogeneous_time == 1`. A second entry there would offer the same curve
    twice under two spellings of one axis.
    """
    ids = _ids(homogeneousTime=1)
    ids.flux = type(str('Flux'), (), {})()
    ids.flux.time = list(TIMES)
    ids.flux.data = [7., 9.]
    return FakeAxesNode(ids, 'foo', 'foo.flux', 'FLT_1D', name='data',
                        coordinates=('flux.time',), coordinateUnits={1: 's'},
                        alongTime=False)


def _twoAxesToDraw():
    """Two axes on the leaf: a picture, and neither entry has a curve to open."""
    ids = _ids()
    ids.matrix = [[1., 2., 3.], [4., 5., 6.]]
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_2D', name='matrix',
                        coordinates=('1..N', '1..M'))


@pytest.fixture
def view(qapp):
    """One shot view and the api it reports its figures to, with an MDI area."""

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
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    return shot


def handling(view, node):
    node.dataTreeView = view
    if not hasattr(node, 'default_coordinates'):
        node.default_coordinates = {}
    return QVizSignalHandling(dataTreeView=view, treeNode=node)


def entries(view, node):
    """The entries the right click offers at its top level, in the order shown."""
    menu = handling(view, node).buildContextMenu(node)
    return [action.text() for action in menu.actions()]


def trigger(view, node, maker):
    """One entry of the pop-up, built and triggered as the click does."""
    action = maker(handling(view, node))
    assert action is not None
    action.trigger()
    frames = [frame for frame in view.imas_viz_api.figureframes.values()
              if isinstance(frame, QVizCurvePlot)]
    assert len(frames) == 1, view.imas_viz_api.figureframes
    return frames[0]


def plotted(figure, index=0):
    x, y = figure.curves()[index].getData()
    return list(x), list(y)


def bottom(figure):
    return figure.pgPlotWidget.getAxis('bottom').labelText


# -- the two entries -----------------------------------------------------

@pytest.mark.ui
def test_a_quantity_of_the_dynamic_array_is_offered_along_both(view):
    texts = entries(view, _profileInTimeSlices())

    assert ALONG_TIME in texts
    assert ALONG_GRID in texts
    # Side by side, before the entries that ask which window.
    assert texts.index(ALONG_GRID) == texts.index(ALONG_TIME) + 1


@pytest.mark.ui
def test_the_coordinate_entry_draws_the_profile_of_the_slice_the_tree_names(view):
    """The curve the preview panel draws, now reachable from the menu.

    Slice 0, four points: the leaf's own axis, one element of the dynamic array.
    """
    frame = trigger(view, _profileInTimeSlices(),
                    lambda h: h.actionPlotAsFunctionOfCoordinate())

    assert frame.abscissa == ('dimension', '')
    assert frame.abscissa != TIME
    assert plotted(frame)[1] == PROFILE[0]
    assert bottom(frame) == 'dimension 1'


@pytest.mark.ui
def test_the_time_entry_still_draws_the_history(view):
    """The default of the plain entry is untouched: time first, T36."""
    frame = trigger(view, _profileInTimeSlices(),
                    lambda h: h.actionPlotAsFunctionOfTime())

    assert frame.abscissa == TIME
    assert plotted(frame)[0] == TIMES
    assert plotted(frame)[1] == [line[0] for line in PROFILE]
    assert bottom(frame) == 'time'


# -- one entry where there is one abscissa -------------------------------

@pytest.mark.ui
def test_a_coordinate_that_is_a_time_base_gets_one_entry_not_two(view):
    node = _timedByItsOwnCoordinate()

    assert handling(view, node).actionPlotAsFunctionOfTime() is not None
    assert handling(view, node).actionPlotAsFunctionOfCoordinate() is None
    assert ALONG_TIME in entries(view, node)
    assert ALONG_GRID not in entries(view, node)


@pytest.mark.ui
def test_a_quantity_of_two_axes_to_draw_gets_neither(view):
    node = _twoAxesToDraw()

    assert handling(view, node).actionPlotAsFunctionOfCoordinate() is None
    assert handling(view, node).actionPlotAsFunctionOfTime() is None


# -- the tensor entry, one per abscissa ----------------------------------

ALONG_TIME_TENSOR = 'Explore this tensor along time axis'
ALONG_GRID_TENSOR = 'Explore this tensor along its index'


def tensorLines(view, node, heading):
    menu = handling(view, node).buildContextMenu(node)
    for action in menu.actions():
        sub = action.menu()
        if sub is not None and sub.title() == heading:
            return [line.text() for line in sub.actions()]
    raise AssertionError('no %r submenu in %r'
                         % (heading, [a.text() for a in menu.actions()]))


@pytest.mark.ui
def test_the_tensor_entry_of_the_coordinate_is_offered_on_a_bare_right_click(view):
    """The slider the manual promises, reachable without a figure already open.

    Asked for the quantity's default abscissa only, this heading needed an open
    figure drawn along the coordinate -- and no entry knew how to open one.
    """
    assert tensorLines(view, _profileInTimeSlices(), ALONG_GRID_TENSOR) == ['New']


@pytest.mark.ui
def test_the_clock_heading_is_not_offered_when_the_history_has_nothing_left_out(view):
    """One heading per abscissa means **none** where an abscissa leaves nothing.

    Along the clock this quantity keeps one value per slice: the dynamic array is
    the axis being drawn, so there is no axis left to put a slider on. Offering
    *Explore this tensor along time axis* there would open a figure whose band
    controls walk nothing. Two headings need two arrays to leave out, which is
    the shape test_64's ``ion`` array pins.
    """
    node = _profileInTimeSlices()
    menu = handling(view, node).buildContextMenu(node)
    headings = [action.menu().title() for action in menu.actions()
                if action.menu() is not None]

    assert ALONG_GRID_TENSOR in headings
    assert ALONG_TIME_TENSOR not in headings


@pytest.mark.ui
def test_the_tensor_heading_draws_the_abscissa_it_names(view):
    """The title is not decoration: it travels to the command.

    Triggered through the line of the menu, because the abscissa a heading
    promises reaches the read in the connection the menu makes. Called by hand
    with no opinion, a quantity of the dynamic array settles on the clock
    whatever it was titled, and the sliders are then the clock's leftovers.
    """
    node = _profileInTimeSlices()
    menu = handling(view, node).buildContextMenu(node)
    for action in menu.actions():
        sub = action.menu()
        if sub is not None and sub.title() == ALONG_GRID_TENSOR:
            assert sub.actions()[0].text() == 'New'
            sub.actions()[0].trigger()
            break
    else:
        raise AssertionError('no %r submenu' % ALONG_GRID_TENSOR)
    frame = list(view.imas_viz_api.figureframes.values())[-1]

    assert frame.abscissa == ('dimension', '')
    assert frame.sliceControls.keys() == [('AOS', 'foo', 'time_slice')]


# -- the same, on the leaf the manual demonstrates -----------------------

CASE_LEAF = 'equilibrium.time_slice[i].profiles_1d.f'
GRID_ABSISSA = ('coordinate', 'time_slice.profiles_1d.psi')


@pytest.fixture(scope='module')
def caseBundle(qapp, request):
    from support import caseTrees
    return caseTrees.loadCaseTrees(qapp, ['equilibrium'], request=request)


@pytest.mark.ui
@pytest.mark.case
def test_the_case_offers_the_grid_of_the_dictionary_by_name(caseBundle, qapp):
    """**Plot as function of psi**, on the leaf the manual walks.

    101 points against `psi` for the entry, 49 against the clock for its sibling:
    the two numbers the manual states for this very leaf, now both one click away.
    """
    from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip
    from support import caseTrees as helper
    from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource

    uri = case_uri_or_skip()
    bundle = caseBundle['trees']['equilibrium']
    for element, path in helper.shadowTreePaths(bundle, 'equilibrium'):
        if element.text == CASE_LEAF:
            node = helper.nodeAsTheBuilderBuildsIt(
                element, 'equilibrium', caseBundle['runtime']['equilibrium'],
                None, path=path)
            break
    else:
        raise AssertionError('no %r in the shadow tree' % CASE_LEAF)

    shot = QObject()
    shot.mdi = QMdiArea()
    shot.uri = uri
    shot.dataSource = QVizIMASDataSource('west 54924', uri)
    shot.dataSource.dd_version = CASE_DATA_DICTIONARY_VERSION
    shot.selectedItem = None
    shot.selectedSignalsDict = {}
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = []
    node.dataTreeView = shot

    menu = QVizSignalHandling(dataTreeView=shot, treeNode=node)
    coordinate = menu.actionPlotAsFunctionOfCoordinate()
    assert coordinate is not None, [a.text() for a in
                                    menu.buildContextMenu(node).actions()]
    assert coordinate.text() == 'Plot as function of psi'

    coordinate.trigger()
    frame = list(shot.imas_viz_api.figureframes.values())[0]
    assert frame.abscissa == GRID_ABSISSA
    assert len(plotted(frame)[0]) == 101
    assert bottom(frame) == 'psi'
