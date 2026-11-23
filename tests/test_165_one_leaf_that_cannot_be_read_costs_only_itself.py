# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""One leaf whose value the case refuses must cost only itself.

Measured on WEST 54924 run 0 at its own dictionary 3.35.0: that case holds
`hard_x_rays/code/output_flag` -- a filled array whose coordinate `time` names
a time base the case does not hold (`homogeneous_time = 0`, `IDS.time` empty)
-- and reading it answers `Unable to open HDF5 dataset: time`. The shot view
colours a leaf by **reading** it, so that one leaf stopped the build of its
branch: `hard_x_rays` occurrence 0 landed **0** leaves in the view while the
load answered success with the signal count of the IDS loaded before it, and
every later gesture on that IDS was refused as "not a leaf of the case". Nothing
of that IDS could be searched or drawn -- the user's "je ne peux plus rien
tracer". The neighbouring IDSs of the same shot were fine: `soft_x_rays`
occurrence 0 keeps 4505 leaves, `magnetics` 6058.

A leaf that cannot be read is nothing to draw, so it is left unusable and named
in the log of the case, and the branch it sits in is built: **5687** leaves for
`hard_x_rays` occurrence 0, one of them left out by a refused read -- and that
one refusal is the only one the whole branch answers.
"""

import logging
import types

import numpy as np
import pytest

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip
from support.caseTrees import (loadCaseTrees, nodeAsTheBuilderBuildsIt,
                               shadowTreePaths)
from support.fakes import FakeTreeView

from imasviz.VizGUI.VizTreeView.QVizTreeNode import QVizTreeNode
from imasviz.VizUtils import QVizPreferences

IDS_NAME = 'hard_x_rays'
UNREADABLE_LEAF = 'hard_x_rays/code/output_flag'
DRAWN_LEAF = 'hard_x_rays/channel(0)/radiance/data'

# Measured with the guard standing: the leaves of that occurrence the view
# keeps, and how many of them the case refuses to read.
HARD_X_RAYS_SIGNALS = 5687
HARD_X_RAYS_REFUSED = 1


def captureLog(name):
    """Records of what `name` logged, whatever its own handlers do."""
    records = []

    class Collect(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger(name)
    handler = Collect()
    handler.setLevel(logging.WARNING)
    logger.addHandler(handler)
    return records, handler


# --------------------------------------------------------------------------
# The rule, without a pulse: a refused read is a leaf, not a stopped build
# --------------------------------------------------------------------------

class RefusedIDS:
    """An IDS instance that answers the read the way the backend does."""

    def __getattr__(self, name):
        raise RuntimeError('Error while reading data: al_plugin_read_data: '
                           '[ALBackendException = Unable to open HDF5 dataset:'
                           ' time] Error status=-3')


def nodeWhoseReadIsRefused(dataType):
    node = QVizTreeNode(None, ['output_flag'], {
        'IDSName': IDS_NAME, 'name': 'output_flag',
        'dataName': '%s.code.output_flag' % IDS_NAME, 'data_type': dataType,
        'occurrence': 0, 'isSignal': 1, 'isStatic': 0, 'isSelected': 0,
        'availableData': 1, 'Path': UNREADABLE_LEAF, 'aos_parents_count': '1'})
    node.idsRef = RefusedIDS()
    return node


@pytest.mark.parametrize('dataType', ['FLT_1D', 'FLT_0D', 'FLT_2D'])
def test_a_leaf_whose_read_is_refused_is_marked_unusable_and_named(qapp, caplog,
                                                                   dataType):
    """The colour of a leaf is settled by reading it, on all three shapes.

    Before the guard each of these raised out of `updateStyle`, and the caller
    -- `QVizDataTreeViewBuilder.build_nodes` -- let it go: the build of the whole
    IDS ended at that node, with the exception consigned to the log of the case
    by the parser and the load answering success.
    """
    node = nodeWhoseReadIsRefused(dataType)
    records, handler = captureLog('logPanel')
    try:
        node.updateStyle()
    finally:
        logging.getLogger('logPanel').removeHandler(handler)

    assert node.hasAvailableData() == 0, \
        'a leaf the case cannot answer must not be offered as one that holds data'
    assert any(UNREADABLE_LEAF in record.getMessage() for record in records), \
        'the refused leaf is not named in the log: %r' % [
            record.getMessage() for record in records]
    assert any('Unable to open HDF5 dataset' in record.getMessage()
               for record in records), 'the reason the case gave is dropped'


def test_a_leaf_the_case_answers_is_left_as_it_was(qapp):
    """The guard must not touch the leaves that answer."""
    QVizPreferences().build()

    class AnsweringIDS:
        code = types.SimpleNamespace(output_flag=np.array([1.0, 0.0, 1.0]))

    node = QVizTreeNode(None, ['output_flag'], {
        'IDSName': IDS_NAME, 'name': 'output_flag',
        'dataName': '%s.code.output_flag' % IDS_NAME, 'data_type': 'FLT_1D',
        'occurrence': 0, 'isSignal': 1, 'isStatic': 0, 'isSelected': 0,
        'availableData': 0, 'Path': UNREADABLE_LEAF, 'aos_parents_count': '1'})
    node.idsRef = AnsweringIDS()
    node.updateStyle()
    assert node.hasAvailableData() == 1


# --------------------------------------------------------------------------
# On the case that carries the defect
# --------------------------------------------------------------------------

@pytest.fixture(scope='module')
def hardXrays(qapp, request):
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    return loadCaseTrees(qapp, [IDS_NAME], request=request)


@pytest.fixture(scope='module')
def styled(hardXrays):
    """Every node of the branch as the builder puts it on screen, styled.

    `QVizDataTreeViewBuilder.build_nodes` calls `updateStyle()` on each node it
    creates and lets the exception go; this walks the same nodes, so a refused
    read here is the one that used to end the build. Walked once for the module
    and kept, the log of the case caught while it runs.
    """
    case = hardXrays
    # The colour of a leaf that holds data comes from the preferences: without
    # this, `setStyleWhenContainingData` hands Qt a None brush and the walk dies
    # on a TypeError that has nothing to do with what is measured here.
    QVizPreferences().build()
    records, handler = captureLog(case['uri'])
    try:
        treeView = FakeTreeView(uri=case['uri'])
        runtime = case['runtime'][IDS_NAME]
        nodes = {}
        for element, path in shadowTreePaths(case['trees'][IDS_NAME], IDS_NAME):
            node = nodeAsTheBuilderBuildsIt(element, IDS_NAME, runtime,
                                            treeView, path=path)
            node.updateStyle()
            nodes[path] = node
    finally:
        logging.getLogger(case['uri']).removeHandler(handler)
    refusals = [record.getMessage() for record in records
                if 'could not be read' in record.getMessage()]
    return nodes, refusals


def test_the_whole_branch_is_styled_though_one_leaf_refuses_the_read(styled):
    nodes, _ = styled
    assert len(nodes) > 1000, 'the branch is not walked: %d nodes' % len(nodes)


def test_the_refused_leaf_is_left_unusable_and_its_neighbours_are_not(styled):
    """Only the refused leaf loses its colour, and only once.

    Many leaves of this case answer an empty array or an empty string and are
    legitimately shown as holding nothing -- measured: 15 063 of them for
    `hard_x_rays` occurrence 0, most of those the `name` text of an error index.
    That is not what a refused read looks like: the read that came back with a
    value is not named in the log, the read that raised is, and the log of the
    case answers **one** such line for the whole branch.
    """
    nodes, refusals = styled
    refusedLeaf = nodes[UNREADABLE_LEAF]
    assert refusedLeaf.hasAvailableData() == 0, \
        'a leaf whose read raised is shown as one that holds data'
    assert len(refusals) == HARD_X_RAYS_REFUSED, \
        'more than the measured leaf had its read refused: %r' % refusals

    radiance = nodes[DRAWN_LEAF]
    assert radiance.hasAvailableData() == 1, \
        'the filled two-dimension radiance of the same IDS is refused too'
    time = nodes['hard_x_rays/channel(0)/radiance/time']
    assert time.hasAvailableData() == 1, \
        'the time base of that radiance is refused too'


def test_the_refusal_is_named_once_in_the_log_of_the_case(styled):
    _, messages = styled
    assert len(messages) == HARD_X_RAYS_REFUSED, \
        '%d leaves refused the read: %r' % (len(messages), messages)
    assert UNREADABLE_LEAF in messages[0]


# --------------------------------------------------------------------------
# The gesture the user made: the load of that occurrence keeps its leaves
# --------------------------------------------------------------------------

@pytest.fixture(scope='module')
def loaded(qapp):
    """A shot view of the case holding `hard_x_rays` occurrence 0.

    Built the way `QVizOpenShotView.Open` builds one, so `signalsList` is the
    record the real gestures ask -- *Plot* for everything, a Table Plot View,
    the search of the agent.
    """
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
    from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
        import QVizLoadOccurrence
    from imasviz.Viz_API import Viz_API

    api = Viz_API()
    source = QVizDataSourceFactory().create(CASE_URI)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    view = api.CreateDataTree(source).dataTreeView
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME, occurrence=0,
                       asynch=False).execute()
    return view


@pytest.mark.case
@pytest.mark.dd
def test_the_occurrence_that_landed_no_leaf_keeps_them_all(loaded):
    """0 against 5687: the number the user's "je ne peux plus rien tracer" was.

    `showOccurrenceView` extends `signalsList` from `endBuildView`, which the
    aborted build never reached, so the occurrence reported loaded and held
    nothing: `search_nodes` and *Plot* refused every path of that IDS as "not a
    leaf of the case".
    """
    paths = {node.getPath() for node in loaded.signalsList}
    assert len(loaded.signalsList) == HARD_X_RAYS_SIGNALS, \
        '%d signals for %s occurrence 0' % (len(loaded.signalsList), IDS_NAME)
    assert DRAWN_LEAF in paths, 'the radiance the user asked for is not a leaf'
    assert UNREADABLE_LEAF in paths, \
        'the refused leaf left the tree instead of being left unusable'
    refusal = [node for node in loaded.signalsList
               if node.getPath() == UNREADABLE_LEAF][0]
    assert refusal.hasAvailableData() == 0
