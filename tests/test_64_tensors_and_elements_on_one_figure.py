# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Superposing tensors, and adding an element to a figure that walks one.

A curve figure has one abscissa, and since T36 the figure answers whether a
quantity can be read along it. That answer is not enough for a tensor: a figure
that explores a tensor holds a band of sliders, one per array of structures it
leaves out of the curve, and those sliders drive **every** curve on the figure.
So a second tensor whose sliders would be *other* arrays is not the same picture
-- moving one slider would walk one curve and leave the other at the element the
tree stood on. Before this file, nothing even asked the question: the tensor
entry had no way to name an open figure, so exploring a tensor **always** opened
a new window, and an element added to a tensor figure kept a coordinate slider of
its own, so it moved under sliders the user was moving for another curve.

Four destinations, four rules -- all of them the figure's answer, all of them
asked of the same function the read uses to decide which axes it leaves out
(`QVizCurveAbscissa.axesLeftOut`), so the gate and the reading cannot drift:

    element -> figure        the abscissa (T36, unchanged)
    tensor -> figure         the abscissa **and** the arrays the figure holds; a
                             figure that holds none adopts the ones asked
    tensor -> tensor figure  the abscissa and **equal** array sets, else a refusal
                             that names both sets
    element -> tensor figure the abscissa and the same arrays -- and the element
                             is frozen on **all** of them: no slider, tensor or
                             coordinate, moves a curve asked for as one element

The entry says along *what* it explores (`Explore this tensor along time axis`),
because which arrays are left out depends on the abscissa the figure runs along:
`equilibrium.time_slice[i].profiles_1d.f` has nothing to explore along time --
the array is the curve -- and puts a slider on **time_slice** along `psi`, which
is the slider the manual promises and the old `tensorAxes()` hid, since it
excluded time arrays whatever the figure drew.

