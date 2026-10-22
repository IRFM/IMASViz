# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Who owns a plot frame built by a test, and the check that nobody drops it.

A frame the application builds is held by `Viz_API.figureframes` for as long as
the window it belongs to lives. A frame a *test* builds has no such holder: when
the test function returns, its last Python reference goes, Shiboken deletes the
C++ object, and Qt may still owe that object a paint event. The run then dies in
`pyqtgraph.GraphicsView.paintEvent` -- in a test several files later, at a fixed
position, and only under some allocation timings. Measured on this suite before
any of this existed: of the **110** plot frames a run built, **79** lost their
wrapper before the run ended, and **11** of those had been *shown* without ever
being closed -- the only ones that can be painted, and therefore the only real
hazards.

So the harness does what the application does: it owns what its tests build, for
the whole session (`keep`). And because a rule only followed by discipline
breaks, a passive watch (`watchOfPlotFrames`, `deadFrames`) records every frame
built -- through weak references, which keep nothing alive -- and the check runs
at the teardown of the very test that dropped it. That turns a segfault in an
unrelated file into a named failure on the test at fault.
"""

import weakref

from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizCurvePlot import QVizCurvePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizImagePlot import QVizImagePlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPlotWidget import QVizPlotWidget
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizPreviewPlot import QVizPreviewPlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizStackedPlot import QVizStackedPlot
from imasviz.VizGUI.VizPlot.VizPlotFrames.QVizTablePlot import QVizTablePlot

# The frames that carry a pyqtgraph view, i.e. the ones a paint event can be
# queued for. A QVizPanel or a QVizSliceControls owns no view: deleting one is
# not what kills a run, so they are not watched.
FRAME_CLASSES = (QVizPlotWidget, QVizCurvePlot, QVizImagePlot, QVizStackedPlot,
                 QVizTablePlot, QVizPreviewPlot)

_owners = []
_watched = []
_watchedOnce = set()


def keep(widget):
    """Keep `widget` alive for the whole session, as the application would.

    Returns it, so a test can write `frame = keep(QVizCurvePlot(...))`.
    """
    _owners.append(widget)
    return widget


def watchOfPlotFrames():
    """Start recording every frame the tests build. Idempotent.

    Only weak references are kept, so the recording cannot be what keeps a frame
    alive -- which is the difference between measuring this defect and hiding it.
    """
    for cls in FRAME_CLASSES:
        if cls in _watchedOnce:
            continue
        _watchedOnce.add(cls)
        _watch(cls)
    return _watched


def _watch(cls):
    originalInit = cls.__init__

    def __init__(self, *args, **kwargs):
        originalInit(self, *args, **kwargs)
        record = {'ref': weakref.ref(self), 'class': cls.__name__,
                  'name': self.objectName() or '-',
                  'builtDuring': _builtDuring[0], 'shown': False,
                  'closed': False, 'reported': False}
        _watched.append(record)

    cls.__init__ = __init__

    # `close()` is what makes a frame safe to forget: it hides the widget, and a
    # hidden widget is dropped from the paint queue. The production refusal paths
    # do exactly that -- draw nothing, close the window they had opened, take it
    # out of `figureframes` -- so a frame that dies after being closed is not a
    # defect, it is the cleanup those paths are tested for.
    originalClose = cls.close

    def close(self):
        _mark(self, 'closed')
        return originalClose(self)

    cls.close = close

    # Qt delivers a paint event only to a widget that became visible, so the
    # state that can crash a run is "was shown, then went away without being
    # closed". Measured: 79 of the 110 frames a run builds lose their wrapper,
    # and the ones never shown are not a hazard -- they are the harness letting
    # go of what a test was only using to read numbers from.
    originalShowEvent = cls.showEvent

    def showEvent(self, event):
        _mark(self, 'shown')
        return originalShowEvent(self, event)

    cls.showEvent = showEvent


def _mark(widget, key):
    for record in _watched:
        if record['ref']() is widget:
            record[key] = True


# Filled by the fixture below before each test runs, so a death can be blamed on
# the test that built the widget rather than the one that noticed it.
_builtDuring = ['(before any test)']


def builtDuring(nodeid):
    _builtDuring[0] = nodeid


def shownFrames():
    """How many recorded frames were shown at least once."""
    return sum(1 for record in _watched if record['shown'])


def deadFrames():
    """Frames that were shown and then died without being closed.

    Each is reported once, at the first teardown that notices it: otherwise
    every later test fails on the same death and the run stops saying anything
    useful.
    """
    dead = []
    for record in _watched:
        if record['reported'] or record['closed'] or not record['shown']:
            continue
        if record['ref']() is None:
            record['reported'] = True
            dead.append((record['class'], record['name'],
                         record['builtDuring']))
    return dead


def describe(dead):
    return '; '.join('%s %r built in %s' % (name, obj, test)
                     for name, obj, test in dead)
