# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The window between asking for a load and getting the tree: the default path.

`asynch=True` is the default of `QVizLoadOccurrence`, so it is the path every menu
entry takes, and `tests/test_46_time_slices_on_a_real_case.py` deliberately walked
the other one. What no test looked at is the interval itself -- the request has
returned, the walk is still running, and the application is still answering. Every
number and every state below was measured on the reference case (WEST 54924 run 0,
data dictionary pinned at 3.35.0) before it was written, with the event loop
pumped by hand so the delivery rounds are visible:

* the request returns in **0,010 s**, having built nothing: 0 signals, the view
  saying the load is in flight, one parser held alive;
* the walk runs on another thread (`Dummy-1`) and the tree is built on the one
  that owns the view (`MainThread`) -- measured at **6 058** signals for
  `magnetics`, **3 368** for one slice of `equilibrium`;
* while the walk runs, the same occurrence asked of the same view is refused with
  a sentence and does not start a second walk; asked of *another* view, it goes
  through -- which is what the retired class-level `Lock` used to prevent.

One measured defect is fixed here rather than pinned, and the first probe found it
by hanging. On the refusal path of an asynchronous walk -- an index the IDS does
not hold, a dictionary that does not match, anything the walk cannot swallow --
`run()` took the progress bar down itself, from the walk's own thread. On this Qt
stack that call never returns: a thread asked to `close()` a window it does not
own sits in `QWindow::close()` waiting on the GUI thread, and the GUI thread is
waiting for a thread that will not come back. Reproduced without IMAS and without
a case: a `QThread` closing a shown `QProgressBar` stays in `close()` past a 20 s
watchdog. The walk thread is therefore lost, `finished` never fires, the parser is
never dropped, the occurrence stays in `loadsInProgress` for the rest of the
session -- so every later request for it is refused as "already being loaded" --
and the bar stays on screen. So the walk may log what it met, but it may not touch
a window: the bar now goes down on the thread that made it, through the source's
`finished` handler, which is delivered on the thread the view belongs to (measured:
`_loadFinished` on `MainThread`).

Two consequences are pinned rather than fixed, because they are behaviour rather
than a hang: the bar of an accepted asynchronous load is taken down by the frame
that receives the result, and one progress-bar window is left alive per load --
closed, off screen, not destroyed. That accumulation is measured (one per load)
and left alone deliberately; the visible promise is that none is on screen once
the load is over.
"""

import time

import pytest

from PySide6.QtWidgets import QApplication, QProgressBar

from imasviz.VizDataAccess.VizTimeSlices import atIndex
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.Viz_API import Viz_API

from conftest import CASE_DATA_DICTIONARY_VERSION, CASE_URI, case_uri_or_skip

EQUILIBRIUM = 'equilibrium'
MAGNETICS = 'magnetics'
OCCURRENCE = 0
ONE_SLICE = 3368
MAGNETICS_SIGNALS = 6058
TIME_SLICES = 49
REFUSAL = ('time_slice: %d is not a time slice of this IDS: it holds %d, so the '
           'index runs from 0 to %d.' % (TIME_SLICES, TIME_SLICES, TIME_SLICES - 1))

pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


def visibleBars():
    """The progress bars this session has on screen.

    A bar is built per load and only closed, never destroyed: what the user must
    not meet is a bar still on screen after the load it belongs to is over. The
    count is only meaningful across a whole test, so a test of one view asks that
    view's own source (see `barOf`).
    """
    return [bar for bar in QApplication.topLevelWidgets()
            if isinstance(bar, QProgressBar) and bar.isVisible()]


def barOf(view):
    """The bar of the last load this view's source started."""
    return view.dataSource.progressBar


def barsOnScreen():
    """Every progress-bar window alive, visible or not: one per load."""
    return [bar for bar in QApplication.topLevelWidgets()
            if isinstance(bar, QProgressBar)]


def opening(api):
    """A shot view built the way `QVizOpenShotView.Open` builds one."""
    source = QVizDataSourceFactory(None).create(CASE_URI)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    return api.CreateDataTree(source).dataTreeView


def asking(view, idsName, sliceSelection=None):
    """The asynchronous load -- the default, and the one every menu entry takes."""
    QVizLoadOccurrence(dataTreeView=view, idsName=idsName,
                       occurrence=OCCURRENCE, sliceSelection=sliceSelection,
                       asynch=True).execute()


def delivered(qtbot, view, idsName):
    """Wait for the walk's result to reach the view, then for the walk to end."""
    qtbot.waitUntil(lambda: '%s/%d' % (idsName, OCCURRENCE)
                    in view.ids_roots_occurrence, timeout=60000)
    qtbot.waitUntil(lambda: not view.dataSource.runningParsers, timeout=60000)
    assert view.isLoadInFlight(idsName, OCCURRENCE) is False


@pytest.fixture(scope='module')
def api(qapp):
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    return Viz_API()


# --------------------------------------------------------------------------
# The flight: what the view says while the walk runs
# --------------------------------------------------------------------------