The shapes are built in memory, because the reference case holds no rank 3 leaf
with values in it and no leaf drawn along a coordinate other than time; the three
`case` tests pin the same rules on the numbers of the case, and the registry
(TESTING.md) says which shape only a stub can answer.
"""

import pytest

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea

from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode import QVizPlotOneNode
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizUtils import QVizPreferences

from conftest import CASE_DATA_DICTIONARY_VERSION, case_uri_or_skip
from support import ownership
from support.fakes import FakeAxesNode

AOS, LEAF = 'AOS', 'LEAF'
DYNAMIC = (AOS, 'foo', 'profiles_1d')
ION = (AOS, 'foo', 'ion')
COIL = (AOS, 'foo', 'coil')
RADIAL = (LEAF, 'foo', 'dimension 1')

EXPLORE = 'Explore this tensor along time axis'
# The same quantity read along its own coordinate instead: another abscissa, so
# another set of arrays left out of the curve, so another heading.
ALONG_INDEX = 'Explore this tensor along its index'

# Two time slices, two elements each, three points each. Two leaves of one array
# (`z_ion`, `z_second`) answer the superposition of two tensors; a second array
# (`coil`) answers the refusal.
IONS = {'z_ion': [[[1., 2., 3.], [10., 20., 30.]],
                  [[4., 5., 6.], [40., 50., 60.]]],
        'z_second': [[[7., 8., 9.], [70., 80., 90.]],
                     [[14., 15., 16.], [140., 150., 160.]]]}
COILS = {'voltage': [[[100., 200., 300.], [1000., 2000., 3000.]],
                     [[400., 500., 600.], [4000., 5000., 6000.]]]}


def _ids(aosName, leafValues):
    """`ids.profiles_1d[k].<aosName>[m].<leaf>`: a leaf held by two arrays.

    `homogeneous_time == 1` and a dynamic array of two slices, so the quantity
    has two abscissae -- the clock and its own coordinate -- which is what makes
    the arrays it leaves out depend on the figure it is drawn on.
    """
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    shape = next(iter(leafValues.values()))
    ids.profiles_1d = []
    for index in range(len(shape)):
        slice_ = type(str('Slice'), (), {})()
        slice_.time = None
        elements = []
        for element in range(len(shape[0])):
            held = type(str('Element'), (), {})()
            for leaf, values in leafValues.items():
                setattr(held, leaf, values[index][element])
            elements.append(held)
        setattr(slice_, aosName, elements)
        ids.profiles_1d.append(slice_)
    return ids


def _leaf(name='z_ion', ionIndex='1'):
    """An *element* of `ion`: the tree stands on that index."""
    return FakeAxesNode(_ids('ion', IONS), 'foo',
                        'foo.profiles_1d[itime].ion[j]', 'FLT_1D', name=name,
                        itimeIndex=0, coordinates=('1..N',),
                        indices={'i': '0', 'j': str(ionIndex)},
                        lengths={'i': '2', 'j': '2'})


def _coil(ionIndex='1'):
    """The same shape under **another** array: a tensor of other arrays."""
    return FakeAxesNode(_ids('coil', COILS), 'foo',
                        'foo.profiles_1d[itime].coil[j]', 'FLT_1D',
                        name='voltage', itimeIndex=0, coordinates=('1..N',),
                        indices={'i': '0', 'j': str(ionIndex)},
                        lengths={'i': '2', 'j': '2'})


@pytest.fixture
def figure(qtbot):
    widget = QVizCurvePlot(title='SlicesPlot1')
    qtbot.addWidget(widget)
    return widget


class _FakeSource(QObject):
    def __init__(self, uri):
        super().__init__()
        self.uri = uri
        self.name = 'NATIVE'

    def dataKey(self, treeNode):
        return treeNode.getParametrizedDataPath()


class _FakeView(QObject):
    """Enough of a shot view for a command and a context menu.

    The MDI area owns the windows the commands open, so it has to outlive the
    call that builds it: the api holds it as its Qt parent.
    """

    def __init__(self):
        super().__init__()
        from imasviz.Viz_API import Viz_API

        self.uri = 'imas:hdf5?case=1'
        self.dataSource = _FakeSource(self.uri)
        self.selectedItem = None
        self.selectedSignalsDict = {}
        self.mdi = QMdiArea()
        self.imas_viz_api = Viz_API(parent=self.mdi)
        self.imas_viz_api.DTVlist = [self]


@pytest.fixture
def view(qapp):
    return _FakeView()


def plotted(figure, index=0):
    """The numbers actually on screen for one curve."""
    x, y = figure.curves()[index].getData()
    return list(x), list(y)


def legendOf(figure):
    """The legend's labels, in the order the traces were drawn."""
    return [text.text for _, text in figure.pgPlotWidget.getPlotItem().legend.items]


def _equipped(view, node):
    """The attributes the tree builder puts on a real node, and a stub lacks.

    Needed by the whole pop-up, not by one entry: `QVizSelectNodes.viewOf` walks
    up through `parent()` to find the view, and the coordinate1 entry reads
    `default_coordinates`. Only answered when missing: on a node of the case,
    `default_coordinates` is the dictionary's own and overwriting it with an
    empty dict would change what the read draws.
    """
    if getattr(node, 'dataTreeView', None) is None:
        node.dataTreeView = view
    if not hasattr(node, 'default_coordinates'):
        node.default_coordinates = {}
    return node


def popUpEntries(view, node):
    """The entries the right click offers at its top level, in the order shown."""
    node = _equipped(view, node)
    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).buildContextMenu(node)
    return [action.text() for action in menu.actions()]


def subMenu(menu, title):
    """The sub-menu of the pop-up whose title starts with `title`."""
    for action in menu.actions():
        sub = action.menu()
        if sub is not None and sub.title().startswith(title):
            return sub
    raise AssertionError('no %r submenu in %r'
                         % (title, [action.text() for action in menu.actions()]))


def tensorEntries(view, node, heading=EXPLORE):
    """(the heading of one tensor entry, the lines under it) for a right click.

    The heading is asked for, because a quantity that can be read along two
    abscissae now gets one tensor entry each: the arrays a figure leaves out
    belong to the abscissa it runs against, so the two entries walk two slider
    sets and no single heading can name both.
    """
    node = _equipped(view, node)
    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).buildContextMenu(node)
    tensor = subMenu(menu, heading)
    return tensor.title(), [action.text() for action in tensor.actions()]


