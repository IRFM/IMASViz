# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The *Windows* menu, and what the close box of a window is worth.

The complaint that opened this work was about where the commands are found, not
about what they do: "the show/hide commands of a window are badly organised, I
mean the menus where those commands are found". That is not a wording problem.
Before this file the same question -- which windows are open, and is this one on
the screen? -- was answered in three places, and none of them was complete:

* the right-click pop-up of the *start panel* held the case views, through
  ``QVizMainMenuController.menusShowHideAndDelete``. It was the only place in the
  application able to bring a hidden case view back -- on a panel that looks like
  a form and is nowhere anybody right-clicks looking for a menu;
* the right-click pop-up of a *signal node* held the figures;
* the shot view's ``Plot windows`` menu bar entry held the figures too.

So a user had to know which *kind* of window they were after before knowing where
to look, and the figures were listed twice over -- once under ``Show/Hide``, once
under ``Delete`` -- with a sub-menu per kind in each. Two consequences of that
shape are worse than the navigation, and both are pinned below:

* hiding the last case view takes its menu bar off the screen with it, which
  leaves no gesture at all for a figure that is hidden. A shot view's menu cannot
  be the only way back;
* nothing on screen said whether the window a line named was shown or hidden,
  which is why the manual carries a sentence warning that clicking one of those
  entries does the opposite of what its name says.

The answer is one menu, one line per window, checked while the window is on the
screen, the click bouncing it. Case views and figures share the list, grouped by
kind, because "where is my window?" is one question. It hangs twice -- on the
application bar and on each shot view's bar -- and those two cannot drift apart,
because they are filled by one class from one answer: ``Viz_API.openWindows``.

Four measurements decided the shape.

**A refill that does not delete shows the entries twice.** ``QMenu.clear()``
removes the actions and keeps the objects, and a sub-menu built with its parent
(the only shape that survives on this PySide6 -- T0, T7, T21) stays a child of the
menu. Measured on the shot view's ``Plot windows`` entry, which called ``clear()``
and rebuilt itself three times: **7** child menus for **0** actions on a menu
meant to hold two. ``QVizMenuRefill.refill`` is what the menu fillers share now,
and the count is pinned here: one ``Delete`` sub-menu however many times the menu
is redrawn, once the deferred deletes Qt was asked for have been delivered.

**A window closed with its own box was a window nobody could reach.** Measured on
a curve figure before the rule existed: the close box left ``figureframes``
**empty**, the subwindow **hidden inside the MDI area**, and
``GetFigureKeyOf(frame)`` answering ``None`` for a frame that was still alive --
and the next curve figure of that kind was handed ``SlicesPlot1`` again. Two
windows under one name, one of them unreachable by any gesture and still holding
the case data it read. The close box hides now, and the menu says so.

**The close box is what a user reaches for when they mean "get this out of my
way"**, far more often than when they mean "throw it away" -- and a figure costs a
read of the case to redraw. So hiding is the default, and ``Close_button_deletes=1``
in :file:`~/.imasviz/preferences` puts the other answer back for the user who means
it. Both values are pinned, for the three families of window: a figure, a case view,
and the top-level window a plugin draws.

**A menu with no windows is a menu that cannot be clicked.** With nothing open the
*Windows* entry stays on the bar -- an entry that appears and disappears is a
target that moves under the hand -- disabled, holding **0** action.

