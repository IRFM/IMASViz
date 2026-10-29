# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a node path answers, and what it refuses -- read off the IDS object.

A shot view is built from paths it holds as text: the parser spells them, the
tree builder turns them into items, the documentation panel turns an item's path
back into one. Until now their value was asked with a pair of statements --
`exec(idsName + " = self.getIDSRef()")` and then `eval(path)` -- which never
looked at the IDS: the first bound a *local name* in the frame of the caller and
the second was left to find it back in that frame's locals. That is a CPython
implementation detail. Measured on this node's Python 3.11.5 the pair answers; on
the frame semantics of Python 3.13 the binding made by `exec` is not visible to
the `eval` that follows it, and a real session on such a node answered for every
node it built:

    File ".../QVizDataTreeView.py", line 574, in event
        self.onResult(event)
    ...
    File ".../QVizTreeNode.py", line 579, in updateStyle
        e = self.evalPath(self.getDataName())
    File ".../QVizTreeNode.py", line 836, in evalPath
        return eval(path)
    NameError: name 'magnetics' is not defined

Nothing there names the case, the IDS or the path, and the tree stops at the
node that asks. The Profiles plugin carried the same pair five times -- one
`exec` binding the IDS under its own name, fifteen `eval` reads after it -- so
the same node lost the plugin's time slider, spin box and labels too.

Walking the instance answers the same values, and does it faster. Both numbers
were measured on the reference case (WEST 54924 run 0, opened at its own
dictionary 3.35.0) by recording every path a real shot view asks:

* building the view of `magnetics` occurrence 0 asks **11 428** paths and of
  `equilibrium` occurrence 0 **3 703** more -- **15 131** over **802** distinct
  shapes, **none** of them failing -- in **0,189 s** with the pair against
  **0,053 s** with the walk;
* asking the callers that are still reached (`coordinateValues`, the error bars)
  of every one of the **9 426** signal nodes of those two views is **22 658**
  paths, identical answers, **0,630 s** against **0,076 s**;
* the plot path asks **none**: `QVizPlotAsSlices` went through the axes model
  long ago, and the documentation panel asks three.

Two things the pair could not answer are now refused by name instead of by a
bare `NameError` or `SyntaxError`. An index that was never given a position --
`[i]`, `[itime]` -- is named as such. And a coordinate the dictionary spells as
a range rather than a position is named with its text: on this case **537**
nodes of `magnetics` and **6** of `equilibrium` carry one (`1...2` for
`magnetics/flux_loop(i)/indices_differential`, `1...3` for
`equilibrium/time_slice(itime)/coordinate_system/tensor_covariant`), which
reached the evaluator as `magnetics.1...2` and was refused with
`SyntaxError: invalid syntax (<string>, line 1)` -- a message that named neither
the node nor the coordinate, and was swallowed by the caller.

The guard at the end is the point of the file: it walks the compiled module of
the shot view and of the plugin and refuses the names `eval` and `exec` in it,
so the pair cannot come back one call site at a time.
"""

import inspect
import types

import pytest
import numpy as np

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizTreeView import QVizTreeNode
from imasviz.VizGUI.VizTreeView.QVizTreeNode import resolveIDSPath
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizPlugins.viz_Profiles.viz_profiles import VizProfiles
from imasviz.Viz_API import Viz_API

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip

IDS_NAME = 'magnetics'
OCCURRENCE = 0

pytestmark = [pytest.mark.case, pytest.mark.dd]


@pytest.fixture(scope='module')
def view(qapp):
    """One shot view of the reference case, with `magnetics` occurrence 0 loaded.

    Built the way `QVizOpenShotView.Open` builds one, and kept through the api's
    `DTVframeList` for the whole module -- which is what keeps it alive in the
    application, and here.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    api = Viz_API()
    source = QVizDataSourceFactory().create(CASE_URI)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    view = api.CreateDataTree(source).dataTreeView
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME, occurrence=OCCURRENCE,
                       asynch=False).execute()
    return view


