# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The thumbnail the shot view shows for the node under the left click.

The panel used to answer only the questions it knew how to ask. The gesture
called it for a node the dictionary spelled dynamic or one-dimensional, so a
static matrix was never previewed at all; for anything else it returned without
clearing, so the previous node's curve stayed on screen under the previous
node's name -- measured on this checkout, clicking a text leaf left the profile
clicked before it still drawn. A quantity whose leaf ranked three was answered
'No preview available' although the read walks its axes, and the labels came
from the selection rather than from the node under the click.

What is pinned here is that the panel answers for every node it is handed: it
draws what the axes allow and says in one line what it left out, or it says why
nothing is drawn. The quantities it draws and the refusals it makes are checked
on stub nodes -- with no IDS behind them, so a refusal that read the shot first
would crash instead of answering. The drawn quantities hold their values in
memory, as in the image and curve figure tests: a filled quantity of three axes
needs several enclosing arrays of structures, and no reference case on this
checkout holds one. The two node shapes the tree shows for everything that is
not a quantity are checked on the reference case too, because only the builder
leaves them the way the panel meets them -- without a data path of their own.
"""

import numpy as np
import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea, QWidget

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPreviewPlot import QVizPreviewPlot, \
    CURVE, PICTURE, NOTHING
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.Viz_API import Viz_API

from support.caseTrees import (elementByTreePath, loadCaseTrees,
                               nodeAsTheBuilderBuildsIt)
from support.fakes import FakeAxesNode

TIMES = [0., 1., 2., 3., 4.]
RHO = [0.1, 0.2, 0.3, 0.4]
THETA = [0., 0.25, 0.5, 0.75, 1.]
PROFILES = 2
# The tree carries the second element of the dynamic array and of profiles_2d.
TIME_INDEX = 2
PROFILE_INDEX = 1


def densities(timeIndex, profile):
    return [1000. * timeIndex + 100. * profile + rank for rank in range(len(RHO))]


def psi(timeIndex, profile):
    return [[1000. * timeIndex + 100. * profile + 10. * radial + vertical
             for vertical in range(len(THETA))]
            for radial in range(len(RHO))]


def _ids():
    ids = type(str('StubIds'), (), {})()
    ids.ids_properties = type(str('Props'), (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = list(TIMES)
    # The leaf coordinates are spelled from the IDS, so they sit at IDS level.
    ids.rho_tor = list(RHO)
    ids.theta_poloidal = list(THETA)
    ids.matrix = [[1., 2., 3.], [4., 5., 6.]]
    ids.time_slice = []
    for timeIndex in range(len(TIMES)):
        timeSlice = type(str('TimeSlice'), (), {})()
        timeSlice.time = None
        timeSlice.major_radius = 6.2 + 0.01 * timeIndex
        timeSlice.profiles_1d = []
        timeSlice.profiles_2d = []
        for profile in range(PROFILES):
            oneD = type(str('Profiles1d'), (), {})()
            oneD.time = None
            oneD.electron_density = densities(timeIndex, profile)
            timeSlice.profiles_1d.append(oneD)
            twoD = type(str('Profiles2d'), (), {})()
            twoD.time = None
            twoD.psi = psi(timeIndex, profile)
            timeSlice.profiles_2d.append(twoD)
        ids.time_slice.append(timeSlice)
    return ids


def _profile():
    """One axis of its own, held by a dynamic array and a static one."""
    return FakeAxesNode(_ids(), 'foo', 'foo.time_slice[itime].profiles_1d[j]',
                        'FLT_1D', name='electron_density', units='m^-3',
                        itimeIndex=0, coordinates=('rho_tor',),
                        coordinateUnits={1: 'm'},
                        indices={'i': str(TIME_INDEX), 'j': str(PROFILE_INDEX)},
                        lengths={'i': str(len(TIMES)), 'j': str(PROFILES)})


def _matrix(values=None):
    """A static quantity at IDS level: two axes, nothing outside them.

    Nothing dynamic about it, which is exactly why the gesture never brought it
    to the panel: the gate asked the dictionary whether the leaf was dynamic or
    one-dimensional, and a static FLT_2D answered neither.
    """
    ids = _ids()
    ids.matrix = [[1., 2., 3.], [4., 5., 6.]] if values is None else values
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_2D', name='matrix',
                        coordinates=('1..N', '1..M'))


def _history():
    """One number per time slice: the only curve it allows is its history."""
    return FakeAxesNode(_ids(), 'foo', 'foo.time_slice[itime]', 'FLT_0D',
                        name='major_radius', units='m', itimeIndex=0,
                        indices={'i': str(TIME_INDEX)},
                        lengths={'i': str(len(TIMES))})


def _picture():
    """Three axes: the thumbnail draws two and pins one of each kind."""
    return FakeAxesNode(_ids(), 'foo', 'foo.time_slice[itime].profiles_2d[j]',
                        'FLT_2D', name='psi', units='Pa', itimeIndex=0,
                        coordinates=('rho_tor', 'theta_poloidal'),
                        coordinateUnits={1: 'm', 2: 'rad'},
                        indices={'i': str(TIME_INDEX), 'j': str(PROFILE_INDEX)},
                        lengths={'i': str(len(TIMES)), 'j': str(PROFILES)})


def makeNode(dataType, name='psi', path='time_slice[itime].profiles_1d',
             coordinates=('rho_tor_norm',), itimeIndex=0, aosCount=1,
             lengths=None, indices=None, idsName='equilibrium'):
    """A tree node as the builder leaves it, with no case and no IDS behind it.

    A refusal must cost no read: with idsRef left at None, a panel that asked
    the shot before deciding would raise instead of answering.
    """
    infoDict = {'IDSName': idsName, 'name': name, 'dataName': name,
                'data_type': dataType, 'occurrence': 0, 'isSignal': 1,
                'isStatic': 0, 'isSelected': 0, 'availableData': 1,
                'aos_parents_count': str(aosCount), 'Path': path + '.' + name}
    node = QVizTreeNode(None, [name], infoDict)
    # The walk spells a parametrized path for a leaf and for nothing else
    # (QVizIDSViewParser.buildLeaf), and the builder copies the attribute only
    # when the element carries it (QVizDataTreeViewBuilder.py:287). A structure
    # node handed to the panel with a path under it is a shape no shot view ever
    # shows -- and it is the shape that kept the refusal below green while every
    # left click on a folder of the tree raised TypeError.
    node.parametrizedPath = None
    if dataType not in ('structure', 'struct_array'):
        node.parametrizedPath = path or None
    node.itime_index = itimeIndex if path else None
    node.aos_parents_count = aosCount
    node.coordinates = list(coordinates)
    node.parameters_values = dict(indices or {})
    node.parameters_max_values = dict(lengths or {})
    return node


@pytest.fixture
def panel(qtbot):
    """The thumbnail docked in a shot view, as the frame docks it."""
    frame = QWidget()
    qtbot.addWidget(frame)
    preview = QVizPreviewPlot(parent=frame, title='Preview Plot')
    qtbot.addWidget(preview)
    # A Qt child does not keep its parent's Python wrapper alive, and a frame
    # collected with nothing holding it takes the panel down with it.
    preview.frame = frame
    return preview


@pytest.fixture
def view(qapp, panel):
    """Enough of the shot view for the gesture that asks for a preview.

    The shot view is a widget's child: the frame it sits in is where the docked
    thumbnail is looked for, so the stand-in has to carry that frame.
    """

    class FakeSource(QObject):
        def __init__(self, uri):
            super().__init__()
            self.uri = uri

    class FakeView(QObject):
        def __init__(self, frame):
            super().__init__()
            self.parent = frame
            self.uri = 'imas:hdf5?case=1'
            self.dataSource = FakeSource(self.uri)
            self.selectedItem = None
            self.selectedSignalsDict = {}
            self.imas_viz_api = Viz_API(parent=QMdiArea())

    view = FakeView(panel.parentWidget())
    # A figure needs an MDI area to be handed one; the thumbnail needs none.
    view.imas_viz_api.DTVlist = [view]
    return view


def click(view, panel, treeNode):
    """Ask for the preview the way the left click does, and say what came of it."""
    QVizSignalHandling(dataTreeView=view, treeNode=treeNode) \
        .plotPreviewSignalCommand()
    return panel


# ---------------------------------------------------------------------------
# What the panel draws.

def test_a_quantity_with_one_axis_of_its_own_becomes_a_curve(qapp, panel, view):
    node = _profile()
    assert click(view, panel, node).kind() == CURVE

    x, y = panel.curve()
    np.testing.assert_array_almost_equal(x, RHO)
    np.testing.assert_array_almost_equal(y, densities(TIME_INDEX, PROFILE_INDEX))
    axis = panel.curvePlot.getPlotItem().getAxis
    assert axis('bottom').labelText == 'rho_tor'
    assert axis('bottom').labelUnits == 'm'
    assert axis('left').labelText == 'electron_density[m^-3]'


def test_a_static_matrix_is_previewed(qapp, panel, view):
    # The gesture used to refuse this node before the panel saw it, so the panel
    # kept showing whatever the last accepted click had drawn.
    assert click(view, panel, _matrix()).kind() == PICTURE

    values, _ = panel.picture()
    np.testing.assert_array_equal(values, [[1., 2., 3.], [4., 5., 6.]])
    # Two axes to draw and no axis outside them: nothing was pinned.
    assert panel.sliceText() == ''


def test_a_number_held_by_the_dynamic_array_becomes_its_history(qapp, panel, view):
    # One number per time slice: the axes say there is nothing to draw against,
    # and the read along time is what turns it into a curve.
    assert click(view, panel, _history()).kind() == CURVE

    x, y = panel.curve()
    np.testing.assert_array_almost_equal(x, TIMES)
    np.testing.assert_array_almost_equal(y, [6.2 + 0.01 * k for k in
                                             range(len(TIMES))])
    assert panel.curvePlot.getPlotItem().getAxis('bottom').labelUnits == 's'


def test_a_quantity_of_three_axes_becomes_a_picture(qapp, panel, view):
    # The dictionary spells the leaf FLT_2D and one array of structures holds
    # it: three axes, and the legacy panel answered 'No preview available'.
    assert click(view, panel, _picture()).kind() == PICTURE

    values, _ = panel.picture()
    np.testing.assert_array_equal(values, psi(TIME_INDEX, PROFILE_INDEX))


def test_the_picture_says_which_element_of_every_other_axis_it_read(qapp, panel, view):
    # A thumbnail cannot carry the slice controls a figure carries, so the line
    # under it has to name what the picture stands for -- and it comes from the
    # tree, so naming it costs no extra read.
    click(view, panel, _picture())

    assert panel.sliceText() == 'time_slice %d, profiles_2d %d' % (TIME_INDEX,
                                                                   PROFILE_INDEX)


def test_the_labels_name_the_node_under_the_click_not_the_selection(qapp, panel, view):
    # The preview used to take its words from dataTreeView.selectedItem, so a
    # curve appeared under the name of a quantity the user had selected earlier.
    shot = view
    other = _history()
    shot.selectedItem = other

    click(shot, panel, _profile())

    assert panel.curvePlot.getPlotItem().getAxis('left').labelText != \
           'major_radius[m]'
    assert panel.curvePlot.getPlotItem().getAxis('left').labelText == \
           'electron_density[m^-3]'


# ---------------------------------------------------------------------------
# What the panel says when it draws nothing.

def test_a_text_leaf_takes_the_previous_thumbnail_away(qapp, panel, view):
    click(view, panel, _profile())
    assert panel.kind() == CURVE

    click(view, panel, makeNode('STR_1D', name='wall_component',
                                      path='time_slice[itime]'))

    assert panel.kind() == NOTHING
    assert panel.curve() == (None, None)
    assert 'text' in panel.reason()


def test_a_structure_says_it_is_not_a_quantity(qapp, panel, view):
    # Carrying no parametrized path is what the builder leaves a structure with,
    # so refusing it by naming it cannot ask for a data path it does not have.
    panel_result = click(view, panel,
                         makeNode('structure', name='profiles_1d',
                                  path='time_slice[itime]', coordinates=()))

    assert panel_result.kind() == NOTHING
    assert 'profiles_1d' in panel_result.reason()
    assert panel_result.curve() == (None, None)


def test_an_array_of_structures_says_it_is_not_a_quantity(qapp, panel, view):
    # The shape every left click on a folder of the tree takes: an element of a
    # dynamic array is a struct_array node, named by the dictionary, with no
    # path of its own.
    panel_result = click(view, panel,
                         makeNode('struct_array', name='time_slice',
                                  path='time_slice[itime]', coordinates=()))

    assert panel_result.kind() == NOTHING
    assert 'time_slice' in panel_result.reason()


def test_a_lone_number_says_what_it_is_not_drawn_against(qapp, panel, view):
    # A number with no axis around it: borrowing one from another quantity on a
    # figure is what a figure does, not what a thumbnail may invent.
    result = click(view, panel, makeNode('FLT_0D', name='major_radius',
                                               path='', coordinates=(),
                                               itimeIndex=-1, aosCount=0))

    assert result.kind() == NOTHING
    assert 'major_radius' in result.reason()


def test_a_quantity_with_more_axes_than_a_thumbnail_shows_says_so(qapp, panel, view):
    result = click(view, panel,
                   makeNode('FLT_3D', name='emission', path='',
                            coordinates=('1..N', '1..M', '1..7'), itimeIndex=-1,
                            aosCount=0))

    assert result.kind() == NOTHING
    assert 'figure' in result.reason()


def test_a_quantity_holding_nothing_says_so(qapp, panel, view):
    result = click(view, panel, _matrix(values=[]))

    assert result.kind() == NOTHING
    assert 'matrix' in result.reason()


# ---------------------------------------------------------------------------
# What the panel is not.

def test_the_thumbnail_carries_no_slider_for_a_read_to_answer_to(qapp, panel, view):
    # The panel used to be a legacy plot widget, so every read it made went
    # through a plot widget holding time-slider machinery -- the one path that
    # kept the old reader alive for a node nobody selected. It is a fact panel
    # now, not a frame of any kind: a frame is what a queued paint event can
    # kill, and this one is drawn, not plotted.
    assert not isinstance(panel, QVizCurvePlot)
    assert not hasattr(panel, 'sliderGroup')


# ---------------------------------------------------------------------------
# The two shapes the tree really shows for a node that is not a quantity.
#
# Measured on the reference case before this was pinned: every left click on a
# folder of the tree died in the panel. The stub above could not show it, because
# a stub built with a path under it is not what the builder hands over for a
# structure -- and the refusal names the node, which is where the missing path
# was asked for.


@pytest.fixture(scope='module')
def caseTree(qapp, request):
    return loadCaseTrees(qapp, ('equilibrium',), request=request)


def caseNode(caseTree, view, path):
    """The node the shot view shows under that path, as the builder leaves it."""
    element, walked = elementByTreePath(caseTree['trees']['equilibrium'],
                                        'equilibrium', path)
    return nodeAsTheBuilderBuildsIt(element, 'equilibrium',
                                    caseTree['runtime']['equilibrium'], view,
                                    path=walked)


@pytest.mark.ui
@pytest.mark.case
def test_the_element_of_a_dynamic_array_of_the_case_is_refused_by_name(qapp, panel,
                                                                       view, caseTree):
    node = caseNode(caseTree, view, 'equilibrium/time_slice(0)')
    assert node.getDataType() == 'struct_array'
    assert node.getParametrizedPath() is None

    click(view, panel, node)

    assert panel.kind() == NOTHING
    assert 'time_slice' in panel.reason()


@pytest.mark.ui
@pytest.mark.case
def test_a_structure_of_the_case_is_refused_by_name(qapp, panel, view, caseTree):
    node = caseNode(caseTree, view, 'equilibrium/time_slice(0)/profiles_1d')
    assert node.getDataType() == 'structure'
    assert node.getParametrizedPath() is None

    click(view, panel, node)

    assert panel.kind() == NOTHING
    assert 'profiles_1d' in panel.reason()
