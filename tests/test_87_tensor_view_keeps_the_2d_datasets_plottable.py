# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The 'Show only tensors (rank >= 1)' view keeps a 2D dataset plottable.

The tensor view keeps a quantity the moment it owns an axis of its own -- which
is exactly what a 2-dimension dataset is -- so the leaf is still in the tree.
What went missing was the pop-up: its tensor branch offered one plot entry,
'Explore this tensor', and that entry refuses a quantity with two axes of its
own by name, because it is an image, not a curve, and has no abscissa a curve
figure can run along. The menu then had an entry to select the dataset and
nothing to draw it.

The routing is fixed: a plottable quantity without a curve abscissa goes to the
same entry the plain view hands it -- 'Plot <node> to -> Image -> New' -- so a
dataset the view keeps in the tree can still be traced there. A quantity that
runs along a curve keeps its abscissa items ('Plot as function of time', and
the coordinate one beside it) and the tensor entry, and loses the
'Plot <node> to' menu -- the view shows one node per tensor, and the tensor's
own entry opens the window it fills.

Nothing opens a case: a two-dimension leaf with values needs enclosing arrays
the reference case does not fill, so the quantities live in memory, as in the
plot-routing and one-node tests.
"""

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea
try:
    from types import SimpleNamespace
except ImportError:  # pragma: no cover
    SimpleNamespace = None

import numpy as np

from imasviz.Viz_API import Viz_API
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot

from support.fakes import FakeAxesNode


def _idsWith(name, values):
    """A minimal IDS: no homogeneous time base except the clock, no arrays."""
    ids = type('StubIds', (), {})()
    ids.ids_properties = type('Props', (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0.]
    ids.rho_tor = [0.0, 1.0, 2.0]
    setattr(ids, name, values)
    return ids


def attach(node, view):
    """The view a node belongs to, as the tree sets it on every node it builds.

    The selection entry walks `dataTreeView` off the node to find its view, so a
    stub that is handed a menu without it dies in `QVizSelectNodes.viewOf`.
    """
    node.dataTreeView = view
    return node


def _matrix():
    """Two axes of its own and nothing around them: a picture, not a curve."""
    ids = _idsWith('matrix', [[1., 2., 3.], [4., 5., 6.]])
    return FakeAxesNode(ids, 'foo', 'foo', 'FLT_2D', name='matrix',
                        coordinates=('1..N', '1..M'))


def _vector():
    """One axis of its own in the dynamic array: a curve, and a tensor to walk."""
    ids = type('StubIds', (), {})()
    ids.ids_properties = type('Props', (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1., 2.]
    ids.time_slice = []
    for t in (0., 1., 2.):
        one = type('Slice', (), {})()
        one.time = t
        one.z = [float(t), float(t) + 1., float(t) + 2.]
        ids.time_slice.append(one)
    return FakeAxesNode(ids, 'foo', 'foo.time_slice[itime]', 'FLT_1D',
                        name='z', itimeIndex=0, units='m',
                        coordinates=('rho_tor',),
                        indices={'i': '0'}, lengths={'i': '3'})


@pytest.fixture
def view(qapp):
    """One shot view and api enough for a menu and a draw, without a case."""

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
    # The MDI area owns the window a triggered entry opens, so it has to
    # outlive the draw: the api holds it as its Qt parent.
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    # The pop-up asks its catalog; an empty one keeps the test off the plugins
    # and their imports, which is not under test here.
    shot.pluginCatalog = SimpleNamespace(entriesFor=lambda node: [])
    return shot


def submenu(menu, title):
    """The sub-menu of `title` in `menu`, as the user would open it."""
    for action in menu.actions():
        if action.text() == title and action.menu() is not None:
            return action.menu()
    raise AssertionError('%r has no %r sub-menu: %r'
                         % (title, menu, [a.text() for a in menu.actions()]))


def plotToMenu(menu):
    """The top-level 'Plot <node> to' entry of the pop-up, whatever node it is."""
    for action in menu.actions():
        if action.text().startswith('Plot ') and action.text().endswith(' to'):
            return action.menu()
    raise AssertionError('no "Plot ... to" entry in %r'
                         % [a.text() for a in menu.actions()])


def imageNew(menu):
    """The 'Image' -> 'New' action the menu would offer for a 2D dataset."""
    image = plotToMenu(menu)
    # 'Plot X to' nests the frame kind as a sub-menu, the leaf as an action.
    for action in image.actions():
        if action.text() == 'Image' and action.menu() is not None:
            for inner in action.menu().actions():
                if inner.text() == 'New':
                    return inner
    raise AssertionError('no "Image -> New" under %r'
                         % [a.text() for a in image.actions()])


# --------------------------------------------------------------------------
# What the tensor view offers for a 2D dataset
# --------------------------------------------------------------------------

def test_the_tensor_view_still_offers_to_draw_a_2d_dataset(view):
    """An entry to trace the dataset, on a leaf the view kept in the tree."""
    node = attach(_matrix(), view)
    view.showOnlyTensorsRankGe1 = True

    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).buildContextMenu(node)

    # The selection is still there -- the leaf is a tensor as far as the tree is
    # concerned -- and now so is something that draws it.
    assert [a.text() for a in menu.actions()
            if a.text().startswith('Select ') or a.text().startswith('Unselect ')]
    imageNew(menu)


def test_the_tensor_view_entry_draws_the_2d_dataset(view):
    """The entry the menu offers traces the dataset into an image figure."""
    node = attach(_matrix(), view)
    view.showOnlyTensorsRankGe1 = True

    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).buildContextMenu(node)
    imageNew(menu).trigger()

    pictures = [frame for frame in view.imas_viz_api.figureframes.values()
                if isinstance(frame, QVizImagePlot)]
    assert len(pictures) == 1, view.imas_viz_api.figureframes
    np.testing.assert_array_equal(pictures[0].images()[0].image,
                                  [[1., 2., 3.], [4., 5., 6.]])


def test_the_plain_view_still_offers_the_same_entry(view):
    """The plain view was never broken: the contrast that pins the routing."""
    node = attach(_matrix(), view)
    view.showOnlyTensorsRankGe1 = False

    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).buildContextMenu(node)

    imageNew(menu)


# --------------------------------------------------------------------------
# What the tensor view offers a curve
# --------------------------------------------------------------------------

def test_the_tensor_view_keeps_the_explore_entry_for_a_curve(view):
    """A tensor that runs along a curve keeps the tensor entry, and its abscissae.

    The same branch that lost the 2D dataset had to keep what it was made for:
    a curve with an array around it gets 'Explore this tensor along ...'. The
    abscissa items come back with it -- the view shows one node per tensor, but
    the tensor still has a clock to run against and a coordinate to run along
    -- and what stays out is the 'Plot z to' menu, which asks which window the
    node should go into: the tensor's own entry opens the window it fills.
    """
    node = attach(_vector(), view)
    view.showOnlyTensorsRankGe1 = True

    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).buildContextMenu(node)

    titles = [a.text() for a in menu.actions()]
    assert [t for t in titles if t.startswith('Explore this tensor along')], \
        titles
    assert 'Plot as function of time' in titles, titles
    assert 'Plot as function of rho_tor' in titles, titles
    # Side by side, before the tensor heading, as in the plain view.
    assert titles.index('Plot as function of time') == \
        titles.index('Plot as function of rho_tor') - 1
    assert 'Plot z to' not in titles, titles


# --------------------------------------------------------------------------
# What the tensor view no longer offers
# --------------------------------------------------------------------------

AOS_ENTRY = 'Select all nodes from the same AOS'


def test_the_tensor_view_does_not_offer_to_select_a_family_it_does_not_show(view):
    """The family of an AOS is one node here: the per-node entry is the whole of it.

    The view keeps the first element of each structure array and takes the rest
    out of the tree, so the family a 'Select ... from the same AOS' gestures at
    is the node itself -- an entry that duplicates 'Select <node>' and promises
    to select the elements the view took away.
    """
    node = attach(_vector(), view)
    view.showOnlyTensorsRankGe1 = True

    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).buildContextMenu(node)
    titles = [a.text() for a in menu.actions()]

    assert AOS_ENTRY not in titles, titles
    # The per-node entry stays: the leaf is a tensor as far as the tree is
    # concerned, and it is the only entry that acts on it there.
    assert [t for t in titles if t.startswith('Select ') and t != AOS_ENTRY], \
        titles
    assert [t for t in titles if t.startswith('Explore this tensor along')], \
        titles


def test_the_plain_view_keeps_offering_the_aos_family(view):
    """The same leaf on the plain tree shows its family on screen: the entry means."""
    node = attach(_vector(), view)
    view.showOnlyTensorsRankGe1 = False

    menu = QVizSignalHandling(dataTreeView=view,
                              treeNode=node).buildContextMenu(node)
    titles = [a.text() for a in menu.actions()]
    assert AOS_ENTRY in titles, titles