def nodeOf(view, path):
    """The node the tree holds under that path, by its spelling in the tree."""
    for node in view.signalsList:
        if node.getPath() == path:
            return node
    raise AssertionError('no node %r among %d signals'
                         % (path, len(view.signalsList)))


def nodeInTree(view, path):
    """The node on screen under that path, structures included.

    `signalsList` holds quantities only, so it cannot answer for the two shapes
    that are not one: an element of a dynamic array and a structure are on the
    screen and in no list of signals.
    """

    def walk(item):
        for number in range(item.childCount()):
            child = item.child(number)
            if child.getPath() == path:
                return child
            found = walk(child)
            if found is not None:
                return found

    found = walk(view.IDSRoots[IDS_NAME])
    if found is None:
        raise AssertionError('no node %r in the tree of %s' % (path, IDS_NAME))
    return found


# --------------------------------------------------------------------------
# The values are the ones the IDS object holds
# --------------------------------------------------------------------------

def test_a_node_path_answers_the_values_of_the_same_leaf(view):
    node = nodeOf(view, 'magnetics/flux_loop(0)/flux/time')
    leaf = node.getIDSRef().flux_loop[0].flux.time
    answer = node.resolvePath(node.getDataName())
    assert np.array_equal(np.asarray(answer), np.asarray(leaf))
    assert len(np.asarray(answer)) == len(np.asarray(leaf))


def test_the_bare_name_of_an_ids_answers_the_ids_itself(view):
    """An IDS root carries its own name as its data name.

    `QVizDataTreeView` sets `dataName` to the IDS name for a root node, and
    `updateStyle` reads it -- so the bare name has to answer the instance, not
    raise on a name nothing bound.
    """
    instance = view.dataSource.get(IDS_NAME, OCCURRENCE)
    assert resolveIDSPath(IDS_NAME, IDS_NAME, instance) is instance


def test_the_last_element_of_an_array_is_reached_by_a_negative_index(view):
    """The plugin read its last time value as `time[-1]`; the walk must too."""
    instance = view.dataSource.get(IDS_NAME, OCCURRENCE)
    last = resolveIDSPath('%s.time[-1]' % IDS_NAME, IDS_NAME, instance)
    assert float(last) == float(instance.time[-1])
    assert float(last) == float(resolveIDSPath(
        '%s.time[%d]' % (IDS_NAME, len(instance.time) - 1), IDS_NAME, instance))


# --------------------------------------------------------------------------
# What is refused, and how it is named
# --------------------------------------------------------------------------

def test_an_index_that_was_never_given_a_position_is_refused_by_name(view):
    """Spelled from real nodes: a parametrized path is one of these by nature.

    `getParametrizedDataPath` is how the selection names a quantity held by an
    array of structures -- with the index *letter*, never a position. So the two
    paths below are not invented: they are what the tree hands out before a load
    turns that letter into a number.
    """
    instance = view.dataSource.get(IDS_NAME, OCCURRENCE)
    unvalued = sorted({node.getParametrizedDataPath() for node in view.signalsList
                       if '[i]' in node.getParametrizedDataPath()})
    assert len(unvalued) > 1, 'no parametrized path among %d signals' \
                              % len(view.signalsList)
    for path in unvalued[:2]:
        with pytest.raises(ValueError) as raised:
            resolveIDSPath(path, IDS_NAME, instance)
        message = str(raised.value)
        assert path in message
        assert 'never given a position' in message


def test_a_path_of_another_ids_is_refused_naming_both(view):
    instance = view.dataSource.get(IDS_NAME, OCCURRENCE)
    with pytest.raises(ValueError) as raised:
        resolveIDSPath('equilibrium.time', IDS_NAME, instance)
    assert 'equilibrium.time' in str(raised.value)
    assert IDS_NAME in str(raised.value)


def test_a_node_without_a_loaded_ids_is_refused_naming_the_ids():
    with pytest.raises(ValueError) as raised:
        resolveIDSPath('magnetics.time', 'magnetics', None)
    assert 'magnetics' in str(raised.value)
    assert 'not loaded' in str(raised.value)