def test_the_request_returns_before_anything_is_built(qtbot, api):
    view = opening(api)

    asking(view, EQUILIBRIUM)

    # The call is not the walk: it hands the walk to a thread and comes back.
    assert len(view.signalsList) == 0
    assert view.isLoadInFlight(EQUILIBRIUM, OCCURRENCE) is True
    assert len(view.dataSource.runningParsers) == 1
    assert barOf(view).isVisible()

    # Let this one land: a view left mid-walk hands its progress bar, and its
    # thread, to whichever test runs next.
    delivered(qtbot, view, EQUILIBRIUM)


def test_the_tree_arrives_on_the_thread_that_owns_the_view(qtbot, api):
    view = opening(api)
    asking(view, MAGNETICS)

    # Real time, no event loop: the walk may well be over, and the tree still
    # absent -- it is applied by the event the walk posts, in the thread that
    # owns the widget, not by the walk itself.
    time.sleep(0.5)
    assert len(view.signalsList) == 0

    delivered(qtbot, view, MAGNETICS)
    assert len(view.signalsList) == MAGNETICS_SIGNALS


def test_the_bar_of_an_asynchronous_load_is_off_screen_once_it_is_over(qtbot,
                                                                       api):
    view = opening(api)
    alive = len(barsOnScreen())
    asking(view, MAGNETICS)
    assert barOf(view).isVisible()

    delivered(qtbot, view, MAGNETICS)

    assert barOf(view).isVisible() is False
    # Closed, not destroyed: the window of a finished load stays alive, one per
    # load. Measured, and left alone here -- what is promised is that none of
    # them is on screen.
    assert len(barsOnScreen()) == alive + 1


# --------------------------------------------------------------------------
# What the guard meets while a load is in flight
# --------------------------------------------------------------------------

def test_the_same_occurrence_asked_twice_while_in_flight_starts_one_walk(
        qtbot, api, caplog):
    view = opening(api)
    asking(view, EQUILIBRIUM)

    with caplog.at_level('INFO', logger=view.uri):
        asking(view, EQUILIBRIUM)
        assert len(view.dataSource.runningParsers) == 1

    assert ('Occurrence 0 of the equilibrium IDS is already being loaded in this '
            'view: this request is ignored.' in caplog.text)

    delivered(qtbot, view, EQUILIBRIUM)
    # One walk, one tree -- the second request added nothing behind it.
    assert len(view.signalsList) == ONE_SLICE


def test_another_view_may_load_the_same_occurrence_while_this_one_walks(qtbot,
                                                                        api):
    # The retired guard was a class attribute keyed by IDS name, so a second shot
    # view could not load what the first one was loading.
    first = opening(api)
    second = opening(api)
    asking(first, EQUILIBRIUM)

    asking(second, EQUILIBRIUM)
    assert len(second.dataSource.runningParsers) == 1
    assert second.isLoadInFlight(EQUILIBRIUM, OCCURRENCE) is True

    delivered(qtbot, first, EQUILIBRIUM)
    delivered(qtbot, second, EQUILIBRIUM)
    assert len(first.signalsList) == ONE_SLICE
    assert len(second.signalsList) == ONE_SLICE


# --------------------------------------------------------------------------
# The refusal, on the thread that is allowed to take a window down
# --------------------------------------------------------------------------

def test_a_refused_asynchronous_walk_lets_its_bar_go_and_frees_the_view(
        qtbot, api, caplog):
    view = opening(api)

    with caplog.at_level('ERROR', logger=view.uri):
        asking(view, EQUILIBRIUM, atIndex(TIME_SLICES))

    # The walk ends and its thread comes back: before this was fixed the thread
    # never returned from close(), so this wait would never be satisfied.
    qtbot.waitUntil(lambda: not view.dataSource.runningParsers, timeout=15000)

    assert REFUSAL in caplog.text
    assert view.dataSource.runningParsers == set()
    assert view.isLoadInFlight(EQUILIBRIUM, OCCURRENCE) is False
    assert len(view.signalsList) == 0
    assert barOf(view).isVisible() is False


def test_a_view_whose_walk_was_refused_can_be_asked_again(qtbot, api):
    view = opening(api)
    asking(view, EQUILIBRIUM, atIndex(TIME_SLICES))
    qtbot.waitUntil(lambda: not view.dataSource.runningParsers, timeout=15000)

    # An `endLoad` never delivered would leave the occurrence in flight, and the
    # guard would then refuse it for the rest of the session.
    asking(view, EQUILIBRIUM)
    delivered(qtbot, view, EQUILIBRIUM)
    assert len(view.signalsList) == ONE_SLICE
    assert (view.ids_roots_occurrence['%s/%d' % (EQUILIBRIUM, OCCURRENCE)]
            .text(0) == 'occurrence 0 [displaying first time slice]')


# --------------------------------------------------------------------------
# The scripting api, which asks for the thread rather than taking it by default
# --------------------------------------------------------------------------

def test_the_scripting_api_builds_the_tree_before_returning_when_no_thread_is_asked(
        api):
    view = opening(api)

    api.LoadIDSData(view, MAGNETICS, OCCURRENCE)

    assert len(view.signalsList) == MAGNETICS_SIGNALS
    assert view.dataSource.runningParsers == set()
    assert visibleBars() == []


def test_the_scripting_api_hands_the_walk_to_a_thread_when_asked(api):
    view = opening(api)

    api.LoadIDSData(view, MAGNETICS, OCCURRENCE, threadingEvent=True)

    assert len(view.signalsList) == 0
    assert len(view.dataSource.runningParsers) == 1
