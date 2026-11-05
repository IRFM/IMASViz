# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The tensor view offers the figures an open curve shares an abscissa with.

The report: a curve already open in a figure, and a tensor the right click
should be able to add to it while the two share an abscissa -- and in the
'Show only tensors (rank >= 1)' view there was **no entry pointing at the open
figure**, while the plain view offered it. The menu had taken the 'Plot <node>
to' window menu out of the tensor view on purpose (one tensor is one node
there), which left the quantity with the two abscissa items -- each opening a
*new* window -- and the 'Explore this tensor along <X>' heading, which is the
tensor representation of the *same quantity only where it has a heading for
that figure's abscissa*. A figure the quantity can run along, that already
holds another curve, then had no line in any menu: the overlap the plain view
offered under 'Plot <node> to -> Figure' was simply not there.

This file pins the window menu back: in the tensor view the pop-up offers
'Plot <node> to -> Figure -> New' and one line per open figure the quantity
can run along (the element representation, added as the element the tree
stands on), beside the 'Explore this tensor along <X>' heading and its own
lines (the tensor representation, with the arrays under sliders).

Nothing opens a case: the stub of test_64 answers the same shapes the case
does (dynamic array, array of structures, leaf coordinate), and the reference
case keeps no figure drawn on a coordinate the menu could not already offer.
"""

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea
try:
    from types import SimpleNamespace
except ImportError:  # pragma: no cover
    SimpleNamespace = None

from imasviz.Viz_API import Viz_API
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotOneNode import QVizPlotOneNode
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot

from support import ownership
from support.fakes import FakeAxesNode

ION = ('AOS', 'foo', 'ion')

IONS = {'z_ion': [[[1., 2., 3.], [10., 20., 30.]],
                  [[4., 5., 6.], [40., 50., 60.]]],
        'z_second': [[[7., 8., 9.], [70., 80., 90.]],
                     [[14., 15., 16.], [140., 150., 160.]]]}


def _ids(leafValues):
    """`ids.profiles_1d[k].ion[j].<leaf>`: one dynamic array, one static array.

    The dynamic array carries the clock (homogeneous_time 1, so the clock is
    `ids.time`), which is what makes the quantity run along time and along the
    leaf's own coordinate, the two abscissae the plain pop-up documents.
    """
    ids = type('StubIds', (), {})()
    ids.ids_properties = type('Props', (), {})()
    ids.ids_properties.homogeneous_time = 1
    ids.time = [0., 1.]
    shape = next(iter(leafValues.values()))
    ids.profiles_1d = []
    for index in range(len(shape)):
        slice_ = type('Slice', (), {})()
        slice_.time = None
        elements = []
        for element in range(len(shape[0])):
            held = type('Element', (), {})()
            for leaf, values in leafValues.items():
                setattr(held, leaf, values[index][element])
            elements.append(held)
        setattr(slice_, 'ion', elements)
        ids.profiles_1d.append(slice_)
    return ids


def _leaf(name='z_ion', ionIndex='1'):
    """An element of `ion`; the tree stands on that index in the plain view."""
    return FakeAxesNode(_ids(IONS), 'foo',
                        'foo.profiles_1d[itime].ion[j]', 'FLT_1D', name=name,
                        itimeIndex=0, coordinates=('1..N',),
                        indices={'i': '0', 'j': str(ionIndex)},
                        lengths={'i': '2', 'j': '2'})


def _equipped(view, node):
    """The attributes the tree builder puts on a real node, and a stub lacks."""
    if getattr(node, 'dataTreeView', None) is None:
        node.dataTreeView = view
    if not hasattr(node, 'default_coordinates'):
        node.default_coordinates = {}
    return node


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
    # outlive the trigger: the api holds it as its Qt parent.
    shot.mdi = QMdiArea()
    shot.imas_viz_api = Viz_API(parent=shot.mdi)
    shot.imas_viz_api.DTVlist = [shot]
    # The pop-up asks its catalog; an empty one keeps the test off the plugins
    # and their imports, which are not under test here.
    shot.pluginCatalog = SimpleNamespace(entriesFor=lambda node: [])
    return shot


def popUp(view, node):
    """The right click the pop-up is about, in the view it is asked of."""
    node = _equipped(view, node)
    return QVizSignalHandling(dataTreeView=view, treeNode=node).buildContextMenu(node)


def titles(menu):
    return [action.text() for action in menu.actions()]


def figureMenuOf(menu, node):
    """The 'Plot <node> to' window menu, the 'Figure' sub-menu, and its lines."""
    for action in menu.actions():
        if action.text() == 'Plot %s to' % node.getDataName() \
                and action.menu() is not None:
            for inner in action.menu().actions():
                if inner.text() == 'Figure' and inner.menu() is not None:
                    figure = inner.menu()
                    return action.menu(), figure, \
                        [a.text() for a in figure.actions()]
    raise AssertionError('no "Plot ... to -> Figure" in %r' % titles(menu))


def exploreMenuOf(menu, heading):
    for action in menu.actions():
        if action.text() == heading and action.menu() is not None:
            return [a.text() for a in action.menu().actions()]
    raise AssertionError('%r not in %r' % (heading, titles(menu)))


def openFigureAlongTime(view, node):
    """The open curve the report started from: an element, a figure of its own."""
    figure = QVizPlotOneNode(dataTreeView=view, treeNode=node).execute()
    assert isinstance(figure, QVizCurvePlot)
    ownership.keep(figure)
    return figure


@pytest.mark.ui
def test_the_tensor_offers_the_open_figure_to_the_element(view):
    """The overlap: the open figure is a line, in the tensor view as in the plain one.

    The figure holds `z_ion` as an element run along time; the node under the
    mouse can run along that very abscissa, so it is offered in the window menu
    -- the line the plain view has always offered, and the one the tensor view
    took out with the window menu.
    """
    figure = openFigureAlongTime(view, _leaf('z_ion'))
    node = _leaf('z_second')

    view.showOnlyTensorsRankGe1 = True
    menu = popUp(view, node)
    _, _, lines = figureMenuOf(menu, node)
    assert lines == ['New', figure.figureKey], lines

    # And the plain view offers the same line: the contrast that pins the
    # routing, and the shape the tensor view used to be missing.
    view.showOnlyTensorsRankGe1 = False
    lines = figureMenuOf(popUp(view, node), node)[2]
    assert lines == ['New', figure.figureKey], lines


@pytest.mark.ui
def test_the_tensor_view_line_draws_into_that_figure(view):
    """The line adds the element to the open figure; no second window is opened."""
    figure = openFigureAlongTime(view, _leaf('z_ion'))
    node = _leaf('z_second')
    before = list(view.imas_viz_api.figureframes)

    view.showOnlyTensorsRankGe1 = True
    menu = popUp(view, node)
    _, figureMenu, lines = figureMenuOf(menu, node)
    action = next(a for a in figureMenu.actions()
                  if a.text() == figure.figureKey)
    action.trigger()

    assert list(view.imas_viz_api.figureframes) == before
    assert figure.curveCount() == 2
    # The element keeps its element: the tree stood on ion[1] -- the values of
    # `z_second` at that element, read the way the figure runs along time.
    x, y = [curve.getData() for curve in figure.curves() if
            curve.name() == 'foo.profiles_1d[itime].ion[1].z_second'][0]
    assert list(y) == [70., 140.]


@pytest.mark.ui
def test_the_tensor_view_does_not_duplicate_the_abscissa_entries(view):
    """One menu, each entry once: the window menu joins, not repeats, the pop-up."""
    openFigureAlongTime(view, _leaf('z_ion'))
    node = _leaf('z_second')

    view.showOnlyTensorsRankGe1 = True
    menu = popUp(view, node)
    t = titles(menu)

    assert t.count('Plot as function of time') == 1, t
    assert t.count('Explore this tensor along time axis') == 1, t
    assert t.count('Plot as function of its index') == 1, t
    assert t.count('Plot %s to' % node.getDataName()) == 1, t
    # The order the plain view shows: the abscissa items, the tensor heading,
    # then the window menu they complement.
    assert t.index('Plot as function of time') < \
        t.index('Plot as function of its index')
    assert t.index('Explore this tensor along time axis') > \
        t.index('Plot as function of its index')
    assert t.index('Plot %s to' % node.getDataName()) > \
        t.index('Explore this tensor along time axis')


@pytest.mark.ui
def test_the_tensor_heading_offers_the_open_figure_in_both_views(view):
    """The tensor representation keeps offering the figure of its own abscissa."""
    figure = openFigureAlongTime(view, _leaf('z_ion'))
    node = _leaf('z_second')

    for tensorsOnly in (False, True):
        view.showOnlyTensorsRankGe1 = tensorsOnly
        lines = exploreMenuOf(
            popUp(view, node), 'Explore this tensor along time axis')
        assert lines == ['New', figure.figureKey], lines


@pytest.mark.ui
def test_a_figure_the_node_cannot_run_along_is_not_offered(view):
    """The abscissa gate answers for the figure, whatever view asks.

    The figure runs along an abscissa this quantity cannot run along, so it is
    a line of another window -- offered to a node that can run along it, not to
    this one.
    """
    figure = openFigureAlongTime(view, _leaf('z_ion'))
    figure.abscissa = ('coordinate', 'some other quantity\'s grid')
    node = _leaf('z_second')

    for tensorsOnly in (False, True):
        view.showOnlyTensorsRankGe1 = tensorsOnly
        _, _, lines = figureMenuOf(popUp(view, node), node)
        assert lines == ['New'], lines