# -- two tensors on one figure -----------------------------------------

@pytest.mark.ui
def test_two_tensors_of_one_array_share_the_sliders_that_move_both(figure):
    """The superposition the user asked for: one band, both curves follow it."""
    figure.plot(_leaf('z_ion'), tensor=True)
    figure.plot(_leaf('z_second'), tensor=True)

    # One control per axis, not one per tensor: the arrays are the same arrays.
    assert figure.sliceControls.keys() == [ION, RADIAL]
    assert figure.curveCount() == 2
    assert plotted(figure, 0)[1] == [10., 40.]
    assert plotted(figure, 1)[1] == [70., 140.]

    figure.sliceControls.setIndex(ION, 0)
    assert plotted(figure, 0)[1] == [1., 4.]
    assert plotted(figure, 1)[1] == [7., 14.]
    # Both legends moved with the one slider, each naming its own quantity.
    assert legendOf(figure) == ['foo.profiles_1d[itime].ion[0].z_ion',
                                'foo.profiles_1d[itime].ion[0].z_second']


@pytest.mark.ui
def test_a_tensor_of_another_array_is_refused_by_name(figure):
    """The arrays are the figure's identity beside its abscissa.

    A curve of `coil` in a figure whose sliders walk `ion` would answer a
    different question: moving the slider would walk one curve and leave the
    other where the tree stood, which is exactly what "les axes soient les memes"
    refuses. The refusal names both sets, because "different axes" says nothing
    about which to change.
    """
    figure.plot(_leaf(), tensor=True)

    with pytest.raises(ValueError) as refused:
        figure.plot(_coil(), tensor=True)

    message = str(refused.value)
    assert 'coil' in message and 'ion' in message
    assert 'foo.profiles_1d[itime].coil[j].voltage' in message
    # And the refused quantity is not half drawn: the figure is what it was.
    assert figure.curveCount() == 1


@pytest.mark.ui
def test_a_tensor_of_other_arrays_costs_no_window(view, caplog):
    """Through the gesture: the reason is in the log, no empty window is left."""
    caplog.clear()
    first = QVizPlotOneNode(dataTreeView=view, treeNode=_leaf(),
                            tensor=True).execute()
    first.figureKey = 'SlicesPlot1'
    ownership.keep(first)

    refused = QVizPlotOneNode(dataTreeView=view, treeNode=_coil(),
                              intoFigureKey=first.figureKey,
                              tensor=True).execute()

    assert refused is None
    assert list(view.imas_viz_api.figureframes) == ['SlicesPlot1']
    assert first.curveCount() == 1
    assert any('coil' in record.getMessage() for record in caplog.records)


@pytest.mark.ui
def test_the_figure_keeps_which_arrays_it_holds(figure):
    """Both halves of the identity, settled by the first trace."""
    figure.plot(_leaf(), tensor=True)

    assert figure.walkingArrays == frozenset({ION})
    assert figure.accepts(_leaf('z_second'), tensor=True) is True
    assert figure.accepts(_leaf('z_second'), tensor=False) is True
    assert figure.accepts(_coil(), tensor=True) is False
    assert figure.accepts(_coil(), tensor=False) is False


# -- an element added to a figure that walks a tensor --------------------

@pytest.mark.ui
def test_an_element_added_to_a_tensor_figure_is_frozen_on_every_axis(figure):
    """The element does not move under the sliders that answer the tensor.

    Ni les tableaux ni la coordonnée ne le déplacent: it is pinned at the element
    the tree stands on, its own coordinate included, and its legend spells the
    whole index set -- the one thing on screen that says which element it is.
    """
    figure.plot(_leaf('z_ion'), tensor=True)
    figure.plot(_leaf(ionIndex=0), tensor=False)

    assert figure.sliceControls.keys() == [ION, RADIAL]
    assert [trace.isFrozen() for trace in figure.traces()] == [False, True]
    assert plotted(figure, 1)[1] == [1., 4.]
    assert legendOf(figure)[1] == 'foo.profiles_1d[itime].ion[0].z_ion'

    # The tensor walks, the element stays: that is what makes them comparable.
    figure.sliceControls.setIndex(ION, 1)
    assert plotted(figure, 0)[1] == [10., 40.]
    assert plotted(figure, 1)[1] == [1., 4.]
    assert legendOf(figure)[1] == 'foo.profiles_1d[itime].ion[0].z_ion'


