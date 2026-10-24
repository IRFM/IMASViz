# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""How many elements of a dynamic array a view keeps, on a real case.

:file:`doc/source/manual/loading_IDS.rst` promises four views -- *All time
slices*, *One over 10 time slices*, *Specific time slice only*, *First time slice
only* (the default) -- and states that the reference *equilibrium* holds 49
``time_slice`` and 1 ``grids_ggd``, with one index serving both.
``tests/test_42_load_an_occurrence.py`` pins the plumbing of that choice against
a fake source that records the call; what no test says is **how much tree each
choice really builds**, which only a real walk can answer. Every number below was
measured on this machine before it was written (WEST 54924 run 0, data dictionary
pinned at 3.35.0, harness dictionary 4.0.0), each from a shot view of its own so
the count is a cold start and not an accumulation:

* a plain load keeps slice 0: **3 368** signals, and the occurrence node reads
  ``occurrence 0 [displaying first time slice]``;
* the case answers 49 for its widest dynamic array, and its two dynamic arrays
  are ``time_slice`` (49) and ``grids_ggd`` (1) -- the manual's sentence, read off
  the case;
* one over ten keeps 5 of the 49 slices: **16 820** signals;
* all slices keeps all 49: **164 792** signals, and **26 s** of walking -- the
  slowest thing in this suite by a wide margin, written down rather than hidden;
* ``atIndex(48)`` is kept (3 368 signals, slice 48) and ``atIndex(49)`` is not.

Three measured facts decided how the refusals are asserted, and the first probe
got all three wrong:

* an index past the end does **not** reach the caller. ``QVizIDSViewParser.run()``
  catches ``ValueError`` and consigns it to the log of the case, so the refusal is
  an ERROR line naming the array, how many it holds and the bound;
* a refused view loads **nothing at all**: on a cold view, ``atIndex(49)`` leaves
  0 signals and ``loadedOccurrences`` empty, so the occurrence is not even marked
  loaded. A test expecting a raised exception, or expecting the previous view to
  survive, is testing the wrong door;
* the narrower array only refuses when the walk meets it. With ``Ignore_GGD=1``
  -- what the harness leaves it at -- the walk skips ``grids_ggd``, so
  ``atIndex(1)`` is accepted; with ``Ignore_GGD=0`` the same index is refused by
  ``grids_ggd: 1 is not a time slice of this IDS: it holds 1, so the index runs
  from 0 to 0.`` The manual's "an index past the end of the narrower one is
  refused" is conditional on the GGD preference, and the test says so.