def test_a_coordinate_spelled_as_a_range_is_refused_naming_that_text(view):
    """Measured on this case: 537 nodes of `magnetics` carry one of these.

    The dictionary spells the first coordinate of
    `magnetics/flux_loop(i)/indices_differential` as `1...2`, and the guard in
    `coordinateValues` only catches the literal `1..N` / `1...N`, so the text
    reaches the walk as `magnetics.1...2`. It was refused with
    `SyntaxError: invalid syntax (<string>, line 1)`; it is refused with the
    offending text named.
    """
    node = nodeOf(view, 'magnetics/flux_loop(0)/indices_differential')
    assert node.coordinates[0] == '1...2'
    with pytest.raises(ValueError) as raised:
        node.coordinateValues(1, view)
    assert '1...2' in str(raised.value)
    assert 'not a node of the dictionary' in str(raised.value)


def test_a_leaf_the_opened_object_does_not_hold_is_named_by_the_runtime(view):
    """Not rewritten: the runtime answer already names the structure and the leaf.

    Measured: `AttributeError: IDS structure 'flux_loop[0]/flux' has no attribute
    'not_a_node'` -- which is what the documentation panel puts on its `No values:`
    row, so the user learns which leaf is missing. The walk hands that on rather
    than dressing it up in a `ValueError` that would name less.
    """
    node = nodeOf(view, 'magnetics/flux_loop(0)/flux/time')
    with pytest.raises(AttributeError) as raised:
        node.resolvePath('magnetics.flux_loop[0].flux.not_a_node')
    assert 'flux_loop[0]/flux' in str(raised.value)
    assert 'not_a_node' in str(raised.value)


# --------------------------------------------------------------------------
# The data path a node has, and the one it has not
# --------------------------------------------------------------------------

def test_a_leaf_is_named_by_its_parametrized_data_path(view):
    node = nodeOf(view, 'magnetics/flux_loop(0)/flux/data')

    assert node.getParametrizedDataPath() == 'magnetics.flux_loop[i].flux.data'


def test_a_node_that_is_not_a_leaf_has_no_data_path(view):
    """Nothing to append a name to: the walk spells the path on a leaf only.

    A structure and an element of a dynamic array carry a name -- the dictionary
    gives them one -- and no parametrized path. Measured on the reference case:
    `magnetics/flux_loop(0)` and `magnetics/flux_loop(0)/flux` both answer None.
    The thumbnail the left click asks for names the node it refuses, so while
    this accessor answered `None + '.' + name` every click on a folder of the
    tree died with TypeError in that panel.
    """
    for path, dataType in (('magnetics/flux_loop(0)', 'struct_array'),
                           ('magnetics/flux_loop(0)/flux', 'structure')):
        node = nodeInTree(view, path)

        assert node.getDataType() == dataType
        assert node.getName() is not None
        assert node.getParametrizedPath() is None
        assert node.getParametrizedDataPath() is None


# --------------------------------------------------------------------------
# The guard: the idiom may not come back
# --------------------------------------------------------------------------

def _names_used_by(owner):
    """Every name the compiled module of `owner` can look up, at any depth.

    `owner` may be a class or a module: the packages here re-export classes under
    their module's name, so `QVizTreeNode` is a class and its module has to be
    found back.
    """
    module = inspect.getmodule(owner)
    found = set()

    def walk(code):
        found.update(code.co_names)
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                walk(constant)

    with open(module.__file__) as source:
        walk(compile(source.read(), module.__file__, 'exec'))
    return found


@pytest.mark.parametrize('owner', [QVizTreeNode, VizProfiles],
                         ids=['the shot view', 'the Profiles plugin'])
def test_neither_module_evaluates_a_name_any_more(owner):
    """`exec` binding a name and `eval` reading it back is what broke.

    Checked on the compiled module rather than on the case: it costs nothing, it
    needs no case, and it holds whatever the runtime underneath happens to answer
    for `eval` itself.
    """
    module = inspect.getmodule(owner)
    names = _names_used_by(owner)
    assert 'eval' not in names, '%s still evaluates names' % module.__name__
    assert 'exec' not in names, '%s still binds names with exec' % module.__name__
