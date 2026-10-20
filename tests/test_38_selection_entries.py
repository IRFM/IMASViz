# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Node selection: one record, and the tree coloured from it.

The four gestures under "Select <node>", "Select all nodes from the same AOS"
and "Unselect Nodes → This / All IMAS Databases" wrote the selection twice: into
``dataTreeView.selectedSignalsDict`` -- which is what every frame built since T3
reads -- and into the node's own ``infoDict['isSelected']``, and they coloured the
tree from the second. Measured on real tree items, the two records drift apart and
the tree then lies to the user:

* an entry could hold the wrong node. ``QVizSelectSignal`` keyed the entry by the
  node it was asked for but stored ``dataTreeView.selectedItem`` in it -- the
  node the tree happened to be pointed at. Measured: asking to select ``a`` while
  the tree was on ``b`` left one entry, keyed for ``a``, holding **b**; a plot of
  that selection would draw b and never a.
* unselecting coloured the wrong item. ``QVizSelectOrUnselectSignal`` recoloured
  ``selectedItem`` too: measured on three selected nodes, asking to unselect ``a``
  while the tree was on ``b`` left ``a`` red and turned ``b`` blue -- a selected
  node shown as unselected and an unselected one shown as selected.
* the flag and the dictionary disagreed, and the menu followed the flag. With the
  node flagged and the dictionary not holding it, the entry read "Unselect a..."
  and triggering it raised ``KeyError``, leaving the flag set: the node could not
  be unselected, and could not be selected either.
* the order recorded for the user's clicks was off by one -- three clicks left
  ``-1, 0, 1``.
* "Select all nodes from the same AOS" matched a regular expression over the
  display path -- every bracketed run removed. Asked on ``core/time_slice(0)/a``
  in a view holding five nodes, it took three: the other structure element (right),
  and ``core/time_slice(0)/a`` of the **second occurrence** of the IDS, which the
  user never touched. Asked a second time it re-added what was already selected
  and overwrote its place: every entry ended up recorded with index 2. And it
  wrote ``dataTreeView.selectedItem`` for every node it walked, leaving the tree
  pointed at whatever its loop touched last.
* "Unselect All" walked the whole signal list of the view for every selected node,
  comparing dictionaries, then deleted by counting on the wrong list: with three
  selected nodes and one the tree no longer listed, it raised ``IndexError`` after
  dropping two, leaving the third selected and red.

The parametrized path is what replaces the regex: ``QVizIDSViewParser``:388 spells
it with the index *names* (``core.time_slice[i].a``, the time index as ``[itime]``),
so the elements of one array of structures share it and two different structures do
not -- which is the family, read off the structure rather than off a display
string. Nothing here opens a case: selecting is about tree items and their
dictionary, and the nodes are built with the ``itemDataDict`` the tree builder
writes.
"""

import pytest
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMdiArea

from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
    import QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectSignals \
    import QVizSelectSignals
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable import QVizPlotAsTable
from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.Viz_API import Viz_API
from imasviz.VizUtils import QVizPreferences

URI = 'imas:hdf5?case=1'

# The tree colours a selected label with the preference colour, so a test that
# reads a label has to know what that colour is. The application builds these at
# startup from $HOME/.imasviz/preferences.
QVizPreferences().build()


class FakeSource(QObject):
    """A data source keying a selection entry the way the real one does."""

    name = 'NATIVE'
    uri = URI

    def dataKey(self, treeNode):
        # Verbatim from QVizIMASDataSource.dataKey:299: the occurrence is part of
        # the key, which is what lets two occurrences of one IDS hold the same
        # path without sharing a selection entry.
        return self.name + '::' + self.uri + '::' + treeNode.getPath() + \
            '::' + str(treeNode.getOccurrence())


@pytest.fixture
def view(qapp):
    """One shot view with a selection, and the api its sibling views share."""

    class FakeView(QObject):
        def __init__(self):
            super().__init__()
            self.uri = URI
            self.dataSource = FakeSource()
            self.selectedItem = None
            self.selectedSignalsDict = {}
            self.signalsList = []
            self.ids_roots_occurrence = {'core/0': True}
            # The api's Qt parent outlives the call: an unnamed temporary takes
            # the api down with it.
            self.mdi = QMdiArea()
            self.imas_viz_api = Viz_API(parent=self.mdi)
            self.imas_viz_api.DTVlist = [self]

    return FakeView()


def leaf(path, parametrized, occurrence=0):
    """A plottable leaf as the tree builder leaves it.

    ``parametrized`` is spelled the way the view parser spells it -- index names,
    not indices -- because that is what makes two elements of one array of
    structures one family.
    """
    name = path.rsplit('/', 1)[-1]
    infoDict = {'IDSName': 'core', 'name': name, 'dataName': name,
                'data_type': 'FLT_1D', 'occurrence': occurrence,
                'isSignal': 1, 'isStatic': 0, 'availableData': 1,
                'aos_parents_count': '1', 'Path': path}
    node = QVizTreeNode(None, [name], infoDict)
    node.parametrizedPath = parametrized
    node.coordinates = ['rho_tor']
    return node


def _a():
    return leaf('core/time_slice(0)/a', 'core.time_slice[i].a')


def _a_of_other_element():
    return leaf('core/time_slice(1)/a', 'core.time_slice[i].a')


def _a_of_other_occurrence():
    return leaf('core/time_slice(0)/a', 'core.time_slice[i].a', occurrence=1)


def _b():
    return leaf('core/time_slice(0)/b', 'core.time_slice[i].b')


def _a_of_other_aos():
    return leaf('core/profiles_1d(0)/a', 'core.profiles_1d[i].a')


def fill(view, *nodes):
    view.signalsList = list(nodes)
    return view


def select(view, node):
    """The manual's one-by-one gesture, as the node menu fires it."""
    view.selectedItem = node
    QVizSignalHandling(view, node).selectOrUnselectSignal()


