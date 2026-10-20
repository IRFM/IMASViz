# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a node lets the user do with it, read off its axes.

Right clicking a quantity opens the menu that decides whether it can be selected
and how it can be drawn. That decision used the dimension the data dictionary
spells on the leaf -- is0D, is1D, is2D, is2DOrLarger -- which is not the quantity:
the arrays of structures holding the leaf add axes of their own. So a quantity of
three axes answered "not two-dimensional", fell between the two branches of the
menu, and came out with no way to select it and no way to draw it -- while the
read walks those axes and draws it as a stack of pictures. A static two-dimension
leaf was not even selectable, because is2DOrLarger() only counts a quantity as
large when it is dynamic, and returns nothing at all when it is not.

The nodes here are real QVizTreeNodes with a hand-built infoDict, so the old
predicates answer for real and the defect is the menu's, not a stub's. The
quantities are named as the tree names them, with the enclosing arrays in the
parametrized path -- which is exactly the spelling the axes model reads.
"""

import pytest
from PySide6.QtWidgets import QMenu, QMdiArea

from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.Viz_API import Viz_API


def makeNode(dataType, name='psi', path='time_slice[itime].profiles_1d',
             coordinates=('rho_tor_norm',), itimeIndex=0, aosCount=1,
             lengths=None, indices=None, idsName='equilibrium', isSignal=1,
             isStatic=0):
    """A tree node as the tree builder leaves it: the dictionary spelling of one
    quantity, and the enclosing arrays of structures that give it its axes."""
    infoDict = {'IDSName': idsName, 'name': name, 'dataName': name,
                'data_type': dataType, 'occurrence': 0, 'isSignal': isSignal,
                'isStatic': isStatic, 'isSelected': 0, 'availableData': 1,
                'aos_parents_count': str(aosCount), 'Path': path + '.' + name}
    node = QVizTreeNode(None, [name], infoDict)
    node.parametrizedPath = path
    node.itime_index = itimeIndex if path else None
    node.aos_parents_count = str(aosCount)
    node.coordinates = list(coordinates)
    node.parameters_values = dict(indices or {})
    node.parameters_max_values = dict(lengths or {})
    return node


@pytest.fixture
def view(qapp):
    from PySide6.QtCore import QObject

    class FakeSource(QObject):
        name = 'NATIVE'

        def __init__(self, uri):
            super().__init__()
            self.uri = uri

        def dataKey(self, treeNode):
            # As QVizIMASDataSource.dataKey spells it: the selection is keyed by
            # it, and the menu now asks the selection whether this node is in it
            # instead of reading a flag the node keeps for itself.
            return (self.name + '::' + self.uri + '::' + treeNode.getPath() +
                    '::' + str(treeNode.getOccurrence()))

    class FakeView(QObject):
        def __init__(self):
            super().__init__()
            self.uri = 'imas:hdf5?case=1'
            self.dataSource = FakeSource(self.uri)
            self.selectedItem = None
            self.selectedSignalsDict = {}

    view = FakeView()
    view.imas_viz_api = Viz_API(parent=QMdiArea())
    view.imas_viz_api.DTVlist = [view]
    return view


def contextMenuEntries(qapp, view, node):
    """The titles of the entries the right click offers for this node."""
    view.selectedItem = node
    handling = QVizSignalHandling(dataTreeView=view, treeNode=node)
    menu = handling.buildContextMenu(node)
    return [action.text() for action in menu.actions()]


# ---------------------------------------------------------------------------
# The quantity, not the leaf spelling, decides what the menu offers.

def test_a_quantity_of_three_axes_can_be_drawn(qapp, view):
    # Two axes of its own inside the dynamic array: three to walk, and the read
    # draws them as pictures. The dictionary spells the leaf FLT_2D, which the
    # menu read as "a 2D array", offered the legacy image entry, and left the
    # quantity unselectable -- so it could never join a selection either.
    node = makeNode('FLT_2D', name='psi',
                    path='time_slice[itime].profiles_1d',
                    coordinates=('rho_tor_norm', 'z'),
                    indices={'i': '0'}, lengths={'i': 37})
    entries = contextMenuEntries(qapp, view, node)
    assert any('Plot' in entry for entry in entries), entries
    assert any('Select' in entry or 'Unselect' in entry for entry in entries), entries


def test_a_quantity_in_three_arrays_of_structures_can_be_drawn(qapp, view):
    # A scalar at the bottom of three arrays of structures is a rank 3 quantity:
    # each array is an axis. Nothing in the dictionary says so -- the leaf is
    # FLT_0D -- and the menu offered it nothing but the scalar entry, or nothing
    # at all when the enclosing arrays were not the dynamic one.
    node = makeNode('FLT_0D', name='power',
                    path='group[i].component[j].time_slice[itime]',
                    coordinates=(), itimeIndex=2, aosCount=3,
                    indices={'i': '0', 'j': '1', 'itime': '3'},
                    lengths={'i': 4, 'j': 6, 'itime': 100})
    entries = contextMenuEntries(qapp, view, node)
    assert any('Plot' in entry for entry in entries), entries
    assert any('Select' in entry or 'Unselect' in entry for entry in entries), entries


def test_a_static_two_dimension_leaf_can_be_selected(qapp, view):
    # is2DOrLarger() folds "dynamic" into "large": a static array is neither, so
    # this node fell into the branch written for curves and none of its gates
    # matched it. The user could look at it and do nothing with it.
    node = makeNode('FLT_2D', name='radiance',
                    path='channel[i1]', coordinates=('time', 'channel'),
                    itimeIndex=-1, aosCount=1, isSignal=0,
                    indices={'i': '0'}, lengths={'i': 38})
    entries = contextMenuEntries(qapp, view, node)
    assert any('Select' in entry or 'Unselect' in entry
               for entry in entries), entries


# ---------------------------------------------------------------------------
# The axes model answers the same questions, without reading the shot.

def test_the_rank_counts_the_arrays_that_hold_the_leaf(qapp):
    node = makeNode('FLT_1D', name='te',
                    path='source[i].time_slice[itime]',
                    coordinates=('rho_tor_norm',), itimeIndex=1, aosCount=2,
                    indices={'i': '0', 'itime': '5'}, lengths={'i': 12})
    assert QVizNodePlotting(node).rank() == 3


def test_a_scalar_with_nothing_around_it_is_not_plottable(qapp):
    # The read answers it with another quantity's abscissa, which is a line that
    # says nothing about this number: offering it would be a lie.
    node = makeNode('FLT_0D', name='ip', path='global_quantities',
                    coordinates=(), itimeIndex=-1, aosCount=0)
    plotting = QVizNodePlotting(node)
    assert plotting.rank() == 0
    assert plotting.isPlottable() is False


def test_text_is_never_plottable_however_many_axes_it_has(qapp):
    node = makeNode('STR_1D', name='name', path='time_slice[itime].profiles_1d',
                    coordinates=('rho_tor_norm',), indices={'i': '0'})
    plotting = QVizNodePlotting(node)
    assert plotting.rank() == 2
    assert plotting.isPlottable() is False


def test_the_coordinate_menu_stays_after_the_user_put_1_dot_N(qapp, view):
    # The dictionary spells an unbounded coordinate 1..N, and the axes model
    # turns it into no coordinate at all: it names no node to choose between.
    # The leaf still has an axis of its own, so the entry stays -- a menu that
    # disappears once the user has used it is a choice that cannot be undone.
    node = makeNode('FLT_1D', name='data', path='channel[i1]',
                    coordinates=('1..N',), itimeIndex=-1, aosCount=1,
                    indices={'i': '0'})
    plotting = QVizNodePlotting(node)
    assert plotting.hasOwnCoordinate()
    assert any('coordinate' in entry.lower()
               for entry in contextMenuEntries(qapp, view, node)), \
        contextMenuEntries(qapp, view, node)


def test_the_family_of_arrays_is_offered_whatever_the_leaf_spelling(qapp):
    # "Select all the signals from the same array" was gated on a 1D leaf: a
    # scalar held by an array belongs to that family just as much.
    scalar = makeNode('FLT_0D', name='beta', path='time_slice[itime]',
                      coordinates=(), indices={'i': '0'})
    matrix = makeNode('FLT_2D', name='psi', path='time_slice[itime]',
                      coordinates=('rho_tor_norm', 'z'), indices={'i': '0'})
    assert QVizNodePlotting(scalar).inArrayOfStructures()
    assert QVizNodePlotting(matrix).inArrayOfStructures()


def test_the_time_axis_is_read_from_the_axes_not_from_the_leaf_rank(qapp):
    # hasTimeAxis() used to test the three leaf ranks one by one and their
    # coordinate numbers by hand: a two-dimension leaf whose time sits in
    # coordinate 1 answered that it had no time axis.
    insideArray = makeNode('FLT_0D', name='ip', path='time_slice[itime]',
                           coordinates=(), indices={'i': '0'})
    coordinateIsTime = makeNode('FLT_2D', name='radiance', path='channel[i1]',
                                coordinates=('time_slice[itime].time', 'x'),
                                itimeIndex=0, aosCount=1, indices={'i': '0'})
    nowhere = makeNode('FLT_1D', name='lam', path='constant_1d',
                       coordinates=('rho_tor_norm',), itimeIndex=-1, aosCount=0)
    assert QVizNodePlotting(insideArray).hasTimeAxis()
    assert QVizNodePlotting(coordinateIsTime).hasTimeAxis()
    assert QVizNodePlotting(nowhere).hasTimeAxis() is False


# ---------------------------------------------------------------------------
# The shapes the legacy frames can still be asked to draw. They are a limit of
# the frames, not of the quantity: one slider group per figure, so a curve frame
# only ever drew a one-dimension leaf and an image frame a two-dimension one.

@pytest.mark.parametrize('dataType,path,coordinates,asCurve,asImage', [
    ('FLT_1D', 'time_slice[itime]', ('rho_tor_norm',), True, False),
    ('FLT_0D', 'time_slice[itime]', (), False, False),
    ('FLT_0D', 'constant_0d', (), False, False),
    ('FLT_2D', 'time_slice[itime].profiles_1d', ('rho_tor_norm', 'z'), False, True),
])
def test_what_the_legacy_frames_can_still_draw(qapp, dataType, path, coordinates,
                                               asCurve, asImage):
    node = makeNode(dataType, path=path, coordinates=coordinates,
                    itimeIndex=0 if 'itime' in path else -1,
                    indices={'i': '0'}, lengths={'i': 10})
    plotting = QVizNodePlotting(node)
    assert plotting.legacyCanDrawAsCurve() is asCurve
    assert plotting.legacyCanDrawAsImage() is asImage