@pytest.mark.ui
def test_an_element_of_other_arrays_is_refused_from_a_tensor_figure(figure):
    figure.plot(_leaf(), tensor=True)

    with pytest.raises(ValueError) as refused:
        figure.plot(_coil(), tensor=False)

    assert 'coil' in str(refused.value)
    assert figure.curveCount() == 1


# -- a tensor joining a figure of elements -----------------------------

@pytest.mark.ui
def test_a_tensor_joins_a_figure_that_pins_the_same_arrays(figure):
    """A figure of elements holds those arrays too, so the tensor is offered.

    The element keeps its own element -- it was asked as one -- and the tensor
    walks the array from there.
    """
    figure.plot(_leaf(ionIndex=0))
    assert figure.sliceControls.keys() == [RADIAL]

    figure.plot(_leaf('z_second'), tensor=True)

    assert figure.exploresTensor is True
    # The band keeps the axes in the order they first appeared, and the array the
    # element pinned by itself is now under a slider for the tensor to walk.
    assert figure.sliceControls.keys() == [RADIAL, ION]
    figure.sliceControls.setIndex(ION, 0)
    assert plotted(figure, 0)[1] == [1., 4.]
    assert plotted(figure, 1)[1] == [7., 14.]


@pytest.mark.ui
def test_the_gate_asks_the_figure_which_arrays_it_holds(figure, view):
    """`figureDrawsSameCurveAxis` answers the arrays as well as the abscissa."""
    from imasviz.Viz_API import Viz_API

    figure.figureKey = 'SlicesPlot1'
    figure.plot(_leaf(), tensor=True)
    api = Viz_API()
    api.figureframes['SlicesPlot1'] = figure

    assert api.figureDrawsSameCurveAxis('SlicesPlot1', _leaf('z_second'),
                                       tensor=True)
    assert not api.figureDrawsSameCurveAxis('SlicesPlot1', _coil(), tensor=True)
    # The element representation asks the same arrays: the figure's sliders would
    # otherwise walk an array that element does not belong to.
    assert not api.figureDrawsSameCurveAxis('SlicesPlot1', _coil(), tensor=False)

    plain = QVizCurvePlot(title='SlicesPlot2')
    plain.figureKey = 'SlicesPlot2'
    plain.plot(_leaf(ionIndex=0))
    api.figureframes['SlicesPlot2'] = plain
    # A figure whose band is empty has no arrays of its own yet: it accepts the
    # tensor and adopts its arrays, while the element keeps its own element. The
    # first tensor asked is what settles the band, and from then on the arrays
    # are asked of every trace.
    assert api.figureDrawsSameCurveAxis('SlicesPlot2', _leaf('z_second'),
                                        tensor=True)
    assert api.figureDrawsSameCurveAxis('SlicesPlot2', _coil(), tensor=True)
    plain.plot(_leaf('z_second'), tensor=True)
    assert plain.walkingArrays == frozenset({ION})
    assert not api.figureDrawsSameCurveAxis('SlicesPlot2', _coil(), tensor=True)
    assert not api.figureDrawsSameCurveAxis('SlicesPlot2', _coil(), tensor=False)


# -- what the entry offers ---------------------------------------------

@pytest.mark.ui
def test_the_entry_names_the_axis_it_explores_along(view):
    """The heading says along what, because the arrays depend on it."""
    heading, lines = tensorEntries(view, _leaf())

    assert heading == EXPLORE
    assert lines == ['New']


@pytest.mark.ui
def test_the_entry_offers_the_open_figures_whose_sliders_are_those_arrays(view):
    """A tensor is not tied to a new window: it joins the figures it fits."""
    first = QVizPlotOneNode(dataTreeView=view, treeNode=_leaf(),
                            tensor=True).execute()
    ownership.keep(first)

    heading, lines = tensorEntries(view, _leaf('z_second'))

    assert heading == EXPLORE
    assert lines == ['New', first.figureKey]