def labelColours(*nodes):
    """Which labels the user would read as selected."""
    return ['selected' if node.foreground(0) == QVizPreferences.SelectionColor
            else 'other' for node in nodes]


def pathsInSelection(view):
    return [entry['QTreeWidgetItem'].getPath()
            for entry in view.selectedSignalsDict.values()]


def indexesInSelection(view):
    return [entry['index'] for entry in view.selectedSignalsDict.values()]


def entryFor(view, node):
    return view.selectedSignalsDict[view.dataSource.dataKey(node)]


# ---------------------------------------------------------------------------
# One node: the dictionary is the record, and the label follows it.

@pytest.mark.ui
def test_one_click_selects_the_node_the_menu_was_built_on(view):
    fill(view, _a())
    node = view.signalsList[0]

    select(view, node)

    assert pathsInSelection(view) == ['core/time_slice(0)/a']
    assert entryFor(view, node)['QTreeWidgetItem'] is node
    assert entryFor(view, node)['uri'] == URI


@pytest.mark.ui
def test_the_clicks_are_recorded_in_the_order_they_came(view):
    # Measured on the legacy commands: three clicks were recorded -1, 0, 1.
    fill(view, _a(), _b())

    for node in view.signalsList:
        select(view, node)

    assert indexesInSelection(view) == [0, 1]


@pytest.mark.ui
def test_the_label_of_the_asked_node_goes_red(view):
    fill(view, _a(), _b())
    node = view.signalsList[0]

    select(view, node)

    assert labelColours(*view.signalsList) == ['selected', 'other']


@pytest.mark.ui
def test_the_node_recorded_is_the_one_asked_and_not_the_trees_current_item(view):
    # Measured: the entry was keyed for a and held b, because the command stored
    # dataTreeView.selectedItem instead of the node it was handed.
    fill(view, _a(), _b())
    wanted, other = view.signalsList
    view.selectedItem = other

    QVizSelectNodes(view, wanted).execute()

    assert pathsInSelection(view) == ['core/time_slice(0)/a']
    assert entryFor(view, wanted)['QTreeWidgetItem'] is wanted
    assert labelColours(wanted, other) == ['selected', 'other']


@pytest.mark.ui
def test_unselecting_recolours_the_node_it_was_asked_about(view):
    # Measured: unselecting a while the tree was on b left a red and turned b
    # blue -- the user saw a selected node as free and a free one as selected.
    fill(view, _a(), _b(), _a_of_other_element())
    for node in view.signalsList:
        select(view, node)
    asked, current = view.signalsList[0], view.signalsList[1]
    view.selectedItem = current

    QVizSignalHandling(view, asked).selectOrUnselectSignal()

    assert pathsInSelection(view) == ['core/time_slice(0)/b',
                                      'core/time_slice(1)/a']
    assert labelColours(*view.signalsList) == ['other', 'selected', 'selected']


@pytest.mark.ui
def test_a_node_already_selected_keeps_one_entry_and_its_place(view):
    # The menu entry toggles, so this is the path the AOS entry takes when it
    # walks over a node the user had already picked: the legacy command re-added
    # it and overwrote its place -- measured, three entries all recorded index 2.
    fill(view, _a(), _b())

    select(view, view.signalsList[0])
    select(view, view.signalsList[1])
    QVizSelectNodes(view, view.signalsList[0]).selectNode(
        view.signalsList[0])

    assert indexesInSelection(view) == [0, 1]
    assert pathsInSelection(view) == ['core/time_slice(0)/a',
                                      'core/time_slice(0)/b']


