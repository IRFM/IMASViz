# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under it.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""A window whose object is gone, but whose bookkeeping stayed, is released.

The report this file pins: *Close this case*, called several times over, left
entries of the menu behind -- a plugin window of that case -- and the window
behind the line could not be brought back, nor taken down by any line of the
menu. Repeated *Close this case* did nothing with them, over and over.

The state is one: the window's Qt object is gone, while its registration
(``DTVframeList``/``DTVlist``/``figureframes``) stayed. The *Windows* menu is
drawn from that bookkeeping without asking whether the object is still there,
and every gesture asks ``QVizWindowRecord.frame()``, which answers ``None``
for an object Qt has already taken away: the line is drawn for ever, and
nothing -- clicking, *Close this case*, the *Delete* line -- can act on it.
The number of the next window of the kind skips the dead key for the whole
session, and a session written over the state would carry the line with it.

It is made by any path that takes a window away under a live registration:
a close interrupted between its windows (a failure inside one leaves the rest
of the case's windows unprocessed -- the user's "several times" is this loop
meeting the same state again and again), and a deletion that ran while the
registration survived. A measured fact of this Qt decided the shape of the
reproduction: destroying the parent does not take a top-level plugin window
down with it (it survives, hidden under its registration). So the dead state
is not "killed with its case" but "taken away under a registration that was
still there".

