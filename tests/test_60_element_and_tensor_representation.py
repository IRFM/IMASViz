# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""An element of a tensor, and the tensor itself, on the same kind of figure.

The tree shows the elements of every array of an IDS. Asking for one of them used
to put a slider on each enclosing array anyway -- so the figure offered to move
the very indices that made the node the element it is, and two elements asked in
the same figure shared one slider and were therefore read at the same element.
Measured on the reference case (WEST 54924, `magnetics.flux_loop[i].flux.data`,
17 elements of 17 344 samples each): plotting element 0 then element 1 answered
**two curves with identical samples**, while the runtime says element 1 starts
`0.00817774` where element 0 starts `0.00619676` -- and both legend entries were
spelled `flux_loop[i]`, so nothing on screen said which element either came from.

Two questions, kept apart here and joined by one entry:

    an element (the plot entries)  the arrays the tree stands on are fixed, and
                                   spelled out in the legend; only the leaf's own
                                   coordinate is movable
    the tensor (Explore this tensor along <axis>) every axis the curve leaves out
                                   gets a slider, opened where the tree was
                                   standing; *Keep this curve* freezes the curve
                                   at the indices it stands on so a family can
                                   pile up

A slider costs a line of the window, so the band of a curve figure folds to one
summary line; an image window and a table panel keep theirs open, because there
the rows are the only place saying which slice the colours stand for.

Three tests open the reference case, marked `case`, and pin both halves where
they were measured. The other shapes are built in memory, because the reference
case holds no rank 3 leaf with values in it. The rank 3 case the harness knows
(`west/3/55799/0`, `hard_x_rays.channel[i].radiance.data`: 8 bands of 808 samples
in each of 38 channels) is two axes to draw at once, so its element goes to a
picture figure rather than to a curve figure under sliders -- which is the
routing, not a limit of the exploration.
"""

import pytest

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode import QVizPlotOneNode
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot
from imasviz.VizUtils import QVizPreferences

from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip
from support import ownership
from support.fakes import FakeAxesNode

AOS, LEAF = 'AOS', 'LEAF'
ION = (AOS, 'foo', 'ion')
RADIAL = (LEAF, 'foo', 'dimension 1')

# The entry says along *what* it explores, because which arrays end up under a
# slider depends on the abscissa the figure runs along: the same quantity left out
# of a figure drawn against time is not left out of one drawn against its own
# coordinate.
EXPLORE = 'Explore this tensor along time axis'

# Two time slices, two ions each, three radial points each -- the same shape
# test_24 drives, read here for the element/tensor split instead of the loop.
VALUES = {'z_ion': [[[1., 2., 3.], [10., 20., 30.]],
                    [[4., 5., 6.], [40., 50., 60.]]]}


def _idsWith(leafValues):
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    shape = next(iter(leafValues.values()))
    ids.profiles_1d = []
    for index in range(len(shape)):
        slice_ = type(str('Slice'), (), {})()
        slice_.time = None
        slice_.ion = []
        for ionIndex in range(len(shape[0])):
            ion = type(str('Ion'), (), {})()
            for leaf, values in leafValues.items():
                setattr(ion, leaf, values[index][ionIndex])
            slice_.ion.append(ion)
        ids.profiles_1d.append(slice_)
    return ids


def _leaf(name='z_ion', ionIndex='1'):
    """An *element* of `ion`: the tree is standing on it."""
    return FakeAxesNode(_idsWith(VALUES), 'foo', 'foo.profiles_1d[itime].ion[j]',
                        'FLT_1D', name=name, itimeIndex=0, coordinates=('1..N',),
                        indices={'i': '0', 'j': str(ionIndex)},
                        lengths={'i': '2', 'j': '2'})


def _inTheDynamicArrayOnly():
    """A quantity held by nothing but the dynamic array: there is nothing to walk."""
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    ids.profiles_1d = []
    for gap in (100., 200.):
        element = type(str('Element'), (), {})()
        element.time = None
        element.gap = gap
        ids.profiles_1d.append(element)
    return FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime]', 'FLT_0D', name='gap',
                        itimeIndex=0, coordinates=(), lengths={'i': '2'})


def _matrix():
    """Two axes to draw and nothing around them: a picture, not a tensor to walk."""
    ids = _idsWith(VALUES)
    ids.matrix = [[1., 2., 3.], [4., 5., 6.]]
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_2D', name='matrix',
                        coordinates=('1..N', '1..M'))


@pytest.fixture
def figure(qtbot):
    widget = QVizCurvePlot(title='SlicesPlot1')
    qtbot.addWidget(widget)
    return widget


def plotted(figure, index=0):
    """The numbers actually on screen for one curve."""
    x, y = figure.curves()[index].getData()
    return list(x), list(y)


def legendOf(figure):
    """The legend's labels, in the order the traces were drawn."""
    return [text.text for _, text in figure.pgPlotWidget.getPlotItem().legend.items]