@pytest.mark.ui
def test_unselecting_a_free_node_answers_without_raising(view):
    fill(view, _a())
    node = view.signalsList[0]
    select(view, node)
    # What a rebuilt tree leaves behind: the node is still here, the selection
    # dictionary no longer holds it.
    view.selectedSignalsDict.clear()

    QVizSignalHandling(view, node).selectOrUnselectSignal()

    assert len(view.selectedSignalsDict) == 1
    assert labelColours(node) == ['selected']


@pytest.mark.ui
def test_a_node_keeps_no_selection_flag_of_its_own(view):
    # The flag was the second record of the same fact, and the one the menu
    # believed. It is gone from the commands and from the tree builder.
    fill(view, _a())
    node = view.signalsList[0]

    select(view, node)
    selected = 'isSelected' in node.getData()
    QVizSignalHandling(view, node).selectOrUnselectSignal()

    assert selected is False
    assert 'isSelected' not in node.getData()
    assert view.selectedSignalsDict == {}


# ---------------------------------------------------------------------------
# The entry the menu offers, and the state it offers it for.

@pytest.mark.ui
def test_the_entry_says_select_for_a_free_node(view):
    fill(view, _a())
    node = view.signalsList[0]

    assert QVizSignalHandling(view, node).actionSelectOrUnselectSignalNode() \
        .text() == 'Select a...'


@pytest.mark.ui
def test_the_entry_says_unselect_for_a_selected_node(view):
    fill(view, _a())
    node = view.signalsList[0]
    select(view, node)

    assert QVizSignalHandling(view, node).actionSelectOrUnselectSignalNode() \
        .text() == 'Unselect a...'


@pytest.mark.ui
def test_the_entry_follows_the_selection_and_not_a_flag_of_its_own(view):
    # Measured: with the dictionary emptied and the flag left set, the entry read
    # "Unselect a..." and its slot answered KeyError, so the node could be
    # neither unselected nor selected.
    fill(view, _a())
    node = view.signalsList[0]
    select(view, node)
    view.selectedSignalsDict.clear()

    text = QVizSignalHandling(view, node).actionSelectOrUnselectSignalNode().text()

    assert text == 'Select a...'
    QVizSignalHandling(view, node).selectOrUnselectSignal()
    assert len(view.selectedSignalsDict) == 1


# ---------------------------------------------------------------------------
# All the nodes of the same structure.

@pytest.mark.ui
def test_the_aos_entry_takes_the_elements_of_that_structure(view):
    fill(view, _a(), _a_of_other_element())

    select(view, view.signalsList[0])
    QVizSignalHandling(view, view.signalsList[0]).selectAllSignalsFromSameAOS()

    assert sorted(pathsInSelection(view)) == ['core/time_slice(0)/a',
                                              'core/time_slice(1)/a']


@pytest.mark.ui
def test_the_aos_entry_leaves_out_the_other_leaf_and_the_other_structure(view):
    fill(view, _a(), _a_of_other_element(), _b(), _a_of_other_aos())

    QVizSelectNodes(view, view.signalsList[0]).sameAos()

    assert sorted(pathsInSelection(view)) == ['core/time_slice(0)/a',
                                              'core/time_slice(1)/a']


@pytest.mark.ui
def test_the_aos_entry_stays_in_the_occurrence_the_user_clicked(view):
    # Measured: the regex over the display path matched the same leaf of the
    # second occurrence of the IDS too, because the occurrence is not spelled in
    # that path.
    fill(view, _a(), _a_of_other_element(), _a_of_other_occurrence())

    QVizSelectNodes(view, view.signalsList[0]).sameAos()

    assert len(view.selectedSignalsDict) == 2
    assert all(entry['QTreeWidgetItem'].getOccurrence() == 0
               for entry in view.selectedSignalsDict.values())


@pytest.mark.ui
def test_the_aos_entry_on_the_second_occurrence_takes_only_that_one(view):
    fill(view, _a(), _a_of_other_occurrence(), _a_of_other_element())

    QVizSelectNodes(view, _a_of_other_occurrence()).sameAos()

    assert [entry['QTreeWidgetItem'].getOccurrence()
            for entry in view.selectedSignalsDict.values()] == [1]


