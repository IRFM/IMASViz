# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The tensor view of the tree: one node per non-empty tensor, and nothing else.

The preference is only the **starting** state -- :file:`doc/source/manual/`
documents a file read once at start-up, and the checkbox of the *Actions* menu is
what answers for a tree that is already open. The two are tested apart for that
reason.

What the view leaves on screen was measured on the reference case (WEST 54924
run 0, dictionary pinned at 3.35.0, GGD ignored as the harness leaves it) before
a single number below was written:

* a plain load of ``equilibrium`` occurrence 0 keeps **3 368** signals under
  5 children of the occurrence node, 4 of which are folders;
* the tensor view keeps **48** nodes, all of them leaves, hanging off the
  occurrence itself, with **no folder left**;
* the same tensor met at every element of an array of structures -- the
  ``bpol_probe`` family alone runs to 109 instances in one slice -- appears
  **once**, under the path that names it and no index
  (``time_slice/profiles_1d/psi``);
* **every** path kept is one the entry names as filled, and the walk of a case
  that holds 133 filled paths for this IDS keeps 48: the difference is what the
  dictionary declares and this case never wrote, which is the whole point of the
  filter;
* it costs **1,89 s** against **0,50 s** for the plain load. The extra is asking
  the entry which paths hold data -- once per IDS, without reading a value --
  and walking the leaves the plain load would have shown.

Two things the first cuts of this got wrong, and the tests pin both:

* the emptiness question was first asked of each tensor by reading it. The entry
  answers it for every path at once (measured **0,022 s** for this IDS), which is
  also the only answer that does not depend on a lazy handle outliving its entry;
* a rank was first read off ``QVizNodePlotting.rank()``, which counts the array
  of structures a quantity sits in. A scalar held by ``time_slice`` therefore
  answers 1 and survived a ``rank() < 1`` test; the axes the leaf owns
  (``axes.leafAxes()``) are the quantity itself, and a scalar owns none.