def figureSubMenu(menu):
    """The 'Figure'/'Image' submenu the plot entries hang from."""
    for action in menu.actions():
        sub = action.menu()
        if sub is not None and sub.title() in ('Figure', 'Image'):
            return sub
    raise AssertionError('no figure submenu in %r'
                         % [action.text() for action in menu.actions()])


def popUpEntries(view, node):
    """The entries the right click offers at its top level, in the order shown.

    The node is equipped as the tree builder leaves a real one, because the whole
    pop-up is built here and not one entry at a time: the view the node belongs
    to, which the select/unselect command walks up to find, and the dictionary's
    default coordinates, which the coordinate1 entry reads. FakeAxesNode carries
    neither, because no other test of this file builds a menu.
    """
    node.dataTreeView = view
    node.default_coordinates = {}
    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).buildContextMenu(node)
    return [action.text() for action in menu.actions()]


# -- the element representation -------------------------------------------

@pytest.mark.ui
def test_an_element_fixes_the_arrays_the_tree_stands_on(figure):
    figure.plot(_leaf())

    assert figure.sliceControls.keys() == [RADIAL]
    assert legendOf(figure) == ['foo.profiles_1d[itime].ion[1].z_ion']


@pytest.mark.ui
def test_two_elements_of_one_array_answer_different_numbers(figure):
    """The defect, on a stub: one figure, two elements, two answers."""
    figure.plot(_leaf(ionIndex=0))
    figure.plot(_leaf(ionIndex=1))

    assert plotted(figure, 0)[1] == [1., 4.]
    assert plotted(figure, 1)[1] == [10., 40.]
    assert legendOf(figure) == ['foo.profiles_1d[itime].ion[0].z_ion',
                                'foo.profiles_1d[itime].ion[1].z_ion']


# -- the tensor representation --------------------------------------------

@pytest.mark.ui
def test_exploring_a_tensor_puts_every_pinned_axis_under_a_slider(figure):
    figure.plot(_leaf(), tensor=True)

    assert figure.exploresTensor is True
    assert figure.sliceControls.keys() == [ION, RADIAL]
    # Opened where the tree was standing, not at the first element: the figure
    # starts on the quantity the user clicked and walks away from it.
    assert figure.sliceControls.indices() == {ION: 1, RADIAL: 0}
    assert plotted(figure)[1] == [10., 40.]


@pytest.mark.ui
def test_moving_the_array_slider_walks_to_another_element(figure):
    figure.plot(_leaf(), tensor=True)

    figure.sliceControls.setIndex(ION, 0)

    assert plotted(figure)[1] == [1., 4.]
    # The legend follows the slider: a label naming the element the figure opened
    # on is wrong from the first move on.
    assert legendOf(figure) == ['foo.profiles_1d[itime].ion[0].z_ion']


@pytest.mark.ui
def test_keeping_a_curve_freezes_it_while_a_new_one_carries_on(figure):
    figure.plot(_leaf(), tensor=True)
    figure.sliceControls.setIndex(ION, 0)

    assert figure.keepCurve() == 1
    assert figure.curveCount() == 2

    figure.sliceControls.setIndex(ION, 1)

    # The kept trace stays at the indices it was frozen at; the live one moves.
    assert plotted(figure, 0)[1] == [1., 4.]
    assert plotted(figure, 1)[1] == [10., 40.]
    assert legendOf(figure) == ['foo.profiles_1d[itime].ion[0].z_ion',
                                'foo.profiles_1d[itime].ion[1].z_ion']


@pytest.mark.ui
def test_unkeeping_takes_the_frozen_curve_back_out(figure):
    figure.plot(_leaf(), tensor=True)
    figure.keepCurve()

    assert figure.curveCount() == 2
    assert figure.dropKeptCurve() == 0
    assert figure.curveCount() == 1
    # What is left is the live one, still answering the sliders.
    figure.sliceControls.setIndex(ION, 0)
    assert plotted(figure)[1] == [1., 4.]