@pytest.mark.ui
def test_asking_the_aos_entry_twice_changes_nothing(view):
    # Measured: the legacy entry re-added what was already selected and
    # overwrote its place -- every one of three entries ended up index 2.
    fill(view, _a(), _a_of_other_element())
    node = view.signalsList[0]

    QVizSelectNodes(view, node).sameAos()
    before = indexesInSelection(view)
    added = QVizSelectNodes(view, node).sameAos()

    assert added == 0
    assert indexesInSelection(view) == before


@pytest.mark.ui
def test_the_aos_entry_leaves_the_trees_current_item_alone(view):
    # The legacy entry wrote selectedItem for every node it walked through.
    fill(view, _a(), _b())
    node = view.signalsList[0]
    view.selectedItem = view.signalsList[1]

    QVizSelectNodes(view, node).sameAos()

    assert view.selectedItem is view.signalsList[1]


@pytest.mark.ui
def test_a_nested_structure_is_a_family_by_its_type(view):
    fill(view, leaf('core/a(0)/b(1)/x', 'core.a[i].b[j].x'),
         leaf('core/a(1)/b(0)/x', 'core.a[i].b[j].x'),
         leaf('core/a(0)/b(0)/y', 'core.a[i].b[j].y'))

    QVizSelectNodes(view, view.signalsList[0]).sameAos()

    assert sorted(pathsInSelection(view)) == ['core/a(0)/b(1)/x',
                                              'core/a(1)/b(0)/x']


# ---------------------------------------------------------------------------
# Unselecting everything.

@pytest.mark.ui
def test_unselecting_this_view_leaves_the_other_view_alone(view):
    otherView = _otherView(view)
    fill(view, _a())
    fill(otherView, _b())
    select(view, view.signalsList[0])
    select(otherView, otherView.signalsList[0])

    QVizSignalHandling(view).onUnselectSignals(all_DTV=False)

    assert view.selectedSignalsDict == {}
    assert len(otherView.selectedSignalsDict) == 1


@pytest.mark.ui
def test_unselecting_all_databases_empties_every_view(view):
    otherView = _otherView(view)
    fill(view, _a())
    fill(otherView, _b())
    select(view, view.signalsList[0])
    select(otherView, otherView.signalsList[0])

    QVizSignalHandling(view).onUnselectSignals(all_DTV=True)

    assert view.selectedSignalsDict == {}
    assert otherView.selectedSignalsDict == {}


@pytest.mark.ui
def test_unselect_all_clears_what_is_selected_even_if_the_tree_changed(view):
    # Measured: with one selected node the tree no longer listed, the legacy
    # command raised IndexError after dropping two of three, leaving the third
    # selected and its label red.
    fill(view, _a(), _b(), _a_of_other_element())
    nodes = list(view.signalsList)
    for node in nodes:
        select(view, node)
    view.signalsList = nodes[:2]

    QVizSignalHandling(view).onUnselectSignals(all_DTV=False)

    assert view.selectedSignalsDict == {}
    assert labelColours(*nodes) == ['other', 'other', 'other']


@pytest.mark.ui
def test_unselect_all_recolours_every_label_it_clears(view):
    fill(view, _a(), _b())
    for node in view.signalsList:
        select(view, node)
    assert labelColours(*view.signalsList) == ['selected', 'selected']

    QVizSelectNodes(view).unselectAll()

    assert labelColours(*view.signalsList) == ['other', 'other']


# ---------------------------------------------------------------------------
# What the rest of the application reads.

@pytest.mark.ui
def test_a_plot_command_draws_the_nodes_that_were_selected(view):
    # The frames read entry['QTreeWidgetItem']: an entry holding the tree's
    # current item instead of the node asked for would draw the wrong quantity.
    fill(view, _a(), _b())
    select(view, view.signalsList[0])
    view.selectedItem = view.signalsList[1]
    select(view, view.signalsList[1])

    quantities = QVizPlotAsTable(view).quantities()

    assert [node.getPath() for _, node, _ in quantities] == \
        ['core/time_slice(0)/a', 'core/time_slice(0)/b']
    assert [entry['QTreeWidgetItem'] is node for _, node, entry in quantities] \
        == [True, True]


@pytest.mark.ui
def test_a_selection_read_from_a_configuration_records_the_same_entries(view):
    fill(view, _a(), _b())

    QVizSelectSignals(view, {'paths': ['core/time_slice(0)/b'],
                             'occurrences': [0]}).execute()

    assert pathsInSelection(view) == ['core/time_slice(0)/b']
    assert labelColours(*view.signalsList) == ['other', 'selected']
    assert view.selectedItem is None


def _otherView(view):
    other = view.__class__()
    other.imas_viz_api = view.imas_viz_api
    view.imas_viz_api.DTVlist = [view, other]
    return other
