# Copyright holders : Commissariat à l'Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The Windows menu, the case-level gestures, and the MDI layout modes.

The user's complaint was a pile of windows when several cases are open, and the
professional answer for that pile is a management of them that speaks in the
language the case is already spoken in -- the URI. A case and the figures it
serves are grouped together in the menu, a figure that serves several cases is
in each case's group (the shared-figure case), a case-less plugin window stays
where it is, and a whole case can be isolated, closed, or moved out of the
way in one gesture.

The layout modes (windowed/tabbed/tiled/cascaded) are applied by the MDI area
and persisted through the same preferences file that already holds the theme
and the close-button rule. Refusals -- no MDI to lay out, an unknown mode --
are named, not silent, because a layout mode that quietly does nothing is
indistinguishable from one that did.

These tests pin the group logic, the gestures, and the layout modes with a
plain api (no case, no imas) so the invariants are checked without a case.
"""

import pytest
from PySide6.QtWidgets import QMenu, QWidget

from imasviz.Viz_API import Viz_API
from imasviz.VizUtils import QVizPreferences
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizWindowMenu import \
    QVizWindowMenu


URI_A = 'imas:hdf5?path=/x/a/3/1/0'
URI_B = 'imas:hdf5?path=/x/b/3/2/1'
URI_U = 'imas:mdsplus?user=g2lfleur;database=JT60SA;shot=957;run=0;version=3'


class FakeDataSource:
    def __init__(self, uri):
        self.uri = uri
        self._forgot = False
    def getLongLabel(self):
        return 'URI:' + self.uri
    def forget_case(self):
        self._forgot = True


class FakeDataTreeView:
    def __init__(self, uri):
        self.dataSource = FakeDataSource(uri)


class FakeCaseView(QWidget):
    def __init__(self, uri):
        super().__init__()
        self.dataTreeView = FakeDataTreeView(uri)
        self.hide()
        self.show()


def makeApi(qapp=None, cases=None, figures=None, shared=None):
    """An api with fake case views and figures to test against.

    `cases`: list of URIs to be its case-views.
    `figures`: dict figureKey -> list of URIs it serves.
    `shared`: dict figureKey -> (uriA, uriB) -- a figure serving two.
    """
    api = Viz_API(parent=None)
    for uri in (cases or ()):
        frame = FakeCaseView(uri)
        api.DTVframeList.append(frame)
        api.DTVlist.append(frame.dataTreeView)
    for key, uris in (figures or {}).items():
        frame = QWidget()
        frame.hide()
        frame.show()
        api.figureframes[key] = frame
        api.figToNodes[key] = {
            str(i): (uri, None) for i, uri in enumerate(uris)
        }
    for key, (ua, ub) in (shared or {}).items():
        frame = QWidget()
        frame.hide()
        frame.show()
        api.figureframes[key] = frame
        api.figToNodes[key] = {1: (ua, None), 2: (ub, None)}
    return api


# ---- Preference and layout modes

def test_layoutMode_accepts_the_shipped_modes():
    assert QVizPreferences.layoutMode('windowed') == 'windowed'
    assert QVizPreferences.layoutMode('tabbed') == 'tabbed'
    assert QVizPreferences.layoutMode('tiled') == 'tiled'
    assert QVizPreferences.layoutMode('cascaded') == 'cascaded'


def test_layoutMode_refuses_a_mode_the_mdi_does_not_wear():
    with pytest.raises(ValueError, match='not a view'):
        QVizPreferences.layoutMode('diagonal')


@pytest.mark.parametrize('written, expected', [
    ('Mdi_view_mode=tabbed\n', 'tabbed'),
    ('Mdi_view_mode=windowed\n', 'windowed'),
    ('Mdi_view_mode=cascaded\n', 'cascaded'),
])
def test_pref_parses_the_layout_mode(tmp_path, monkeypatch, written, expected):
    monkeypatch.setenv('HOME', str(tmp_path))
    (tmp_path / '.imasviz').mkdir(parents=True, exist_ok=True)
    (tmp_path / '.imasviz/preferences').write_text(written)
    QVizPreferences.userPreferencesInitialized = False
    QVizPreferences.Mdi_view_mode = 'windowed'
    QVizPreferences().build()
    assert QVizPreferences.Mdi_view_mode == expected


def test_pref_refuses_and_keeps_the_current_layout(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    (tmp_path / '.imasviz').mkdir(parents=True, exist_ok=True)
    (tmp_path / '.imasviz/preferences').write_text('Mdi_view_mode=diagonal\n')
    QVizPreferences.userPreferencesInitialized = False
    QVizPreferences.Mdi_view_mode = 'tiled'
    QVizPreferences().build()
    # Refused: the mode the file typed was never written, and the one it
    # was read in front of survives.
    assert QVizPreferences.Mdi_view_mode == 'tiled'


def test_mdiLayout_refuses_when_there_is_no_mdi(qapp):
    api = Viz_API(parent=None)
    with pytest.raises(ValueError, match='No MDI'):
        api.mdiLayout('tabbed')


def test_mdiLayout_changes_the_mode_and_writes_the_pref(qapp, monkeypatch):
    from PySide6.QtWidgets import QMdiArea
    mdi = QMdiArea()
    api = Viz_API(parent=mdi)
    from imasviz.Viz_API import QVizMdiSubWindow
    w = QVizMdiSubWindow(api)
    w.resize(100, 100)
    mdi.addSubWindow(w)
    w.show()
    monkeypatch.setattr(QVizPreferences, 'Mdi_view_mode', 'windowed')
    api.mdiLayout('tabbed')
    assert mdi.viewMode() == QMdiArea.TabbedView
    assert QVizPreferences.Mdi_view_mode == 'tabbed'
    api.mdiLayout('tiled')
    assert mdi.viewMode() == QMdiArea.SubWindowView
    assert QVizPreferences.Mdi_view_mode == 'tiled'
    api.mdiLayout('windowed')
    assert mdi.viewMode() == QMdiArea.SubWindowView
    assert QVizPreferences.Mdi_view_mode == 'windowed'


# ---- The per-window record

def test_case_view_record_carrys_its_uri(qapp):
    api = Viz_API(parent=None)
    api.DTVframeList.append(FakeCaseView(URI_A))
    [record] = api.openWindows()
    assert record.cases == (URI_A,)


def test_figure_record_carrys_every_uri_it_serves(qapp):
    api = makeApi(cases=[], figures={'SlicesPlot1': [URI_A, URI_B]})
    [record] = api.openWindows()
    assert record.cases == (URI_A, URI_B)


def test_plugin_window_record_serves_no_case(qapp):
    # A case view and a figure that draws no node: the figure is real, has a
    # key, but serves no URI because nothing in figToNodes references one.
    # The record still carries an empty case set.
    api = makeApi(cases=[URI_A], figures={'SlicesPlotX': []})
    records = api.openWindows()
    [record] = [r for r in records if r.label == 'SlicesPlotX']
    assert record.cases == ()


def test_casesServedBy_answers_every_origin_a_figure_kept(qapp):
    api = makeApi(cases=[], shared={'SlicesPlot1': (URI_A, URI_B)})
    [frame] = api.figureframes.values()
    assert api.casesServedBy(frame) == (URI_A, URI_B)


# ---- The gestures

def test_isolateCase_shows_its_case_and_shared_hides_the_rest(qapp):
    api = makeApi(
        cases=[URI_A, URI_B],
        figures={'SlicesPlot1': [URI_A]},
        shared={'SlicesPlot2': (URI_A, URI_B)})
    # After isolateCase(URI_A), everything that doesn't serve URI_A is
    # hidden, and everything that does -- including the shared figure --
    # stays shown.
    api.isolateCase(URI_A)
    frames = {
        'caseA': api.DTVframeList[0],
        'caseB': api.DTVframeList[1],
        'figA': api.figureframes['SlicesPlot1'],
        'figAB': api.figureframes['SlicesPlot2'],
    }
    assert not frames['caseA'].isHidden()
    assert frames['caseB'].isHidden()
    assert not frames['figA'].isHidden()
    assert not frames['figAB'].isHidden()


def test_isolateCase_the_other_case_reverses(qapp):
    api = makeApi(
        cases=[URI_A, URI_B],
        figures={'SlicesPlot1': [URI_A]},
        shared={'SlicesPlot2': (URI_A, URI_B)})
    api.isolateCase(URI_A)
    api.isolateCase(URI_B)
    frames = {
        'caseA': api.DTVframeList[0],
        'caseB': api.DTVframeList[1],
        'figA': api.figureframes['SlicesPlot1'],
        'figAB': api.figureframes['SlicesPlot2'],
    }
    assert frames['caseA'].isHidden()
    assert not frames['caseB'].isHidden()
    assert frames['figA'].isHidden()
    assert not frames['figAB'].isHidden()


def test_the_case_gestures_do_not_leave_a_blank_shell(qapp):
    """A show that only shows the shell strands a white window.

    The user's report: after *Show only this case*, windows the gesture is
    meant to put back come back as an empty ``QMdiSubWindow`` -- a title bar
    over a blank body -- and they never come back whole, *all over the run*.
    That is the one state a show that forgets its own frame cannot repair.

    ``showHideWindow`` (the *Windows* line) already re-shows the frame after
    showing its shell; the case gestures go through ``setWindowVisible`` and
    did not, which is why the gesture built to hide a case and bring it back
    was the one that stranded the blank shell. This pins that a case gesture
    that puts a window back restores the *frame*, not only the shell.
    """
    from PySide6.QtWidgets import QMdiArea
    from imasviz.Viz_API import QVizMdiSubWindow

    mdi = QMdiArea()
    mdi.show()
    api = Viz_API(parent=mdi)
    frame = QWidget()
    sub = QVizMdiSubWindow(api)
    sub.setWidget(frame)
    mdi.addSubWindow(sub)
    sub.show()
    frame.show()
    api.figureframes['SlicesPlot1'] = frame
    api.figToNodes['SlicesPlot1'] = {0: (URI_A, None)}
    qapp.processEvents()

    # The stranded state a window ends in when a hide reached the frame while
    # the shell stayed up -- exactly the white window on screen.
    frame.hide()
    qapp.processEvents()
    assert sub.isVisible() and not frame.isVisible()

    api.isolateCase(URI_A)
    qapp.processEvents()
    assert sub.isVisible(), 'putting the case back must bring the window back'
    assert frame.isVisible(), 'a show must restore the frame, not strand its shell'


def test_hideOthers_keeps_only_the_one_named(qapp):
    api = makeApi(cases=[URI_A, URI_B], figures={'SlicesPlot1': [URI_A]})
    exceptFrame = api.figureframes['SlicesPlot1']
    for frame in api.DTVframeList:
        frame.show()
    exceptFrame.show()
    api.hideOthers(exceptFrame)
    assert onlyVisible(frames=[api.DTVframeList[0], exceptFrame,
                               api.DTVframeList[1]], except_=exceptFrame)


def test_closeOthers_closes_everything_but_the_one_named(qapp):
    api = makeApi(cases=[URI_A, URI_B], figures={'SlicesPlot1': [URI_A]})
    exceptFrame = api.figureframes['SlicesPlot1']
    api.closeOthers(exceptFrame)
    # The one named stays, the rest are out of the bookkeeping.
    assert exceptFrame in api.figureframes.values()
    assert len(api.DTVframeList) == 0
    assert 'SlicesPlot1' in api.figureframes


def test_closeCase_closes_its_view_and_its_own_figures(qapp):
    api = makeApi(
        cases=[URI_A, URI_B],
        figures={'SlicesPlotA': [URI_A]},
        shared={'SlicesPlotAB': (URI_A, URI_B)})
    figAB = api.figureframes['SlicesPlotAB']
    api.closeCase(URI_A)
    # The case view and the figure that only serves URI_A are gone.
    assert API_caseViewURI(api, URI_A) is None
    assert 'SlicesPlotA' not in api.figureframes
    # The shared figure is hidden, not closed: its key stays.
    assert 'SlicesPlotAB' in api.figureframes
    assert figAB is not None
    assert api.figureframes['SlicesPlotAB'] is figAB


def onlyVisible(frames, except_):
    for frame in frames:
        if frame is except_:
            continue
        if not frame.isHidden():
            return False
    return True


def API_caseViewURI(api, uri):
    for frame in api.DTVframeList:
        if frame.dataTreeView.dataSource.uri == uri:
            return frame
    return None


# ---- The menu

def test_menu_groups_cases_first_and_has_gestures(qapp):
    from imasviz.VizDataSource.QVizIMASDataSource import caseLabel
    api = makeApi(
        cases=[URI_A, URI_B],
        figures={'SlicesPlotA': [URI_A]},
        shared={'SlicesPlotAB': (URI_A, URI_B)})
    win_menu = QMenu()
    ctrl = QVizWindowMenu(win_menu, api, applicationBar=True)
    ctrl.refresh()
    # One sub-menu per case URI, found by the case's label (not by position:
    # the *Delete* and *Disposition* sub-menus sit on the bar too).
    subMenus = {a.text(): a.menu() for a in win_menu.actions()
                if a.menu() is not None}
    assert caseLabel(URI_A) in subMenus
    assert caseLabel(URI_B) in subMenus
    # One line is the shared figure's: it is drawn once per case that serves.
    for uri in (URI_A, URI_B):
        labels = [x.text() for x in subMenus[caseLabel(uri)].actions()]
        assert 'SlicesPlotAB' in labels
    # Each case's sub-menu carries the two case gestures.
    for uri in (URI_A, URI_B):
        labels = [x.text() for x in subMenus[caseLabel(uri)].actions()]
        assert QVizWindowMenu.ISOLATE in labels
        assert QVizWindowMenu.CLOSE_CASE in labels


def test_menu_disposition_on_the_app_bar(qapp, monkeypatch):
    api = makeApi(cases=[URI_A], figures={'SlicesPlotA': [URI_A]})
    win_menu = QMenu()
    ctrl = QVizWindowMenu(win_menu, api, applicationBar=True)
    ctrl.refresh()
    found = False
    for a in win_menu.actions():
        if a.menu() is not None and a.text() == QVizWindowMenu.DISPOSITION:
            found = True
            modes = [x.text() for x in a.menu().actions()]
            assert modes == ['Windows', 'Tabs', 'Tiled', 'Cascaded']
    assert found


def test_menu_disposition_not_on_a_shotview_bar(qapp):
    api = makeApi(cases=[URI_A], figures={'SlicesPlotA': [URI_A]})
    win_menu = QMenu()
    ctrl = QVizWindowMenu(win_menu, api, applicationBar=False)
    ctrl.refresh()
    for a in win_menu.actions():
        assert not (a.menu() is not None and
                    a.text() == QVizWindowMenu.DISPOSITION)


def test_menu_with_no_cases_stays_flat(qapp):
    # A plugin-style window with no case: the menu has no case sub-menus and no
    # case gestures, just the top-level window line and the *All* gestures.
    api = makeApi(cases=[], figures={'SlicesPlot1': []})
    win_menu = QMenu()
    ctrl = QVizWindowMenu(win_menu, api, applicationBar=True)
    ctrl.refresh()
    labels = [a.text() for a in win_menu.actions()]
    assert 'SlicesPlot1' in labels
    assert QVizWindowMenu.ISOLATE not in labels
    assert QVizWindowMenu.CLOSE_CASE not in labels