"""

import re

import pytest

from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizSignalHandling \
    import QVizSignalHandling
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils import QVizPreferences
from imasviz.Viz_API import Viz_API

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip

IDS_NAME = 'equilibrium'
OCCURRENCE = 0
TENSOR_NODES = 48
PLAIN_SIGNALS = 3368
PLAIN_CHILDREN = 5

pytestmark = [pytest.mark.case, pytest.mark.dd]


def opening(api, tensorView):
    """A shot view built the way ``QVizOpenShotView.Open`` builds one.

    The filter is settled on the view before the load, which is what the
    checkbox does to a tree that is already open.
    """
    source = QVizDataSourceFactory().create(CASE_URI)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    view = api.CreateDataTree(source).dataTreeView
    view.showOnlyTensorsRankGe1 = tensorView
    return view


def loading(view):
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                       occurrence=OCCURRENCE, asynch=False).execute()


def childrenOf(view):
    root = view.ids_roots_occurrence['%s/%d' % (IDS_NAME, OCCURRENCE)]
    return [root.child(i) for i in range(root.childCount())]


def leavesOf(view):
    return [node for node in childrenOf(view)
            if node.isDynamicData() or node.isStaticData()]


def keyOf(leaf):
    """The path a node names, free of any array index.

    Spelled here rather than borrowed from the builder: the builder lives only
    for the walk that made the tree, and a test reading a private method off a
    view that no longer holds one would be asserting the test's own arithmetic.
    """
    path = leaf.getParametrizedDataPath()
    if path:
        path = path.split('.', 1)[1] if '.' in path else path
    else:
        path = leaf.getPath() or ''
    return re.sub(r'\[[^\]]*\]|\(\d+\)', '', path.replace('.', '/'))


def keysOf(view):
    return [keyOf(leaf) for leaf in leavesOf(view)]


def filledPaths(view):
    return set(view.dataSource.db_entry.list_filled_paths(IDS_NAME, OCCURRENCE))


@pytest.fixture(scope='module')
def api(qapp):
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    return Viz_API()


@pytest.fixture(scope='module')
def tensorView(api):
    """One shot view, opened with the tensor view asked for."""
    view = opening(api, True)
    loading(view)
    return view


@pytest.fixture(scope='module')
def plainView(api):
    """A second shot view of the same case, with the plain tree."""
    view = opening(api, False)
    loading(view)
    return view


# --------------------------------------------------------------------------
# The preference: a starting state, read like the four options before it
# --------------------------------------------------------------------------

def test_the_preference_is_read_from_the_file(monkeypatch, tmp_path):
    """``Show_only_tensors_rank_ge_1=1`` in ``$HOME/.imasviz/preferences``.

    The global is restored: every other file of this suite builds trees of this
    same case, and a preference left switched on would silently change what they
    see.
    """
    (tmp_path / '.imasviz').mkdir()
    (tmp_path / '.imasviz' / 'preferences').write_text(
        'Show_only_tensors_rank_ge_1=1\n')
    monkeypatch.setenv('HOME', str(tmp_path))

    initialized = QVizPreferences.userPreferencesInitialized
    value = QVizPreferences.Show_only_tensors_rank_ge_1
    try:
        QVizPreferences.userPreferencesInitialized = False
        QVizPreferences().build()
        assert QVizPreferences.Show_only_tensors_rank_ge_1 == 1
    finally:
        QVizPreferences.Show_only_tensors_rank_ge_1 = value
        QVizPreferences.userPreferencesInitialized = initialized


def test_the_view_starts_on_the_preference(api):
    """The preference is what a fresh tree starts with, and nothing more."""
    value = QVizPreferences.Show_only_tensors_rank_ge_1
    QVizPreferences.Show_only_tensors_rank_ge_1 = 1
    try:
        view = Viz_API().CreateDataTree(
            QVizDataSourceFactory().create(CASE_URI)).dataTreeView
        assert view.showOnlyTensorsRankGe1 is True
    finally:
        QVizPreferences.Show_only_tensors_rank_ge_1 = value


# --------------------------------------------------------------------------
# What the tensor view leaves on the tree
# --------------------------------------------------------------------------

def test_nothing_but_tensors_is_left_under_the_occurrence(tensorView):
    """No folder, no element of an array, no scalar."""
    children = childrenOf(tensorView)
    assert children, 'the tensor view left an empty occurrence'
    folders = [node for node in children
               if not (node.isDynamicData() or node.isStaticData())]
    assert folders == [], 'folders are still shown: %s' % [
        node.getPath() for node in folders]
    assert len(children) == TENSOR_NODES


def test_one_node_names_one_tensor_whatever_array_holds_it(tensorView):
    """The same tensor at 109 elements of an array is shown once.

    Measured on the plain tree: the ``bpol_probe`` family alone is walked 109
    times inside one slice. Here each path appears once, spelled without an
    index, which is also the spelling the manual and a configuration file use.
    """
    keys = keysOf(tensorView)
    assert len(keys) == len(set(keys)), 'a tensor is shown more than once'
    assert 'time_slice/profiles_1d/psi' in keys
    assert not [key for key in keys if '[' in key or '(' in key], \
        'a kept path still spells an index: %s' % keys


def test_every_tensor_kept_holds_data(tensorView):
    """A tensor is non-empty when at least one of its elements was written.

    That is exactly the question ``list_filled_paths`` answers, and it answers it
    without reading a value -- which is what makes it usable on a lazy handle.
    """
    filled = filledPaths(tensorView)
    assert filled, 'the entry names no filled path at all'
    kept = set(keysOf(tensorView))
    assert kept <= filled, 'empty tensors shown: %s' % sorted(kept - filled)
    # The filter subtracts: the dictionary declares more than this case wrote.
    assert len(kept) < len(filled)


def test_a_scalar_held_by_an_array_is_not_a_tensor(tensorView):
    """A scalar of ``time_slice`` owns no axis of its own, and is not shown.

    ``QVizNodePlotting.rank()`` counts the array it sits in and answers 1 for it;
    the axes of the leaf answer none. This is the distinction the first cut
    missed, and why scalars used to fill the screen.
    """
    from imasviz.VizDataAccess.QVizNodePlotting import QVizNodePlotting
    stranded = [leaf.getPath() for leaf in leavesOf(tensorView)
                if len(QVizNodePlotting(leaf).axes.leafAxes()) < 1]
    assert stranded == []


def test_the_plain_view_keeps_what_the_tensor_view_takes_away(plainView,
                                                             tensorView):
    """The contrast, on the same case: folders and every element of every array.

    Pinned as a measurement of the same load, so that a change narrowing the
    tensor view cannot pass by making the plain tree smaller too.
    """
    assert len(plainView.signalsList) == PLAIN_SIGNALS
    assert len(childrenOf(plainView)) == PLAIN_CHILDREN
    assert len([node for node in childrenOf(plainView)
                if not (node.isDynamicData() or node.isStaticData())]) == 4
    assert len(leavesOf(tensorView)) < len(plainView.signalsList)


# --------------------------------------------------------------------------
# The checkbox, on a tree that is already open
# --------------------------------------------------------------------------

def test_the_checkbox_switches_a_tree_already_open(plainView, qtbot):
    """The *Actions* entry re-walks what the view holds, in place.

    A preference file cannot answer for a session already running, which is why
    the entry exists; the reload it triggers is the same command the menu of an
    occurrence runs -- asynchronously, so the tree changes when the walk lands
    and not when the mouse goes up. Asserting straight after the call reads the
    tree of the previous view, which is how this test first failed.
    """
    assert len(childrenOf(plainView)) == PLAIN_CHILDREN
    plainView.onToggleTensorsFilter(True)
    assert plainView.showOnlyTensorsRankGe1 is True
    qtbot.waitUntil(lambda: len(leavesOf(plainView)) == TENSOR_NODES,
                    timeout=180000)
    assert [node for node in childrenOf(plainView)
            if not (node.isDynamicData() or node.isStaticData())] == []

    plainView.onToggleTensorsFilter(False)
    qtbot.waitUntil(lambda: len(childrenOf(plainView)) == PLAIN_CHILDREN,
                    timeout=180000)


# --------------------------------------------------------------------------
# What the pop-up offers there
# --------------------------------------------------------------------------

def test_the_pop_up_of_a_tensor_offers_the_tensor_entries(tensorView):
    """Tensor tracing with its sliders, and the figures to superpose it on.

    ``Explore this tensor along <axis>`` is the entry that puts a slider on every
    axis the curve leaves out, and one line per open figure drawn along that
    abscissa is what superposes the traces. The plain *Plot* menu of the leaf is
    what the view takes back out.
    """
    leaf = [node for node in leavesOf(tensorView)
            if keyOf(node) == 'time_slice/profiles_1d/psi'][-1]

    handling = QVizSignalHandling(tensorView)
    menu = handling.buildContextMenu(leaf)
    titles = [action.text() for action in menu.actions()]

    assert [title for title in titles
            if title.startswith('Explore this tensor along')], titles
    assert not [title for title in titles
                if title.startswith('Plot ')
                and not title.startswith('Explore')], titles