@pytest.mark.ui
def test_unkeeping_with_nothing_kept_says_so_rather_than_failing_quietly(figure):
    figure.plot(_leaf(), tensor=True)

    with pytest.raises(ValueError) as raised:
        figure.dropKeptCurve()
    assert 'kept' in str(raised.value)

    figure.keepCurveBox.setChecked(False)
    assert figure.keptCount() == 0
    assert figure.curveCount() == 1


# -- the room a band takes -----------------------------------------------

@pytest.mark.ui
def test_a_band_of_several_rows_folds_to_one_line(figure):
    figure.plot(_leaf(), tensor=True)

    assert figure.sliceControls.isFolded() is True
    assert figure.sliceControls.sliceCount() == 2
    assert figure.sliceControls.summaryText() == 'ion 1 / 1   dimension 1 0 / 2'


@pytest.mark.ui
def test_a_folded_band_still_answers_the_read(figure):
    figure.plot(_leaf(), tensor=True)
    folded = figure.sliceControls.indices()

    assert figure.sliceControls.toggleFold() is True
    assert figure.sliceControls.indices() == folded
    assert [row.key for row in figure.sliceControls.rows()] == [ION, RADIAL]

    # And a slider moved while the band is shut moves the curve, because folding
    # is a visibility, never a rebuild.
    figure.sliceControls.toggleFold()
    figure.sliceControls.setIndex(ION, 0)

    assert plotted(figure)[1] == [1., 4.]


@pytest.mark.ui
def test_one_row_needs_no_summary_line(figure):
    # Folding is about the room several sliders take; a single slider is already
    # one line, and a summary of it would be a second.
    figure.plot(_inTheDynamicArrayOnly(), tensor=True)

    assert figure.sliceControls.keys() == []
    figure.plot(_leaf(), tensor=True)

    assert figure.sliceControls.keys() == [ION, RADIAL]
    assert figure.sliceControls.isFolded() is True


@pytest.mark.ui
def test_an_image_window_and_a_table_panel_keep_their_rows_open(qapp):
    """The band is the only place a picture says which slice it stands for.

    The manual makes those rows the saying of the colour scale and of the panel
    numbers, so folding them would take the answer away rather than the room.
    """
    image = ownership.keep(QVizImagePlot(title='SlicesImage1'))

    assert image.sliceControls.isFoldable() is False
    assert image.sliceControls.isFolded() is False


# -- the entry the two representations meet at ---------------------------

@pytest.fixture
def view(qapp):
    """One shot view and the api it reports its figures to, with an MDI area."""
    from PySide6.QtCore import QObject
    from PySide6.QtWidgets import QMdiArea

    from imasviz.Viz_API import Viz_API

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
    # The MDI area owns the windows the commands open, so it has to outlive the
    # call that builds it: the api holds it as its Qt parent.
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    return shot


@pytest.mark.ui
def test_the_entry_is_offered_when_a_curve_figure_has_an_array_to_pin(view):
    texts = popUpEntries(view, _leaf())

    assert EXPLORE in texts


@pytest.mark.ui
def test_the_entry_is_not_offered_when_there_is_nothing_to_walk(view):
    # A quantity held only by the dynamic array: the curve is already running
    # along it, so a slider for it would ask for what the abscissa shows.
    texts = popUpEntries(view, _inTheDynamicArrayOnly())

    assert EXPLORE not in texts
    assert QVizNodePlotting(_inTheDynamicArrayOnly()).tensorAxes() == []
    assert [axis.name for axis in QVizNodePlotting(_leaf()).tensorAxes()] == ['ion']


@pytest.mark.ui
def test_the_entry_answers_the_node_beside_the_time_entry(view):
    """Where the entry belongs: the pop-up's top level, next to the time entry.

    The two entries answer one question about the quantity -- run along time, or
    walk the arrays that hold it -- and neither answer needs a window picked. The
    submenu that lists windows is the one that asks which window, so an entry
    that opens a window of its own had no business hanging inside it, two levels
    down and below the figures it may join.
    """
    node = _leaf()
    texts = popUpEntries(view, node)

    assert texts.index(EXPLORE) == texts.index('Plot as function of time') + 1
    assert texts.index(EXPLORE) < texts.index('Plot z_ion to')

    # And it is not left behind in the submenu it came out of: one entry, one
    # place to find it.
    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).menuPlotCurrentSignalNode()
    assert not [action.text() for action in figureSubMenu(menu).actions()
                if action.text().startswith('Explore this tensor')]


@pytest.mark.ui
def test_the_entry_draws_a_figure_of_curves_under_sliders(view):
    QVizSignalHandling(dataTreeView=view, treeNode=_leaf()).exploreTensorCommand()

    frame = list(view.imas_viz_api.figureframes.values())[0]
    assert isinstance(frame, QVizCurvePlot)
    assert frame.exploresTensor is True
    assert frame.sliceControls.keys() == [ION, RADIAL]