@pytest.mark.ui
def test_the_entry_hides_a_figure_whose_sliders_are_other_arrays(view):
    opened = QVizPlotOneNode(dataTreeView=view, treeNode=_leaf(),
                             tensor=True).execute()
    ownership.keep(opened)

    heading, lines = tensorEntries(view, _coil())

    assert heading == EXPLORE
    assert lines == ['New']


@pytest.mark.ui
def test_the_line_of_an_open_figure_draws_into_that_figure(view):
    opened = QVizPlotOneNode(dataTreeView=view, treeNode=_leaf(),
                             tensor=True).execute()
    ownership.keep(opened)
    handling = QVizSignalHandling(dataTreeView=view, treeNode=_leaf('z_second'))

    handling.exploreTensorCommand(intoFigureKey=opened.figureKey)

    assert list(view.imas_viz_api.figureframes) == [opened.figureKey]
    assert opened.curveCount() == 2
    assert opened.sliceControls.keys() == [ION, RADIAL]


@pytest.mark.ui
def test_an_element_is_offered_in_a_tensor_figure_by_the_figure_submenu(view):
    """The element representation keeps its menu; the arrays gate still applies."""
    opened = QVizPlotOneNode(dataTreeView=view, treeNode=_leaf(),
                             tensor=True).execute()
    ownership.keep(opened)

    node = _equipped(view, _leaf(ionIndex=0))
    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).menuPlotCurrentSignalNode()
    figureMenu = subMenu(menu, 'Figure')
    assert figureMenu.title() == 'Figure'
    assert [action.text() for action in figureMenu.actions()] == ['New',
                                                                 opened.figureKey]

    other = _equipped(view, _coil())
    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=other).menuPlotCurrentSignalNode()

    assert [action.text() for action in subMenu(menu, 'Figure').actions()] == \
        ['New']


@pytest.mark.ui
def test_the_entry_is_absent_when_there_is_nothing_to_walk(view):
    """A scalar of the dynamic array alone: the array *is* the curve."""
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
    only = FakeAxesNode(ids, 'foo', 'foo.profiles_1d[itime]', 'FLT_0D',
                        name='gap', itimeIndex=0, coordinates=(),
                        lengths={'i': '2'})

    assert EXPLORE not in popUpEntries(view, only)


@pytest.mark.ui
def test_a_figure_along_a_coordinate_walks_the_dynamic_array_it_left_out(view):
    """The slider the manual promises, and the entry that names it.

    On a figure drawn along the leaf's own coordinate, the dynamic array is no
    longer the curve: it is left out, so exploring the tensor puts a slider on
    it. `tensorAxes()` used to exclude time arrays whatever the figure drew,
    which hid the documented slider on the very figure the manual builds it on.

    Opened through the gesture, because the menu asks the api which figures are
    open: a frame built by hand is on screen but unknown to the pop-up.
    """
    figure = QVizPlotOneNode(dataTreeView=view, treeNode=_leaf(),
                             alongTime=False, tensor=True).execute()
    ownership.keep(figure)

    assert figure.abscissa == ('dimension', '')
    assert figure.sliceControls.keys() == [DYNAMIC, ION]
    assert figure.walkingArrays == frozenset({DYNAMIC, ION})
    # Slice 0, element 1: opened where the tree stood, and walking the dynamic
    # array reads another slice of the same element.
    assert plotted(figure)[1] == [10., 20., 30.]
    figure.sliceControls.setIndex(DYNAMIC, 1)
    assert plotted(figure)[1] == [40., 50., 60.]

    heading, lines = tensorEntries(view, _leaf('z_second'))
    # Along the clock the curve is the dynamic array, so only `ion` is left out
    # of it and the entry of its own has no figure to offer.
    assert heading == EXPLORE
    assert lines == ['New']

    # This figure runs along the index, so the dynamic array is left out of it
    # and it is offered under the heading that names *that* abscissa. The single
    # heading this used to answer could only reach it by suffixing the line with
    # an abscissa other than its own title -- the manual's slider on time_slice
    # was one click away from a window no entry could open.
    heading, lines = tensorEntries(view, _leaf('z_second'), ALONG_INDEX)
    assert heading == ALONG_INDEX
    assert lines == ['New', 'SlicesPlot1']