The windows themselves are stand-ins. What is under test is which windows a menu
lists, what it says about each, and what the close box costs -- none of which
depends on what a frame draws. The real frames and the real case are driven
through the same menu by ``test_48`` (figures) and ``test_50`` (case views).
"""

import weakref

import pytest

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QMainWindow, QMenu, QMdiArea, QMenuBar, QWidget

from imasviz.VizGUI.QtVIZ_GUI import QVizMainWindow
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizWindowMenu import \
    QVizWindowMenu
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession import QVizSaveSession
from imasviz.VizUtils import FigureTypes
from imasviz.VizUtils.QVizGlobalValues import QVizPreferences
from imasviz.Viz_API import QVizClosableWindow, QVizMdiSubWindow, Viz_API

from support import ownership

SHOW_ALL = QVizWindowMenu.SHOW_ALL
HIDE_ALL = QVizWindowMenu.HIDE_ALL
DELETE = QVizWindowMenu.DELETE
ALL = QVizWindowMenu.ALL
DISPOSITION = QVizWindowMenu.DISPOSITION
ISOLATE = QVizWindowMenu.ISOLATE
CLOSE_CASE = QVizWindowMenu.CLOSE_CASE
HIDE_OTHERS = QVizWindowMenu.HIDE_OTHERS
CLOSE_OTHERS = QVizWindowMenu.CLOSE_OTHERS
NEXT = QVizWindowMenu.NEXT
PREVIOUS = QVizWindowMenu.PREVIOUS
SHOT_VIEW = 'Shot view'

CURVE = FigureTypes.CURVEPLOTTYPE + '1'
TABLE = FigureTypes.TABLEPLOTTYPE + '1'
CASE = 'west 54924 run 0'

pytestmark = [pytest.mark.ui]


class ADataSource:
    """The three calls ``openWindows`` and ``RemoveDTVFrame`` make of a source.

    The label is what the menu line says, so it is the answer the test cares
    about; ``forget_case`` is counted, because it is the one thing a closed case
    view costs that a hidden one does not.
    """

    def __init__(self, label):
        self.label = label
        self.forgotten = 0

    def getLongLabel(self):
        return self.label

    def forget_case(self):
        self.forgotten += 1


class ACaseView(QWidget):
    """A shot view frame, reduced to the one attribute the menu reads.

    A real ``QVizDataTreeViewFrame`` is built by ``test_50``; here the point is
    that a case view is a window like any other, so a plain widget carrying a
    ``dataTreeView`` is enough to drive the menu and the close box -- the box
    belongs to the ``QVizMdiSubWindow`` it is embedded in, not to the frame.
    """

    def __init__(self, label):
        super().__init__()
        self.dataTreeView = type('View', (), {'dataSource': ADataSource(label)})()


class APluginWindow(QVizClosableWindow, QMainWindow):
    """A window a plugin draws: registered like a figure, top level on screen.

    ``QVizProfilePanel`` is the production one (``test_85``, ``test_69``). What
    the close rule needs of such a window is the mix-in and ``windowApi()``, and
    that is what this stand-in carries.
    """

    def __init__(self, api):
        super().__init__()
        self._api = weakref.ref(api)

    def windowApi(self):
        return self._api()


class Session:
    """One run's worth of windows, and the menu that lists them.

    A bare ``QMdiArea`` rather than the application's root window: since T19 the
    window an entry addresses is found by asking what a frame's parent *is*, not
    what it is called, so the menu behaves the same on both -- and ``test_48``
    pins that on the real root window.
    """

    def __init__(self, qapp, applicationBar=True):
        self.area = ownership.keep(QMdiArea())
        self.api = ownership.keep(Viz_API(parent=self.area))
        self.menu = ownership.keep(QMenu())
        self.win = QVizWindowMenu(self.menu, self.api,
                                  applicationBar=applicationBar).show()
        ownership.keep(self.win)
        self.area.resize(800, 600)
        self.area.show()
        qapp.processEvents()

    # ---------------------------------------------------------------- windows
    def figure(self, key):
        """One figure frame, embedded and shown the way a plot command does it."""
        frame = ownership.keep(QWidget())
        self.api.figureframes[key] = frame
        self.api.addPlotWidgetToMDI(frame)
        return frame

    def caseView(self, label):
        """One shot view, embedded in the window class ``ShowDataTree`` uses."""
        frame = ACaseView(label)
        ownership.keep(frame)
        self.api.DTVframeList.append(frame)
        self.api.DTVlist.append(frame.dataTreeView)
        window = QVizMdiSubWindow(self.api)
        ownership.keep(window)
        window.setWidget(frame)
        self.area.addSubWindow(window)
        window.show()
        frame.show()
        return frame

    def pluginWindow(self, key):
        """One plugin window: registered in the api, never in the MDI area."""
        frame = APluginWindow(self.api)
        ownership.keep(frame)
        self.api.figureframes[key] = frame
        frame.show()
        return frame

    # ------------------------------------------------------------------ reading
    def lines(self, menu=None):
        """What a menu offers: ``(title, checked)``, separators left out."""
        actions = (menu if menu is not None else self.menu).actions()
        return [(a.text(), a.isChecked()) for a in actions if not a.isSeparator()]

    def windowLines(self, menu=None):
        """The lines that name a window, the fixed entries left out.

        The fixed entries are the same titles every run draws alongside the
        window lines -- the *All* / *Hide/Close others* gestures, the *Delete*
        and *Disposition* sub-menus, and (only inside a case's sub-menu) the
        two case gestures -- so a test about the windows does not have to repeat
        them to say what changed.
        """
        fixed = (SHOW_ALL, HIDE_ALL, DELETE, NEXT, PREVIOUS,
                 HIDE_OTHERS, CLOSE_OTHERS, DISPOSITION, ISOLATE, CLOSE_CASE)
        return [(title, checked) for title, checked in self.lines(menu)
                if title not in fixed]

    def entries(self, menu=None):
        """Every action title, separators spelled as ``''`` -- the drawing itself."""
        return [(a.text(), a.isChecked())
                for a in (menu if menu is not None else self.menu).actions()]

    def subMenu(self, title, menu=None):
        for action in (menu if menu is not None else self.menu).actions():
            if action.text() == title and action.menu() is not None:
                return action.menu()
        raise AssertionError('no %r sub-menu in %r'
                             % (title, [a.text() for a in
                                        (menu if menu is not None
                                         else self.menu).actions()]))

    def line(self, title, menu=None):
        for action in (menu if menu is not None else self.menu).actions():
            if action.text() == title:
                return action
        raise AssertionError('%r is not a line of %r'
                             % (title, [a.text() for a in
                                        (menu if menu is not None
                                         else self.menu).actions()]))

    def redrawn(self):
        """The menu as its ``aboutToShow`` slot would draw it now."""
        self.win.refresh()
        return self

    def windowOf(self, frame):
        return self.api.mdiWindowOf(frame)

    def released(self, qapp):
        """Let Qt finish the deletions it deferred, so a count is honest.

        ``processEvents`` alone leaves a released window in ``subWindowList()``
        (measured in T21: **2** where the honest answer is **1**).
        """
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        qapp.processEvents()


@pytest.fixture
def session(qapp):
    """A fresh run: no window open, the menu on the application bar."""
    return Session(qapp)


@pytest.fixture(autouse=True)
def closeBoxKeepsTheWindow(monkeypatch):
    """The default of the application, whatever a test before this one tried.

    ``Close_button_deletes`` is module state read off :file:`~/.imasviz`, so a
    test that turns it on has to leave it off the way the user finds it.
    """
    monkeypatch.setattr(QVizPreferences, 'Close_button_deletes', 0)


# --------------------------------------------------------------------------
# One menu, one line per window
# --------------------------------------------------------------------------

def test_one_line_per_window_grouped_by_kind(session, qapp):
    session.caseView(CASE)
    session.figure(CURVE)
    session.figure(TABLE)
    session.redrawn()

    # A case view first -- it is what the screen is standing on -- then the
    # figures in ``FigureTypes.MENU_ORDER`` order, a separator marking each
    # change of kind. No sub-menu to open before knowing what is on screen.
    assert session.windowLines() == [(CASE, True), (TABLE, True),
                              (CURVE, True)]
    assert [kind.kindLabel for kind in session.api.openWindows()] == \
        [SHOT_VIEW, 'TablePlotView', 'SlicesPlot']
    delete = session.subMenu(DELETE)
    assert [title for title, _ in session.lines(delete)] == [CASE, ALL, TABLE,
                                                             ALL, CURVE, ALL]
    # The state is the line: every window on the screen is checked.
    assert all(checked for _, checked in session.windowLines())


def test_a_hidden_window_is_the_same_line_unchecked_and_a_click_brings_it_back(
        session, qapp):
    frame = session.figure(CURVE)
    session.redrawn()
    window = session.windowOf(frame)
    assert window.isVisible() and session.line(CURVE).isChecked()

    session.line(CURVE).trigger()
    qapp.processEvents()
    assert window.isVisible() is False
    assert frame.isVisible() is False

    session.redrawn()
    assert session.windowLines() == [(CURVE, False)]
    assert [title for title, _ in session.lines()] == [CURVE, SHOW_ALL, HIDE_ALL,
                                                       HIDE_OTHERS, CLOSE_OTHERS,
                                                       DELETE, DISPOSITION, NEXT,
                                                       PREVIOUS]
    # Hiding is not closing: the window is still registered, still listed, and
    # its key is still its own.
    assert session.api.figureframes == {CURVE: frame}
    assert session.api.GetFigureKeyOf(frame) == CURVE

    session.line(CURVE).trigger()
    qapp.processEvents()
    assert window.isVisible() is True and frame.isVisible() is True


def test_the_check_mark_follows_the_window_and_not_the_other_way_round(session,
                                                                      qapp):
    """The line reports the screen; it does not own it.

    A window taken off the screen by its own close box, or by a gesture that
    never went through the menu, is the same unchecked line -- which is the half
    the old menus never said.
    """
    frame = session.figure(CURVE)
    session.windowOf(frame).hide()
    session.redrawn()
    assert session.line(CURVE).isChecked() is False
    assert session.api.figureframes == {CURVE: frame}


def test_show_all_and_hide_all_move_every_window_at_once(session, qapp):
    frames = [session.caseView(CASE), session.figure(CURVE),
              session.figure(TABLE)]
    session.redrawn()

    session.line(HIDE_ALL).trigger()
    qapp.processEvents()
    assert all(session.windowOf(f).isVisible() is False for f in frames)
    # Nothing was closed: every key is still handed out, so *Show all* answers
    # the same windows and not a redraw of what they were reading.
    assert sorted(session.api.figureframes) == sorted([CURVE, TABLE])
    assert len(session.api.DTVframeList) == 1

    session.redrawn().line(SHOW_ALL).trigger()
    qapp.processEvents()
    assert all(session.windowOf(f).isVisible() for f in frames)
    session.redrawn()
    assert [checked for title, checked in session.lines()
            if title in (CASE, CURVE, TABLE)] == [True, True, True]


def test_the_menu_of_a_shot_view_lists_the_same_windows(session, qapp):
    """Two hang points, one answer -- which is what keeps them from drifting.

    Hiding a case view takes its menu bar off the screen with it, so the shot
    view's menu can never be the only place the windows are listed; and a user
    working inside one case wants the list where their eyes are.
    """
    session.caseView(CASE)
    session.figure(CURVE)
    viewBar = ownership.keep(QMenu())
    QVizWindowMenu(viewBar, session.api).show()
    session.redrawn()
    assert session.windowLines(viewBar) == session.windowLines()
    # The keyboard entries belong to the application bar alone: two actions with
    # the same shortcut inside one top-level window make both ambiguous.
    assert NEXT not in [title for title, _ in session.lines(viewBar)]
    assert NEXT in [title for title, _ in session.lines()]


def test_with_no_window_open_the_entry_stays_and_is_disabled(session, qapp):
    assert session.entries() == []
    assert session.menu.isEnabled() is False
    # A bar entry that appears and disappears moves the target under the hand, so
    # the entry is there and says there is nothing in it.
    assert session.menu.findChildren(QMenu) == []


def test_a_view_held_by_no_api_gets_an_empty_menu_and_not_an_error(qapp):
    """``QVizDataTreeView`` accepts an api of ``None``, and hangs this menu anyway.

    Measured on the first full run of this file's feature: building a shot view
    that way raised ``TypeError: cannot create weak reference to 'NoneType'
    object`` out of ``addMenuBar``, so the view did not exist at all -- thirteen
    tests of three other files died on a menu question none of them asked.
    """
    menu = QMenu()
    ownership.keep(menu)
    QVizWindowMenu(menu, None).show()

    assert menu.actions() == []
    assert menu.isEnabled() is False


def test_redrawing_the_menu_leaves_one_delete_sub_menu(session, qapp):
    """The leak the old ``Plot windows`` menu carried: one orphan branch per opening.

    ``QMenu.clear()`` removes the actions and keeps the child menus, and those
    children are what ``findChildren`` counts. Measured on the entry this
    replaces: **7** child menus for **0** actions after three refills.
    """
    session.figure(CURVE)
    for _ in range(4):
        session.redrawn()
        session.released(qapp)
    # Two sub-menus live here on a bar: *Delete* (both bars) and *Disposition*
    # (the bar only). The number is what is pinned -- it does not grow with
    # redraw -- not which one it is.
    assert [m.title() for m in session.menu.findChildren(QMenu)] == \
        [DELETE, DISPOSITION]
    assert len(session.line(DELETE).menu().actions()) == 2


def test_an_entry_of_a_menu_that_is_no_longer_current_costs_nothing(session,
                                                                   qapp):
    """A menu built a minute ago still holds its line; clicking it must not raise.

    The record holds its window weakly, and a frame released with `deleteLater`
    keeps its Python wrapper while anything else holds one -- so the weak
    reference answers an object whose C++ side is gone, and asking it anything
    answers ``RuntimeError: Internal C++ object already deleted``. The record
    asks ``shiboken6.isValid`` for exactly that case.
    """
    frame = session.figure(CURVE)
    session.redrawn()
    stale = session.line(CURVE)
    staleDelete = session.line(CURVE, session.subMenu(DELETE))
    session.api.closeWindow(frame)
    session.released(qapp)

    stale.trigger()
    staleDelete.trigger()
    qapp.processEvents()

    session.redrawn()
    assert session.entries() == []
    assert session.menu.isEnabled() is False


# --------------------------------------------------------------------------
# Delete: the only way a window goes away for good
# --------------------------------------------------------------------------

def test_deleting_takes_the_window_off_the_screen_and_out_of_the_run(session,
                                                                    qapp):
    frame = session.figure(CURVE)
    window = session.windowOf(frame)
    session.redrawn()

    session.line(CURVE, session.subMenu(DELETE)).trigger()
    session.released(qapp)

    assert session.api.figureframes == {}
    assert session.api.GetFigureKeyOf(frame) is None
    assert session.api.GetNextKeyForFigure(FigureTypes.CURVEPLOTTYPE) == CURVE
    # The window is gone from the area, not merely hidden behind it.
    assert window not in session.area.subWindowList()
    session.redrawn()
    assert session.entries() == []


def test_the_all_line_closes_every_window_of_its_kind_only(session, qapp):
    session.caseView(CASE)
    session.figure(CURVE)
    session.figure(TABLE)
    session.redrawn()

    # One group per kind, marked by a separator: the `All` of the curves is the
    # third of the three, and it closes only the curves.
    alls = [a for a in session.subMenu(DELETE).actions() if a.text() == ALL]
    assert [a.text() for a in session.subMenu(DELETE).actions()
            if not a.isSeparator()] == [CASE, ALL, TABLE, ALL, CURVE, ALL]
    alls[2].trigger()
    session.released(qapp)

    assert session.api.GetFiguresKeys(FigureTypes.CURVEPLOTTYPE) == []
    assert session.api.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE) == [TABLE]
    assert len(session.api.DTVframeList) == 1


def test_deleting_a_case_view_lets_go_of_the_case_it_was_showing(session, qapp):
    frame = session.caseView(CASE)
    source = frame.dataTreeView.dataSource
    session.redrawn()

    session.line(CASE, session.subMenu(DELETE)).trigger()
    session.released(qapp)

    assert session.api.DTVframeList == [] and session.api.DTVlist == []
    # What a closed view costs and a hidden one does not: the IDSs loaded for
    # that case go with the last view showing it.
    assert source.forgotten == 1
    assert session.area.subWindowList() == []


# --------------------------------------------------------------------------
# The close box
# --------------------------------------------------------------------------

def test_the_close_box_hides_a_figure_and_keeps_it(session, qapp):
    """The default. Measured before the rule: an unreachable window and a stolen key.

    ``figureframes`` came back empty, the subwindow stayed hidden inside the
    area, ``GetFigureKeyOf`` answered ``None`` for a live frame, and the next
    curve figure of the kind was handed ``SlicesPlot1``.
    """
    frame = session.figure(CURVE)
    window = session.windowOf(frame)
    window.close()
    session.released(qapp)

    assert window.isVisible() is False
    # The window is still in the area, still registered, still named by the menu
    # -- unchecked, which is the sentence the manual used to have to write.
    assert window in session.area.subWindowList()
    assert session.api.figureframes == {CURVE: frame}
    session.redrawn()
    assert session.windowLines() == [(CURVE, False)]
    assert [title for title, _ in session.lines()] == [CURVE, SHOW_ALL, HIDE_ALL,
                                                       HIDE_OTHERS, CLOSE_OTHERS,
                                                       DELETE, DISPOSITION, NEXT,
                                                       PREVIOUS]

    session.line(CURVE).trigger()
    qapp.processEvents()
    assert window.isVisible() is True


def test_a_window_closed_with_its_box_does_not_give_its_key_to_the_next_figure(
        session, qapp):
    frame = session.figure(CURVE)
    session.windowOf(frame).close()
    session.released(qapp)

    # The key is the identity the menu, the session file and the "add to this
    # figure" entries address a window by. Handing it out twice is how two
    # windows end up with one name and one of them unreachable.
    assert session.api.GetNextKeyForFigure(FigureTypes.CURVEPLOTTYPE) != CURVE
    assert session.api.GetFiguresKeys(FigureTypes.CURVEPLOTTYPE) == [CURVE]
    assert session.api.GetFigureKeyOf(frame) == CURVE


def test_the_close_box_of_a_case_view_hides_it_and_the_menu_puts_it_back(session,
                                                                        qapp):
    """A case view used to be a bare ``QMdiSubWindow``: its box said nothing to anyone.

    It is embedded in the same window class a figure is now, so the one rule
    reaches all three families of window.
    """
    frame = session.caseView(CASE)
    window = session.windowOf(frame)
    window.close()
    session.released(qapp)

    assert window.isVisible() is False
    assert len(session.api.DTVframeList) == 1
    assert frame.dataTreeView.dataSource.forgotten == 0
    session.redrawn()
    assert session.windowLines()[0] == (CASE, False)

    session.line(CASE).trigger()
    qapp.processEvents()
    assert window.isVisible() is True and frame.isVisible() is True


def test_a_plugin_window_follows_the_same_rule_as_a_figure(session, qapp):
    """A plugin window is registered like a figure but is not in the MDI area.

    No ``QMdiSubWindow`` sees its close box, so the rule is asked of the window
    itself -- ``QVizClosableWindow`` and the api it answers through
    ``windowApi()``.
    """
    frame = session.pluginWindow(FigureTypes.PROFILESPLOTTYPE + '1')
    frame.close()
    session.released(qapp)

    assert session.api.figureframes == \
        {FigureTypes.PROFILESPLOTTYPE + '1': frame}
    assert frame.isVisible() is False
    session.redrawn()
    assert session.windowLines() == \
        [(FigureTypes.PROFILESPLOTTYPE + '1', False)]


def test_the_preference_on_makes_the_close_box_close_for_good(session, qapp,
                                                              monkeypatch):
    """``Close_button_deletes=1``: the box does what the old one did.

    The same shape as the *Delete* line, so the two cannot disagree about what a
    closed window leaves behind.
    """
    monkeypatch.setattr(QVizPreferences, 'Close_button_deletes', 1)
    frame = session.figure(CURVE)
    view = session.caseView(CASE)
    plugin = session.pluginWindow(FigureTypes.PROFILESPLOTTYPE + '1')
    embedded = [session.windowOf(frame), session.windowOf(view)]

    session.windowOf(frame).close()
    session.windowOf(view).close()
    plugin.close()
    session.released(qapp)

    assert session.api.figureframes == {}
    assert session.api.DTVframeList == [] and session.api.DTVlist == []
    assert view.dataTreeView.dataSource.forgotten == 1
    # Both MDI windows left the area, not merely the screen: this is the *Delete*
    # line's shape, reached through the box.
    assert [w for w in embedded if w in session.area.subWindowList()] == []
    session.redrawn()
    assert session.entries() == []


# --------------------------------------------------------------------------
# The same state the session file writes
# --------------------------------------------------------------------------

def test_a_window_hidden_by_the_menu_is_the_hidden_flag_of_the_session(session,
                                                                      qapp):
    """One reading of "off the screen", so a saved session cannot lie.

    ``QVizSaveSession`` writes ``window.isHidden()`` of the window
    ``mdiWindowOf`` answers -- the same window the menu hides and the same
    window a record asks.
    """
    frame = session.figure(CURVE)
    session.redrawn()
    saver = QVizSaveSession(session.api, name='probe')
    assert saver.windowOf(CURVE, frame).hidden is False

    session.line(HIDE_ALL).trigger()
    qapp.processEvents()
    assert saver.windowOf(CURVE, frame).hidden is True


# --------------------------------------------------------------------------
# The preference, read the way the manual will write it
# --------------------------------------------------------------------------

def test_the_preferences_file_line_is_read_and_a_bad_value_is_refused_by_name(
        tmp_path, monkeypatch, caplog):
    """One bad line is not a stop, and it is not read as a third state either.

    ``Close_button_deletes=purple`` raised out of the reader before each line
    answered for itself (T48), and plain ``int()`` would read ``2`` as a value
    nothing else in the code answers.
    """
    folder = tmp_path / '.imasviz'
    folder.mkdir()
    monkeypatch.setenv('HOME', str(tmp_path))

    def read(text):
        folder.joinpath('preferences').write_text(text)
        monkeypatch.setattr(QVizPreferences, 'userPreferencesInitialized',
                            False)
        QVizPreferences().build()

    read('Close_button_deletes=1\n')
    assert QVizPreferences.Close_button_deletes == 1

    monkeypatch.setattr(QVizPreferences, 'Close_button_deletes', 0)
    read('Close_button_deletes=purple\nIgnore_GGD=1\n')
    assert QVizPreferences.Close_button_deletes == 0
    # The rest of the file is still read -- the line answers for itself.
    assert QVizPreferences.Ignore_GGD == 1
    assert 'Close_button_deletes' in caplog.text


# --------------------------------------------------------------------------
# The two hang points, in the code that hangs them
# --------------------------------------------------------------------------

class AWindow:
    """What ``QVizMainWindow.addWindowMenu`` asks of the application window.

    A plain Python object: ``QVizMainWindow()`` would be the whole application
    (start window, MDI, maximized window), as ``test_75`` says of the same
    methods. The real method is borrowed, so the wiring of the bar is what runs.
    """

    addWindowMenu = QVizMainWindow.addWindowMenu
    sessionApi = QVizMainWindow.sessionApi
    startMenuController = QVizMainWindow.startMenuController

    def __init__(self, api):
        self.bar = ownership.keep(QMenuBar())
        self.startWindow = AStartWindow(api)

    def menuBar(self):
        return self.bar


class AStartWindow:
    def __init__(self, api):
        self.central = AFrame(api)

    def centralWidget(self):
        return self.central


class AFrame:
    def __init__(self, api):
        self.mainMenuController = AController(api)


class AController:
    def __init__(self, api):
        self.openShotView = type('Open', (), {'api': api})()


def test_the_application_window_hangs_the_menu_on_its_own_bar(qapp):
    """The bar that is on screen whatever the user is looking at.

    The api is the session's own -- the one the *Open* gesture drives -- because
    a second bookkeeping would list windows that are not on screen.
    """
    area = ownership.keep(QMdiArea())
    api = ownership.keep(Viz_API(parent=area))
    area.show()
    qapp.processEvents()
    window = AWindow(api)
    window.addWindowMenu()

    assert [a.text() for a in window.bar.actions()] == [QVizWindowMenu.TITLE]
    assert window.windowMenu.applicationBar is True
    assert window.windowMenu._api() is api

    frame = ownership.keep(QWidget())
    api.figureframes[CURVE] = frame
    api.addPlotWidgetToMDI(frame)
    window.windowMenu.refresh()
    lines = [(a.text(), a.isChecked())
             for a in window.windowMenu.menu.actions() if not a.isSeparator()]
    assert lines[0] == (CURVE, True)


def test_a_shot_view_hangs_the_menu_on_its_own_bar(session, qapp):
    """``QVizDataTreeView.addMenuBar`` builds one ``QVizWindowMenu`` per view.

    Pinned at the level of the object: the view's bar used to hold a *Plot
    windows* entry that listed only the figures, next to a node pop-up that
    listed them again.
    """
    view = ownership.keep(QMenu())
    menu = QVizWindowMenu(view, session.api).show()
    ownership.keep(menu)
    session.caseView(CASE)
    session.figure(CURVE)
    menu.refresh()
    assert [t for t, _ in session.lines(view)] == [CASE, CURVE, SHOW_ALL,
                                                   HIDE_ALL, HIDE_OTHERS,
                                                   CLOSE_OTHERS, DELETE]


def test_the_menu_holds_the_api_weakly(session, qapp):
    """A helper kept by a Qt widget may not hold a strong reference back (T25).

    On a shot view the menu lives in a menu bar the frame owns and the api holds
    that frame: a strong reference either way is a cycle through a Qt widget, and
    a widget freed on the cyclic collector is freed while Qt still owes it a
    paint event.
    """
    api = Viz_API(parent=session.area)
    holder = QVizWindowMenu(ownership.keep(QMenu()), api)
    reference = weakref.ref(api)
    del api
    assert reference() is None
    # And a menu whose api is gone answers nothing rather than raising.
    assert holder.windows() == []