The last fact is not a promise but a measurement of a defect: a second view whose
slices overlap the first **duplicates** them. Loading slice 0 and then one over
ten gives 3 368 + 16 820 = **20 188** signals for five distinct slices, and the
paths spelling ``time_slice(0)`` are there twice. Loading all slices on top of
that gives 184 980. That is pinned as what happens today, not as what should
happen; the same arithmetic on non-overlapping slices (slice 0, then slice 1) is
what the manual's "Add a new view" gesture is for.
"""

import pytest

from imas.ids_data_type import IDSDataType

from imasviz.VizDataAccess.VizTimeSlices import (ALL_SLICES, FIRST_SLICE,
                                                 ONE_IN_TEN, atIndex,
                                                 dynamicArrayCount)
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizUtils import QVizPreferences
from imasviz.Viz_API import Viz_API

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip

IDS_NAME = 'equilibrium'
OCCURRENCE = 0
ONE_SLICE = 3368
ONE_IN_TEN_SLICES = [0, 10, 20, 30, 40]
ONE_IN_TEN_SIGNALS = 16820
ALL_SLICES_SIGNALS = 164792
TIME_SLICES = 49
GRIDS_GGD = 1

pytestmark = [pytest.mark.case, pytest.mark.dd]


def slicesKept(view):
    """Which elements of ``time_slice`` this view is holding, as numbers."""
    return sorted({int(node.getPath().split('/time_slice(')[1].split(')')[0])
                   for node in view.signalsList
                   if '/time_slice(' in node.getPath()})


def pathsOfSlice(view, index):
    """The leaves of one slice, by their spelling in the tree."""
    return [node.getPath() for node in view.signalsList
            if '/time_slice(%d)/' % index in node.getPath()]


def loading(view, sliceSelection=None):
    """The load one menu entry stands for, walked here rather than in a thread."""
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                       occurrence=OCCURRENCE, sliceSelection=sliceSelection,
                       asynch=False).execute()


def opening(api):
    """A shot view built the way ``QVizOpenShotView.Open`` builds one.

    The frame stays reachable through ``api.DTVframeList`` for the whole module,
    which is what keeps it alive in the application -- and here.
    """
    source = QVizDataSourceFactory(None).create(CASE_URI)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    return api.CreateDataTree(source).dataTreeView


@pytest.fixture(scope='module')
def api(qapp):
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    return Viz_API()


@pytest.fixture(scope='module')
def view(api):
    """One shot view, loaded twice in the tests below, in the order written.

    The accumulation is on purpose: what the second load leaves behind is one of
    the facts being pinned.
    """
    return opening(api)


# --------------------------------------------------------------------------
# What the default view is, and how wide the arrays really are
# --------------------------------------------------------------------------

def test_a_plain_load_keeps_the_first_slice_and_says_so(view):
    loading(view)

    assert slicesKept(view) == [0]
    assert len(view.signalsList) == ONE_SLICE
    assert view.ids_roots_occurrence['%s/%d' % (IDS_NAME, OCCURRENCE)] \
        .text(0) == 'occurrence 0 [displaying first time slice]'


def test_the_case_answers_how_wide_its_dynamic_arrays_are(view):
    ids = view.loadedIds(IDS_NAME)

    assert dynamicArrayCount(ids) == TIME_SLICES
    widths = {meta.name: len(getattr(ids, meta.name))
              for meta in ids.metadata
              if meta.data_type is IDSDataType.STRUCT_ARRAY
              and meta.type.is_dynamic}
    # The manual's sentence about the reference equilibrium, read off the case:
    # one index has to serve both, so the narrow one bounds it.
    assert widths == {'time_slice': TIME_SLICES, 'grids_ggd': GRIDS_GGD}


# --------------------------------------------------------------------------
# Adding a view of the same occurrence
# --------------------------------------------------------------------------

def test_a_second_view_of_other_slices_adds_their_trees(view):
    loading(view, atIndex(1))

    assert slicesKept(view) == [0, 1]
    assert len(view.signalsList) == 2 * ONE_SLICE
    assert view.ids_roots_occurrence['%s/%d' % (IDS_NAME, OCCURRENCE)] \
        .text(0) == 'occurrence 0 [displaying time slice with index=1]'


def test_a_second_view_whose_slices_overlap_duplicates_them(api):
    # Its own view, so the two loads below are the only ones behind the numbers:
    # slice 0 first, then one over ten -- whose five slices include slice 0.
    overlap = opening(api)
    loading(overlap)
    sliceZero = len(pathsOfSlice(overlap, 0))

    loading(overlap, ONE_IN_TEN)

    # Five distinct slices, but the tree holds slice 0 twice: the second walk
    # does not notice that the view already has it. Pinned as what happens today.
    assert slicesKept(overlap) == ONE_IN_TEN_SLICES
    assert len(pathsOfSlice(overlap, 0)) == 2 * sliceZero
    assert len(overlap.signalsList) == ONE_SLICE + ONE_IN_TEN_SIGNALS


def test_one_over_ten_on_a_view_of_its_own_keeps_five_slices(api):
    ten = opening(api)

    loading(ten, ONE_IN_TEN)

    assert slicesKept(ten) == ONE_IN_TEN_SLICES
    assert len(ten.signalsList) == ONE_IN_TEN_SIGNALS
    assert ten.ids_roots_occurrence['%s/%d' % (IDS_NAME, OCCURRENCE)] \
        .text(0) == 'occurrence 0 [displaying one over 10 time slices]'


# --------------------------------------------------------------------------
# What each refusal says, and where it says it
# --------------------------------------------------------------------------

def test_an_index_past_the_end_is_said_in_the_log_and_loads_nothing(api, caplog):
    refused = opening(api)

    loading(refused, atIndex(TIME_SLICES))

    assert ('time_slice: %d is not a time slice of this IDS: it holds %d, so the '
            'index runs from 0 to %d.'
            % (TIME_SLICES, TIME_SLICES, TIME_SLICES - 1)) in caplog.text
    # Not "the previous view survives": nothing was loaded at all, and the
    # occurrence is not even marked as such.
    assert refused.signalsList == []
    assert refused.loadedOccurrences(IDS_NAME) == []


def test_the_last_slice_the_case_holds_is_accepted(api):
    last = opening(api)

    loading(last, atIndex(TIME_SLICES - 1))

    assert slicesKept(last) == [TIME_SLICES - 1]
    assert len(last.signalsList) == ONE_SLICE


def test_a_selection_without_an_index_is_refused_before_anything_is_read(api):
    cold = opening(api)

    # The menu asks the user; a script has to name the index. So the menu entry
    # is not a load request, and it says so by raising -- unlike an index the IDS
    # does not hold, which is consigned to the log.
    with pytest.raises(ValueError, match='the menu asks the user for one'):
        loading(cold, atIndex(None))

    assert cold.signalsList == []


def test_the_narrower_array_only_refuses_when_the_walk_meets_it(api, monkeypatch,
                                                                caplog):
    # Ignore_GGD=1, which is what the harness leaves it at, keeps grids_ggd out of
    # the walk: the narrow array is never met, so index 1 is accepted.
    assert QVizPreferences.Ignore_GGD == 1
    ignored = opening(api)
    loading(ignored, atIndex(GRIDS_GGD))
    assert slicesKept(ignored) == [GRIDS_GGD]

    monkeypatch.setattr(QVizPreferences, 'Ignore_GGD', 0)
    met = opening(api)
    loading(met, atIndex(GRIDS_GGD))

    assert ('grids_ggd: %d is not a time slice of this IDS: it holds %d, so the '
            'index runs from 0 to 0.' % (GRIDS_GGD, GRIDS_GGD) in caplog.text)
    assert met.signalsList == []
    assert met.loadedOccurrences(IDS_NAME) == []


# --------------------------------------------------------------------------
# The widest view: measured at 26 s of walking, 164 792 signals
# --------------------------------------------------------------------------

def test_all_time_slices_keeps_every_slice_of_the_occurrence(api):
    whole = opening(api)

    loading(whole, ALL_SLICES)

    assert slicesKept(whole) == list(range(TIME_SLICES))
    assert len(whole.signalsList) == ALL_SLICES_SIGNALS
    assert whole.ids_roots_occurrence['%s/%d' % (IDS_NAME, OCCURRENCE)] \
        .text(0) == 'occurrence 0 [displaying all time slices]'
