# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The harness's own rule: a plot frame a test shows must outlive that test.

This file watches the watchdog. The defect it stands against was measured, not
guessed: of the **110** plot frames a run of this suite built, **79** lost their
Python wrapper before the run ended, and **11** of those had been *shown* without
ever being closed -- the only ones Qt can still paint. The run then died with
`Fatal Python error: Segmentation fault` inside pyqtgraph's
`GraphicsView.paintEvent`, at a fixed position, in a test several files away from
the one that dropped the frame, and only under some allocation timings: adding a
single failing test to `test_20_plugins.py` was enough to pull it out, while the
files it landed in pass on their own.

What is pinned here is the shape of the rule, since the difference between the
hazard and the harmless case is narrow and easy to get wrong in either direction:
shown-then-forgotten is what kills a run; never-shown and closed-then-forgotten
are not, and an invariant that called those a defect produced **479 cascading
failures** out of a suite of 690.
"""

import gc

import pytest

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot

from support import ownership

FRAME = 'harnessOwnershipProbe'


@pytest.fixture(autouse=True)
def _watched(qapp):
    # `qapp` because these tests build real frames: without a QApplication, Qt
    # aborts the process at the first QWidget -- measured, "Fatal Python error:
    # Aborted" inside QVizCurvePlot.__init__, which reads as a crash of the very
    # thing under test.
    ownership.watchOfPlotFrames()
    return ownership


def aFrame(keepIt=False):
    """One frame, no Qt parent, named so it can be found in a report."""
    frame = QVizCurvePlot(title=FRAME)
    frame.setObjectName(FRAME)
    if keepIt:
        ownership.keep(frame)
    return frame


def forget():
    """Run the collector, as returning from a test eventually would.

    Deliberately not `def drop(frame): del frame` -- that deletes the *helper's*
    binding and leaves the caller's reference alone, so the frame stays alive and
    the hazard never happens. Measured: three tests here failed for exactly that
    reason until the helper stopped taking the widget.
    """
    gc.collect()


def deadNames():
    return [name for _, name, _ in ownership.deadFrames()]


# --------------------------------------------------------------------------
# The hazard the guard exists for
# --------------------------------------------------------------------------

def test_a_frame_that_was_shown_and_then_forgotten_is_named():
    # Shiboken deletes the C++ object when the wrapper goes and no Qt parent
    # holds it; Qt may still owe that object a paint event, and that is what
    # turns into a segfault several tests later.
    frame = aFrame()
    frame.show()
    assert deadNames() == []
    frame = None
    forget()
    dead = ownership.deadFrames()
    # A report says which class died and which test built it -- the name it is
    # recorded under is the one the widget had when it was built, which for a
    # production frame is its figure key ('TablePlotView0'), and for this probe
    # is nothing. The test file is the part that matters: the crash used to name
    # a different file entirely.
    assert [(cls, where.split('::')[0]) for cls, _, where in dead] == \
        [('QVizCurvePlot', 'tests/test_44_plot_frame_ownership.py')]
    assert 'test_44_plot_frame_ownership.py' in ownership.describe(dead)


def test_a_frame_that_was_never_shown_is_not_a_hazard():
    # Most of the 79 frames that die in a run are of this kind: built so a test
    # can read numbers out of them, never painted. Calling them a defect is what
    # made 479 tests fail at once.
    before = ownership.shownFrames()
    frame = aFrame()
    assert ownership.shownFrames() == before
    frame = None
    forget()
    assert deadNames() == []
    assert ownership.shownFrames() == before


def test_a_frame_closed_before_it_is_forgotten_is_not_a_hazard():
    # The production refusal paths do exactly this -- draw nothing, close the
    # window they had opened, take it out of figureframes -- and several tests
    # exist to check that cleanup. A hidden widget leaves the paint queue.
    frame = aFrame()
    frame.show()
    assert ownership.shownFrames() >= 1
    frame.close()
    frame = None
    forget()
    assert deadNames() == []


def test_a_frame_hidden_before_it_is_forgotten_is_not_a_hazard():
    # Closing is not the only way out of the paint queue, and `Delete` on a shot
    # view does not close anything: it hides the MDI window and asks Qt to
    # delete that window, which deletes the frames nested in it -- at a point of
    # the event loop Qt chose, not at an arbitrary one chosen by the collector.
    frame = aFrame()
    frame.show()
    frame.hide()
    frame = None
    forget()
    assert deadNames() == []


def test_the_frame_inside_a_hidden_window_counts_as_hidden():
    # What the guard has to see through: the frame is not hidden by hand, it is
    # hidden because `QWidget.hide()` sends the hide event to the children
    # recursively. Without that, deleting a shot view reports its preview plot
    # as a hazard and the rule reads as a bug in the guard.
    from PySide6.QtWidgets import QWidget
    before = ownership.hiddenFrames()
    window = QWidget()
    frame = aFrame()
    frame.setParent(window)
    window.show()
    assert frame.isVisible()
    window.hide()
    assert ownership.hiddenFrames() == before + 1
    assert deadNames() == []


# --------------------------------------------------------------------------
# What holding costs, and how the report behaves
# --------------------------------------------------------------------------

def test_a_frame_held_for_the_session_is_never_reported():
    frame = aFrame(keepIt=True)
    frame.show()
    frame = None
    forget()
    assert deadNames() == []
    # Held, and still there to be painted -- which is the point of the guard.
    # Held is not only frames: what a test keeps is often the thing that owns
    # the frame transitively (an api holding figureframes), measured -- three
    # such holders are in that list by the time this file runs, and asking one
    # for objectName answered AttributeError.
    frames = [f for f in ownership.held() if isinstance(f, QVizCurvePlot)]
    assert [f.objectName() for f in frames].count(FRAME) == 1


def test_a_hazard_is_reported_once_and_not_again_in_every_later_test():
    # Without this, the first drop would fail every remaining test on the same
    # death and the run would stop saying where it happened.
    frame = aFrame()
    frame.show()
    frame = None
    forget()
    assert len(ownership.deadFrames()) == 1
    assert ownership.deadFrames() == []


def test_the_frame_classes_are_the_ones_carrying_a_view():
    # A QVizPanel or a QVizSliceControls owns no pyqtgraph view: deleting one is
    # not what kills a run, so watching them would only add noise.
    from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPanel import QVizPanel
    assert QVizPanel not in ownership.FRAME_CLASSES
    assert QVizCurvePlot in ownership.FRAME_CLASSES


def test_the_check_runs_at_the_teardown_of_every_test():
    # The fixture is what turns the unreadable crash into a named failure. If it
    # is ever dropped, the suite goes back to dying at a fixed position with no
    # test at fault in the report -- and nothing else here would notice.
    import conftest
    marker = getattr(conftest, '_every_plot_frame_outlives_its_test', None)
    assert marker is not None
    assert marker._pytestfixturefunction.autouse is True