@pytest.mark.ui
def test_a_picture_figure_refuses_to_explore_its_tensor_and_costs_no_window(view,
                                                                            caplog):
    # The axis an exploration would move is the one the pictures are spread over.
    caplog.clear()
    command = QVizPlotOneNode(dataTreeView=view, treeNode=_matrix(), tensor=True)

    assert command.execute() is None
    assert view.imas_viz_api.figureframes == {}
    assert any('matrix' in record.getMessage() for record in caplog.records)


# -- the defect, where it was measured ---------------------------------

IDS_NAME = 'magnetics'
OCCURRENCE = 0
ELEMENTS = 'magnetics.flux_loop[i].flux.data'
# The band's key for that array: an axis of the case, not one of the stubs.
FLUX_LOOP = (AOS, IDS_NAME, 'flux_loop')


@pytest.fixture(scope='module')
def session(qapp):
    """The reference case, its magnetics occurrence loaded, held for the module."""
    uri = case_uri_or_skip()
    if uri is None:
        pytest.skip('the reference case is not on disk')

    QVizPreferences().build()
    from imasviz.Viz_API import Viz_API

    api = Viz_API()
    source = QVizDataSourceFactory().create(uri)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    frame = api.CreateDataTree(source)
    view = frame.dataTreeView
    # The view and its api are what holds the loaded occurrence alive.
    ownership.keep(api)
    ownership.keep(view)
    ownership.keep(frame)
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                       occurrence=OCCURRENCE, asynch=False).execute()
    return {'view': view, 'api': api}


@pytest.mark.ui
@pytest.mark.case
@pytest.mark.dd
def test_two_elements_of_one_array_of_the_case_are_two_different_curves(session,
                                                                       qtbot):
    """What the probe measured, pinned: element 0 and element 1 are not the same.

    Drawn through the entry the shot view uses, so the figure, the read and the
    tree's own indices are all the real ones.
    """
    elements = [node for node in session['view'].signalsList
                if node.getParametrizedDataPath() == ELEMENTS]
    assert len(elements) >= 2, 'the case holds no two elements of that array'

    first = QVizPlotOneNode(dataTreeView=session['view'], treeNode=elements[0],
                            alongTime=True).execute()
    same = QVizPlotOneNode(dataTreeView=session['view'], treeNode=elements[1],
                           intoFigureKey=first.figureKey,
                           alongTime=True).execute()
    ownership.keep(first)
    assert same is first

    assert first.curveCount() == 2
    assert plotted(first, 0)[1] != plotted(first, 1)[1]
    # The array the tree fixed is written where the user can read it, and there
    # is no slider that would move it under either curve.
    assert first.sliceControls.keys() == []
    assert legendOf(first) == ['magnetics.flux_loop[0].flux.data',
                               'magnetics.flux_loop[1].flux.data']


@pytest.mark.ui
@pytest.mark.case
@pytest.mark.dd
def test_exploring_a_tensor_of_the_case_walks_the_elements_the_case_holds(session,
                                                                          qtbot):
    """The new entry, on the case the defect was measured on.

    The stubs say what a slider does to a read; this says what it does to the
    case: the figure opens on the element the tree was standing on, and walking
    the slider answers the very numbers that element's own curve answers -- read
    here through the other representation, in a figure of its own.
    """
    elements = [node for node in session['view'].signalsList
                if node.getParametrizedDataPath() == ELEMENTS]
    assert len(elements) >= 3, 'the case holds no three elements of that array'

    explored = QVizPlotOneNode(dataTreeView=session['view'], treeNode=elements[2],
                               alongTime=True, tensor=True).execute()
    ownership.keep(explored)

    assert explored.exploresTensor is True
    assert explored.sliceControls.keys() == [FLUX_LOOP]
    assert explored.sliceControls.indices() == {FLUX_LOOP: 2}
    # One array to walk is one row, and one row is already one line of the
    # window: a summary line on top of it would take a second.
    assert explored.sliceControls.isFolded() is False

    explored.sliceControls.setIndex(FLUX_LOOP, 0)
    walked = plotted(explored)[1]
    assert legendOf(explored) == ['magnetics.flux_loop[0].flux.data']

    reference = QVizPlotOneNode(dataTreeView=session['view'],
                                treeNode=elements[0], alongTime=True).execute()
    ownership.keep(reference)

    assert plotted(reference)[1] == walked