@pytest.mark.ui
def test_the_coordinate_heading_is_offered_before_any_figure_is_open(view):
    """The manual's slider, reachable from a bare right click.

    The heading along the coordinate used to need an open figure drawn along it,
    and no entry knew how to open one: the promise was unreachable from the tree.

    Triggered through the line of the menu, not by calling the slot: the abscissa
    the heading promises travels to the command in the connection the menu makes,
    and a slot called by hand with no opinion lets the figure settle on the clock
    under a heading naming the index.
    """
    def clickNew(heading, node):
        menu = QVizSignalHandling(dataTreeView=view,
                                 treeNode=_equipped(view, node)
                                 ).buildContextMenu(node)
        lines = subMenu(menu, heading).actions()
        assert lines[0].text() == 'New', [a.text() for a in lines]
        lines[0].trigger()
        return list(view.imas_viz_api.figureframes.values())[-1]

    frame = clickNew(ALONG_INDEX, _leaf())
    assert frame.abscissa == ('dimension', '')
    assert frame.sliceControls.keys() == [DYNAMIC, ION]

    # And the heading along the clock still opens one along the clock: two titles
    # cannot answer the same abscissa. The band it walks is the clock's own
    # leftovers -- `ion` and the leaf's coordinate -- which is what the entry
    # into an open figure along time pins above.
    frame = clickNew(EXPLORE, _leaf())
    assert frame.abscissa == ('time',)
    assert frame.sliceControls.keys() == [ION, RADIAL]


# -- the same rules, on the numbers of the case -------------------------

IDS_NAME = 'magnetics'
OCCURRENCE = 0
ELEMENTS = 'magnetics.flux_loop[i].flux.data'
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
    ownership.keep(api)
    ownership.keep(view)
    ownership.keep(frame)
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                       occurrence=OCCURRENCE, asynch=False).execute()
    return {'view': view, 'api': api}


def _leaves(view, path):
    """The nodes of one leaf, one per element of the array that holds it."""
    return [node for node in view.signalsList
            if node.getParametrizedDataPath() == path]


# A second leaf of the very same array, filled like the first: `flux_loop[i]`
# holds 17 elements of 17 344 samples for `flux.data` and for
# `flux.data_error_upper`, while `voltage.data` and `flux.time` answer **0**
# samples on this shot -- a tensor of those is refused by the read ("no values
# along the plotted axis"), so they cannot stand for a superposition.
SECOND = 'magnetics.flux_loop[i].flux.data_error_upper'
# Another array of the same IDS, 130 elements: the refusal.
OTHER_ARRAY = 'magnetics.bpol_probe[i].field.data'

# Measured on the case, element 2 of `flux_loop`, the three first samples of the
# curve -- and the three of element 5, which is what one slider step of 3 answers.
FLUX2 = [0.003595616202801466, -0.0019612452015280724, 0.002288119401782751]
FLUX5 = [0.005566614214330912, 0.006876405794173479, 0.008513645268976688]
ERROR2 = [0.009999999776482582] * 3
FLUX0 = [0.006196762900799513, 0.001956872409209609, 0.006196762900799513]


@pytest.mark.ui
@pytest.mark.case
@pytest.mark.dd
def test_two_tensors_of_one_array_of_the_case_move_on_one_slider(session):
    """The superposition, on the numbers of the case.

    Two quantities of one array of structures, each explored as a tensor: one
    band of controls, and the one slider walks both curves -- which is what the
    figure's sliders are for, and what a figure of *other* arrays could not do.
    """
    view = session['view']
    flux = _leaves(view, ELEMENTS)
    assert len(flux) == 17, 'the case holds 17 elements of that array'

    figure = QVizPlotOneNode(dataTreeView=view, treeNode=flux[2],
                             tensor=True).execute()
    ownership.keep(figure)
    assert figure.sliceControls.keys() == [FLUX_LOOP]
    assert figure.sliceControls.indices() == {FLUX_LOOP: 2}

    same = QVizPlotOneNode(dataTreeView=view,
                           treeNode=_leaves(view, SECOND)[2],
                           intoFigureKey=figure.figureKey,
                           tensor=True).execute()
    assert same is figure
    assert figure.curveCount() == 2
    # Still one control, not one per tensor: the arrays are the same arrays.
    assert figure.sliceControls.keys() == [FLUX_LOOP]
    assert figure.walkingArrays == frozenset({FLUX_LOOP})
    assert plotted(figure, 0)[1][:3] == FLUX2
    assert plotted(figure, 1)[1][:3] == ERROR2

    figure.sliceControls.setIndex(FLUX_LOOP, 5)
    assert plotted(figure, 0)[1][:3] == FLUX5
    assert [t.isFrozen() for t in figure.traces()] == [False, False]
    assert legendOf(figure) == ['magnetics.flux_loop[5].flux.data',
                                'magnetics.flux_loop[5].flux.data_error_upper']


