# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""A *New session* that one case refuses still clears the screen of the rest.

`closeAll` is the body of *New session* on every surface the user reaches,
and it closes the case views one by one: case 1 first, then whatever is after
it. What it owed, and what the two group gestures beside it already wear
(`closeOthers` and `closeCase`), is a single window that refuses in the
middle of the run to cost no more than itself: name its refusal and go on.
`closeOthers`/`closeCase` wear that isolation (a `try`/`except` around each
`closeWindow`, a `_gestureFailed` that says which window of which case and
what it refused) — because a gesture that raised here used to abandon the
rest of the list with the failure, the same entry meeting the same dead state
on every repeated click. `closeAll` is the one that did not: a refusal of the
case the run was on its way to closing used to abort the close and leave the
windows that came after it on the screen. The field report is one of those:
two cases open, *New session*, and the case the close had not reached yet —
the second — still there.

What this file pins, on two reference cases:

* a case whose bookkeeping refuses in the middle of the close — measured here
  as one of the two cases' `forget_case` raising the way a closing entry
  answers it — is **named** in the log of the case, and the other cases of
  the run are still closed for good: the case views out of the bookkeeping,
  their windows off the screen, and the clean slate answers how many it took;
* and the gesture itself still runs — a *New session* the first case refuses
  is not one the second case never gets, which is the screen the user is owed.
"""

import logging

import pytest
from PySide6.QtWidgets import QMdiArea

from imasviz.Viz_API import Viz_API

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      RANK3_CASE_DATA_DICTIONARY_VERSION, RANK3_CASE_URI,
                      case_uri_or_skip, rank3_case_uri_or_skip)

pytestmark = [pytest.mark.case, pytest.mark.ui, pytest.mark.dd]


def twoCases(api, qapp):
    """The two reference cases the user had open, each its own view.

    Opened the way the *Open* gesture reaches `ShowDataTree`, so the frames
    register in `DTVframeList`/`DTVlist` the way a click does, and the two
    data sources are distinct objects — which is what makes refusing one
    and answering for the other a thing a real run can wear rather than a
    test fiction.
    """
    from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory

    def openOne(uri, dd):
        source = QVizDataSourceFactory().create(uri)
        source.dd_version = dd
        if api.isDataSourceAlreadyOpened(source):
            view = api.GetDTVFor(source.getKey())
        else:
            view = api.CreateDataTree(source).dataTreeView
        api.ShowDataTree(view)
        qapp.processEvents()
        return view

    first = openOne(CASE_URI, CASE_DATA_DICTIONARY_VERSION)
    second = openOne(RANK3_CASE_URI, RANK3_CASE_DATA_DICTIONARY_VERSION)
    return first, second


def aCaseOf(api, uri):
    """The case view that serves `uri`, so a test can name the one it holds."""
    for frame in api.DTVframeList:
        if getattr(frame.dataTreeView.dataSource, 'uri', None) == uri:
            return frame
    raise AssertionError('no case view for %s: %r' % (uri,
                                                     [getattr(
                                                         f.dataTreeView.dataSource,
                                                         'uri', None)
                                                      for f in api.DTVframeList]))


def visibleSubWindows(mdi):
    return [w for w in mdi.subWindowList() if w.isVisible()]


@pytest.fixture
def area(qapp, qtbot):
    mdi = QMdiArea()
    qtbot.addWidget(mdi)
    mdi.show()
    qapp.processEvents()
    yield mdi


def test_a_new_session_one_case_refuses_still_clears_the_rest(
        area, qapp, monkeypatch, caplog):
    """Two cases open, one of the closes refuses; the other is still closed.

    The refusal is worn the way a closing case can: its bookkeeping lets go
    of the case it is the last to show, and that answers an error. Measured
    here as `forget_case` raising on the first case's source. What the
    *New session* the user asked for is owed, and what this pins: the
    refusal is where the user reads it, and the second case does not stay
    on the screen for it.
    """
    if case_uri_or_skip() is None or rank3_case_uri_or_skip() is None:
        pytest.skip('a reference case is not reachable: %s / %s'
                    % (CASE_URI, RANK3_CASE_URI))

    api = Viz_API(parent=area)
    first, second = twoCases(api, qapp)
    assert api.DTVframeList and api.DTVlist, 'two cases are open on the run'

    # The first case's close answers an error in the middle of the close.
    first.frame = aCaseOf(api, CASE_URI)
    first.source = first.frame.dataTreeView.dataSource
    monkeypatch.setattr(
        first.source, 'forget_case',
        lambda: (_ for _ in ()).throw(
            ValueError('entry already closed: the case cannot be let go')))

    with caplog.at_level(logging.WARNING):
        try:
            closed = api.closeAll()
            raised = None
        except Exception as e:
            closed, raised = '?', e
    qapp.processEvents()

    if raised is not None:
        pytest.fail(
            'closeAll aborted on one case and left the run half-closed: '
            '%s: %s' % (type(raised).__name__, raised))

    # The refusal is where the user reads it.
    assert 'could not be closed' in caplog.text or \
        'entry already closed' in caplog.text, \
        'the refusing case was not named: %s' % caplog.text

    # And the clean slate is still owed in full: every case view is out of
    # the bookkeeping and off the screen, whatever the first one refused.
    assert api.DTVframeList == [], \
        'a case the close did not reach stayed on the screen: %r' % (
            [getattr(f.dataTreeView.dataSource, 'uri', None)
             for f in api.DTVframeList])
    assert api.DTVlist == [], \
        'the case views stayed in the run: %r' % api.DTVlist
    assert visibleSubWindows(area) == [], \
        'a case the close did not reach is still on the screen'


def test_two_cases_new_session_closes_both(qapp, qtbot, area):
    """The everyday shape of the fix: two cases, no refusal, both go.

    The clean slate answers with the two case views it took away and no
    window on the screen, which is the *New session* the user called.
    """
    if case_uri_or_skip() is None or rank3_case_uri_or_skip() is None:
        pytest.skip('a reference case is not reachable: %s / %s'
                    % (CASE_URI, RANK3_CASE_URI))

    api = Viz_API(parent=area)
    twoCases(api, qapp)
    assert len(api.DTVframeList) == 2

    closed = api.closeAll()
    qapp.processEvents()

    assert len(closed) == 2, 'two cases are owed, both taken away: %r' % (closed,)
    assert api.DTVframeList == [] and api.DTVlist == []
    assert visibleSubWindows(area) == [], 'no case may remain on the screen'