The contract pinned here, for both: the dead registration is out of the
bookkeeping and of the menu, its key is back for the next window of its kind,
a line says which window of which case was released and why, an interrupted
close still takes care of the rest of the case, and a session written over
the state raises nothing and carries no ghost.
"""

import logging

import pytest
import shiboken6
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QMainWindow, QMenu, QMdiArea, QWidget

from imasviz.Viz_API import QVizMdiSubWindow, Viz_API
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizWindowMenu import \
    QVizWindowMenu
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession import \
    QVizSaveSession
from imasviz.VizUtils import FigureTypes

URI_A = 'imas:hdf5?path=/x/a/3/1/0'
URI_B = 'imas:hdf5?path=/x/b/3/2/1'

CHART = FigureTypes.EQUILIBRIUMPLOTTYPE + '1'
FIG_A = FigureTypes.CURVEPLOTTYPE + '9'
FIG_AB = FigureTypes.CURVEPLOTTYPE + '8'

pytestmark = [pytest.mark.ui]


class FakeDataSource:
    def __init__(self, uri, refuseCaseRelease=False):
        self.uri = uri
        self.refuseCaseRelease = refuseCaseRelease
        self._forgot = False

    def getLongLabel(self):
        return 'URI:' + self.uri

    def forget_case(self):
        if self.refuseCaseRelease:
            raise RuntimeError('the entry of %s is already gone' % self.uri)
        self._forgot = True


class FakeDataTreeView:
    def __init__(self, uri, refuseCaseRelease=False):
        self.dataSource = FakeDataSource(uri, refuseCaseRelease)
        # The reading the session makes of a case; empty is a case the test
        # does not fill.
        self.IDSRoots = {}
        self.selectedSignalsDict = {}


class FakeCaseView(QWidget):
    def __init__(self, uri, refuseCaseRelease=False):
        super().__init__()
        self.dataTreeView = FakeDataTreeView(uri, refuseCaseRelease)
        # The session save reads the state of a case off the view; the fakes
        # hold an empty one.
        self.IDSRoots = {}
        self.selectedSignalsDict = {}


def makeApi(qapp=None, cases=(), figures=None, chartOn=None):
    """An api, its case views, its figures, and the plugin chart of a case.

    `chartOn` names the case view the chart is parented on, the way the
    Equilibrium chart is parented: the window stands on its own, but it is a
    child of the shot view of the case it was opened from, so it goes down
    with it whichever way the view goes.
    """
    api = Viz_API(parent=None)
    views = []
    for uri in (cases or ()):
        frame = FakeCaseView(uri)
        frame.hide()
        frame.show()
        api.DTVframeList.append(frame)
        api.DTVlist.append(frame.dataTreeView)
        views.append(frame)
    for key, uris in (figures or {}).items():
        frame = QWidget()
        frame.hide()
        frame.show()
        api.figureframes[key] = frame
        for i, uri in enumerate(uris):
            api.AddNodeToFigure(key, str(i), (uri, None))
    chart = None
    if chartOn is not None:
        chart = QMainWindow(chartOn)
        chart.hide()
        chart.show()
        api.AddNodeToFigure(CHART, 'chart', (URI_A, None))
        api.figureframes[CHART] = chart
    return api, views, chart


def takeAway(qapp, *widgets):
    """Take the C++ side of `widgets` right now, and hand back the live wrappers.

    This is the dead state itself, produced the deterministic way: measured on
    this Qt, `deleteLater` with a bare `processEvents` leaves the C++ object
    standing -- the deferred deletion is not delivered until it is sent to the
    very receiver it was posted on. `sendPostedEvents(widget,
    QEvent.DeferredDelete)` is that delivery, and after it
    `shiboken6.isValid` answers False while the Python wrapper -- which is what
    the registration still holds -- keeps answering. A widget that is not valid
    is skipped: killing a parent takes its C++ children down with it, and the
    wrapper of a child that is already gone answers none of the calls.
    """
    for widget in widgets:
        if not shiboken6.isValid(widget):
            continue
        widget.hide()
        widget.deleteLater()
        qapp.sendPostedEvents(widget, QEvent.DeferredDelete)


# ---- The reported state: released, named, and the number is back

def test_a_menu_line_with_no_window_behind_it_is_released(qapp, caplog):
    """The line is not drawn, the key is free, and the log says which case.

    The state of the report, built as the interrupted close leaves it: the
    case is out of the bookkeeping, its plugin chart is out of the C++ world,
    and the registration of the chart is the only thing keeping its line on
    the menu. Before the rule, that line was the one no gesture could take
    off: *Close this case* met it twice, did nothing to it the first time the
    object was already gone, and the next chart of the kind was numbered as
    if the dead one were still open.
    """
    mdi = QMdiArea()
    mdi.show()
    api = Viz_API(parent=None)
    viewA = FakeCaseView(URI_A)
    sub = QVizMdiSubWindow(api)
    sub.setWidget(viewA)
    mdi.addSubWindow(sub)
    sub.show()
    viewB = FakeCaseView(URI_B)
    api.DTVframeList.extend([viewA, viewB])
    api.DTVlist.extend([viewA.dataTreeView, viewB.dataTreeView])
    figAB = QWidget()
    figAB.hide()
    figAB.show()
    api.figureframes[FIG_AB] = figAB
    api.AddNodeToFigure(FIG_AB, '0', (URI_A, None))
    api.AddNodeToFigure(FIG_AB, '1', (URI_B, None))
    chart = QMainWindow(viewA)
    chart.hide()
    chart.show()
    api.AddNodeToFigure(CHART, 'chart', (URI_A, None))
    api.figureframes[CHART] = chart

    # The case and the window of the case are taken away under the live
    # registration the chart still holds: the bookkeeping of the view is out,
    # and the chart's C++ object is gone the next time an event goes by --
    # measured on this Qt, the parent's going is not what takes the window
    # down; a deletion under the registration is.
    api.DTVframeList.remove(viewA)
    api.DTVlist.remove(viewA.dataTreeView)
    sub.hide()
    takeAway(qapp, viewA, chart)
    assert not shiboken6.isValid(viewA) and not shiboken6.isValid(chart)
    assert api.figureframes.get(CHART) is chart, \
        'the dead registration is the state under test'

    with caplog.at_level(logging.WARNING, logger='logPanel'):
        windows = api.openWindows()

    assert all(shiboken6.isValid(r.frame()) for r in windows if r.frame())
    assert all(r.figureKey != CHART for r in windows), \
        'a line whose window is gone is not a line, it is the stuck entry'
    assert CHART not in api.figureframes
    assert CHART not in api.figToNodes
    assert api.GetNextKeyForFigure(FigureTypes.EQUILIBRIUMPLOTTYPE) == \
        FigureTypes.EQUILIBRIUMPLOTTYPE + '1', \
        'the number of the dead window is back for the next one of its kind'
    assert URI_A in caplog.text, \
        'the release says whose case the window was'
    assert CHART in caplog.text, 'the release names the window it let go'


def test_the_menu_draws_no_stale_line_after_a_case_is_gone(qapp):
    """The *Windows* menu of a run with a stale line: one less group, no dead line.

    The same state, read the way the user reads it -- on the bar. The group of
    the case that holds nothing but the ghost is off the menu altogether: that
    is the entry the report kept meeting. The case that still holds its window
    keeps it, and a second *Close this case* on the ghost's case costs nothing
    instead of raising.
    """
    mdi = QMdiArea()
    mdi.show()
    api = Viz_API(parent=None)
    viewA = FakeCaseView(URI_A)
    sub = QVizMdiSubWindow(api)
    sub.setWidget(viewA)
    mdi.addSubWindow(sub)
    sub.show()
    viewB = FakeCaseView(URI_B)
    api.DTVframeList.extend([viewA, viewB])
    api.DTVlist.extend([viewA.dataTreeView, viewB.dataTreeView])
    # A figure of case B alone -- the case that keeps something alive. The
    # ghost's case keeps nothing but the window that is already gone.
    figAB = QWidget()
    figAB.hide()
    figAB.show()
    api.figureframes[FIG_AB] = figAB
    api.AddNodeToFigure(FIG_AB, '0', (URI_B, None))
    chart = QMainWindow(viewA)
    chart.hide()
    chart.show()
    api.AddNodeToFigure(CHART, 'chart', (URI_A, None))
    api.figureframes[CHART] = chart

    api.DTVframeList.remove(viewA)
    api.DTVlist.remove(viewA.dataTreeView)
    sub.hide()
    takeAway(qapp, viewA, chart)
    assert not shiboken6.isValid(viewA) and not shiboken6.isValid(chart)

    menu = QMenu()
    controller = QVizWindowMenu(menu, api, applicationBar=True)
    controller.refresh()
    labels = [a.text() for a in menu.actions()]
    assert not any(CHART in label for label in labels), \
        'the stuck line is not on the menu'
    from imasviz.VizDataSource.QVizIMASDataSource import caseLabel
    # The case that holds nothing but the dead window is off the menu at all;
    # the case that still holds its window keeps it and its group.
    assert caseLabel(URI_A) not in labels
    assert caseLabel(URI_B) in labels
    # And the repeated *Close this case* on the ghost's case -- the report's
    # "several times" -- costs nothing and takes down nothing it should keep.
    api.closeCase(URI_A)
    assert FIG_AB in api.figureframes


def test_an_interrupted_close_takes_care_of_the_rest_of_the_case(qapp,
                                                                 caplog):
    """A failure on one window of the case is named, and does not strand the others.

    The case's own figure is closed, and the shared figure is hidden, whatever
    the case view's release answers -- the way the report's "several times,
    nothing moved" is made when one of the windows meets a refusal in the
    middle of the list and the loop gives up the rest with it.
    """
    api, views, chart = makeApi(
        cases=[URI_A, URI_B],
        figures={FIG_A: [URI_A], FIG_AB: (URI_A, URI_B)})
    viewA, viewB = views
    # The release of the case refuses -- the state the interrupted loop met in
    # the field -- and the close goes on after it.
    viewA.dataTreeView.dataSource.refuseCaseRelease = True

    with caplog.at_level(logging.WARNING, logger='logPanel'):
        api.closeCase(URI_A)

    uris = [view.dataTreeView.dataSource.uri for view in api.DTVframeList]
    assert URI_A not in uris
    assert viewB.dataTreeView.dataSource.uri in uris
    assert FIG_A not in api.figureframes, \
        'the figure that served the case alone is closed with it'
    figAB = api.figureframes[FIG_AB]
    assert FIG_AB in api.figureframes, \
        'the shared figure is kept, as the manual says'
    assert not figAB.isVisible(), \
        'the shared figure is hidden for the case, not closed'
    assert URI_A in caplog.text, \
        'the refusal the release met is named for the case it serves'


def test_closeOthers_and_isolate_run_over_a_stale_state(qapp):
    """The gestures that go over all the windows do not die on the dead one.

    The shared figure of the two cases stays operable once the dead
    registration is out of the bookkeeping: *Show only this case* keeps it
    for either of its two cases, and *Close others* takes down the other
    window without touching it. Before the rule, the dead registration of
    the chart was the record these loops used to die on in the middle of
    their own list -- a gesture that does half its answer and nothing more.
    """
    api, views, chart = makeApi(
        cases=[URI_A, URI_B],
        figures={FIG_AB: (URI_A, URI_B)})
    viewA, viewB = views
    chart = QMainWindow(viewA) if chart is None else chart
    chart.hide()
    chart.show()
    api.AddNodeToFigure(CHART, 'chart', (URI_A, None))
    api.figureframes[CHART] = chart
    figAB = api.figureframes[FIG_AB]
    figAB.show()

    api.DTVframeList.remove(viewA)
    api.DTVlist.remove(viewA.dataTreeView)
    takeAway(qapp, viewA, chart)
    assert not shiboken6.isValid(viewA) and not shiboken6.isValid(chart)

    api.isolateCase(URI_B)
    assert figAB.isVisible(), \
        'the gesture reaches the window that is alive, after the dead one'
    api.isolateCase(URI_A)
    assert figAB.isVisible(), \
        'the shared window serves that case too: isolating it keeps it'

    other = QWidget()
    other.hide()
    other.show()
    api.figureframes[FigureTypes.CURVEPLOTTYPE + '7'] = other
    api.AddNodeToFigure(FigureTypes.CURVEPLOTTYPE + '7', 'q', (URI_B, None))
    other.show()
    figAB.show()
    api.closeOthers(figAB)
    assert other not in api.figureframes.values()
    assert FIG_AB in api.figureframes, \
        'the named window keeps its key, whatever the dead registration cost'
    takeAway(qapp, figAB, other)


def test_a_session_written_over_a_stale_state_carries_no_ghost(tmp_path, qapp):
    """The save of a session over the state: no raise, and no line for the dead window.

    The dead chart carries the stamp a plugin leaves, which is what the save
    reads through the frame -- an object Qt has already taken away answers
    neither, and a session written over such a state died in the middle of its
    own walk, or wrote the line the restore would then meet as "already
    open". The save releases the dead registration first, so the file carries
    what is on the screen and nothing that is not.
    """
    api, views, chart = makeApi(
        cases=[URI_A, URI_B],
        figures={FIG_AB: (URI_A, URI_B)})
    viewA = views[0]
    chart = QMainWindow(viewA)
    chart.hide()
    chart.show()
    api.AddNodeToFigure(CHART, 'chart', (URI_A, None))
    api.figureframes[CHART] = chart
    # The stamp a plugin leaves -- the only thing holding the entry the restore
    # replays -- read off the frame by the session save.
    stamp = type('Stamp', (), {'uri': URI_A, 'plugin': 'equilibriumcharts',
                               'entry': 0, 'ids': 'equilibrium',
                               'occurrence': 0})()
    chart.pluginWindow = stamp

    # Both C++ sides are taken away, and the bookkeeping is exactly where the
    # interrupted close leaves it: the case and its windows still in the lists,
    # the objects gone.
    takeAway(qapp, viewA, chart)
    assert not shiboken6.isValid(viewA) and not shiboken6.isValid(chart)
    assert viewA in api.DTVframeList and CHART in api.figureframes, \
        'the dead registrations are the state under test'

    path = str(tmp_path / 'stale.vsess')
    QVizSaveSession(api, path=path).execute()
    text = open(path, encoding='utf-8').read()
    assert CHART not in text, \
        'the session is what is on the screen, not its bookkeeping'
    assert URI_B in text, 'the case that is still open is in it'