@pytest.mark.ui
@pytest.mark.case
@pytest.mark.dd
def test_an_element_of_the_case_added_to_a_tensor_figure_does_not_move(session):
    """The element stays at its own element while the tensors walk away.

    Its legend is the only place on screen saying which element it is, so it has
    to spell the index the tree stood on and keep spelling it.
    """
    view = session['view']
    flux = _leaves(view, ELEMENTS)
    figure = QVizPlotOneNode(dataTreeView=view, treeNode=flux[2],
                             tensor=True).execute()
    ownership.keep(figure)

    element = QVizPlotOneNode(dataTreeView=view, treeNode=flux[0],
                              intoFigureKey=figure.figureKey).execute()
    assert element is figure
    assert figure.curveCount() == 2
    assert [t.isFrozen() for t in figure.traces()] == [False, True]
    assert plotted(figure, 1)[1][:3] == FLUX0
    assert legendOf(figure) == ['magnetics.flux_loop[2].flux.data',
                                'magnetics.flux_loop[0].flux.data']

    figure.sliceControls.setIndex(FLUX_LOOP, 9)
    assert plotted(figure, 0)[1][:3] != FLUX0
    assert plotted(figure, 1)[1][:3] == FLUX0
    assert legendOf(figure) == ['magnetics.flux_loop[9].flux.data',
                                'magnetics.flux_loop[0].flux.data']


@pytest.mark.ui
@pytest.mark.case
@pytest.mark.dd
def test_a_tensor_of_another_array_of_the_case_is_refused_by_name(session,
                                                                  caplog):
    """The refusal, the gate and the menu, on the case the rules were measured on.

    `flux_loop` and `bpol_probe` are two arrays of one IDS: their curves share
    the clock, so the abscissa alone would let them pile up -- and the one slider
    of the figure would then walk one curve and leave the other at its element.
    """
    caplog.clear()
    view = session['view']
    figure = QVizPlotOneNode(dataTreeView=view,
                             treeNode=_leaves(view, ELEMENTS)[2],
                             tensor=True).execute()
    ownership.keep(figure)
    other = _leaves(view, OTHER_ARRAY)
    assert len(other) == 130, 'the case holds 130 elements of that array'

    assert view.imas_viz_api.figureDrawsSameCurveAxis(figure.figureKey,
                                                      other[0], tensor=True) \
        is False
    assert view.imas_viz_api.figureDrawsSameCurveAxis(figure.figureKey,
                                                      other[0]) is False

    refused = QVizPlotOneNode(dataTreeView=view, treeNode=other[3],
                              intoFigureKey=figure.figureKey,
                              tensor=True).execute()

    assert refused is None
    assert figure.curveCount() == 1
    assert any('bpol_probe' in record.getMessage() and 'flux_loop' in
               record.getMessage() for record in caplog.records)

    # And the menu does not offer what the frame would refuse. The session of
    # this module holds the three figures its case tests opened, all three walking
    # `flux_loop`, so all three are offered -- and the node of another array is
    # offered none, which is the half that carries the rule.
    heading, lines = tensorEntries(view, _leaves(view, SECOND)[3])
    assert heading == EXPLORE
    assert lines == ['New', 'SlicesPlot1', 'SlicesPlot2', 'SlicesPlot3']
    heading, lines = tensorEntries(view, other[0])
    assert lines == ['New']
