# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The life of a figure window, from the menu that shows it to the menu that
closes it.

Show/hide and delete are the only way a user gets rid of a window they did not
open themselves, so what is pinned here is the whole span: the menu when nothing
is open, the lines it offers once three kinds are drawn, what one line changes on
screen, and what a deletion leaves in the two registries the menu is built from.
Measured on the reference case (``west`` 54924, ``equilibrium`` occurrence 0,
**3 368** signals), the commands handed out ``SlicesPlot1``, ``TablePlotView:1``
and ``StackedPlotView:1``, and with no figure open the *Windows* menu came back
disabled with **0** line.

Three measured properties of this path are worth naming before they are pinned.

Hiding acts on the MDI window, and only when the widget's top-level window is
found for what it *is*: the code used to ask ``frame.window().objectName() ==
"IMASViz root window"``, and a bare :class:`QMdiArea` does not answer that.
Measured on such a bare area, the entry did nothing at all -- the frame and its
subwindow stayed invisible through two triggers. So the session here is built the
way the application builds it: a :class:`QMainWindow` carrying that object name,
with the MDI area inside it, and the bare-area case is driven on purpose by
``test_showHide_and_delete_act_on_the_window_under_any_MDI_area``.

Deleting takes the figure out of *both* registries (``figureframes`` and
``figToNodes``), but the ``QMdiSubWindow`` it hides stays a child of the area
until ``deleteLater`` runs, so a window count right after a delete still lists it
-- hidden. And the number of a deleted figure is only given back when its kind is
empty: deleting the middle of ``SlicesPlot1..3`` left the next curve at
``SlicesPlot4``, while deleting the only table view put the next one back at
``TablePlotView:1``.

Closing a window with its own box is a third gesture, and since T52 it is not the
same as deleting: it hides, and the window keeps the key the menu addresses it
by. That half belongs to ``test_86``, which drives it for the three families of
window; what stays here is that a hidden figure is still a figure -- the same
key, the same registries, and its own line on the menu, unchecked.

One gesture is not reproducible here: the ``QInputDialog`` that asks for a time
slice index, and the modal ``exec_()`` of the tree's context menu. The menu is
therefore built and its actions triggered, which is what the click does once the
menu is on screen.
"""

import pytest

from PySide6.QtWidgets import (QMainWindow, QMenu, QMdiArea, QMdiSubWindow,
                               QWidget)

from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizGUI.VizGUICommands.VizDataLoading.QVizLoadOccurrence \
    import QVizLoadOccurrence
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
    import QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizWindowMenu import \
    QVizWindowMenu
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsSlices \
    import QVizPlotAsSlices
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsStacked \
    import QVizPlotAsStacked
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable \
    import QVizPlotAsTable
from imasviz.VizUtils import FigureTypes
from imasviz.Viz_API import Viz_API

from conftest import (CASE_DATA_DICTIONARY_VERSION, CASE_URI,
                      case_uri_or_skip)
from support import ownership

IDS_NAME = 'equilibrium'
OCCURRENCE = 0
SIGNALS = 3368
IP = 'equilibrium.time_slice[0].global_quantities.ip'
TIME = 'equilibrium.time'
ROOT_WINDOW = 'IMASViz root window'

# What the three commands answered for this selection, in the namespaces the
# menus address them by.
CURVE_KEY = FigureTypes.CURVEPLOTTYPE + '1'
TABLE_KEY = FigureTypes.TABLEPLOTTYPE + '1'
STACKED_KEY = FigureTypes.STACKEDPLOTTYPE + '1'

DELETE = QVizWindowMenu.DELETE
ALL = QVizWindowMenu.ALL

# The menu walks the kinds in FigureTypes.MENU_ORDER and lists only the ones with
# an open window. The order they arrive in is pinned in test_30_figure_registry,
# not here.
pytestmark = [pytest.mark.case, pytest.mark.dd, pytest.mark.ui]


class Session:
    """One application session, driven through the menu of its shot view.

    The root window carries the object name the api used to compare against:
    without it the hide entry changes nothing on screen, which is the first
    number this file measured. Everything the session builds is handed to
    :func:`support.ownership.keep`, because a frame the harness drops can be
    painted after it is gone.
    """

    def __init__(self, root, api, view):
        self.root = root
        self.api = api
        self.view = view

    def select(self, *names):
        QVizSelectNodes(self.view).unselectAll()
        for name in names:
            assert QVizSelectNodes(self.view).selectNode(self.leaf(name),
                                                         self.view) is True

    def leaf(self, name):
        for node in self.view.signalsList:
            if node.getDataName() == name:
                return node
        raise AssertionError('"%s" is not a leaf of this tree (%d signals)'
                             % (name, len(self.view.signalsList)))

    def draw(self, commandClass, *names):
        """One "Plot the selection to a new window" entry, then embedded as a click.

        The three commands do not answer alike: the slices command hands back the
        list of windows it drew, the table and the stacked windows come back one
        at a time. Normalised here, because the click does not care either.
        """
        self.select(*names)
        drawn = commandClass(dataTreeView=self.view).execute()
        frames = drawn if isinstance(drawn, list) else [drawn]
        for frame in frames:
            self.api.addPlotWidgetToMDI(frame)
        return frames

    def menu(self):
        """The *Windows* menu, as a menu bar fills it -- on ``aboutToShow``."""
        menu = QMenu()
        ownership.keep(menu)
        QVizWindowMenu(menu, self.api).show()
        return menu

    def windows(self):
        """The MDI windows holding a figure the api knows about."""
        return [window for window in self.root.findChildren(QMdiSubWindow)
                if window.widget() is not None
                and self.api.GetFigureKeyOf(window.widget()) is not None]


@pytest.fixture(scope='module')
def session(qapp):
    """The reference case, one occurrence loaded, on a real root window."""
    if case_uri_or_skip() is None:
        pytest.skip('reference case not reachable: %s' % CASE_URI)
    root = QMainWindow()
    root.setObjectName(ROOT_WINDOW)
    mdi = QMdiArea(root)
    ownership.keep(root)
    api = Viz_API(parent=mdi)
    ownership.keep(api)
    source = QVizDataSourceFactory().create(CASE_URI)
    source.dd_version = CASE_DATA_DICTIONARY_VERSION
    view = api.CreateDataTree(source).dataTreeView
    api.ShowDataTree(view)
    QVizLoadOccurrence(dataTreeView=view, idsName=IDS_NAME,
                       occurrence=OCCURRENCE, asynch=False).execute()
    assert len(view.signalsList) == SIGNALS
    root.show()
    qapp.processEvents()
    return Session(root, api, view)


def subNamed(menu, title):
    for action in menu.actions():
        if action.text() == title and action.menu() is not None:
            return action.menu()
    raise AssertionError('no %r submenu in %r'
                         % (title, [a.text() for a in menu.actions()]))


def actNamed(menu, title):
    for action in menu.actions():
        if action.text() == title:
            return action
    raise AssertionError('no %r entry in %r'
                         % (title, [a.text() for a in menu.actions()]))


def titles(menu):
    return [action.text() for action in menu.actions()]


def windowTitles(menu):
    """The lines that name a window, the fixed entries of the menu left out.

    The shot view of the session is one of those lines -- the *Windows* menu
    lists the case views and the figures together -- so a test that counts
    figures says so by naming the case first.
    """
    fixed = (QVizWindowMenu.SHOW_ALL, QVizWindowMenu.HIDE_ALL, DELETE,
             QVizWindowMenu.NEXT, QVizWindowMenu.PREVIOUS)
    return [action.text() for action in menu.actions()
            if not action.isSeparator() and action.text() not in fixed]


def caseTitle(session):
    """The line the session's own case view is named by."""
    return session.view.dataSource.getLongLabel()


def allOf(menu, figureKey):
    """The *All* line of the group that figureKey opens in the *Delete* menu.

    The groups are separated, not nested, and a group opens with the line of its
    first window -- so the key says which group is meant.
    """
    groups, current = {}, None
    for action in subNamed(menu, DELETE).actions():
        if action.isSeparator():
            current = None
        elif current is None:
            current = action.text()
            groups[current] = []
        if action.text() == ALL:
            groups[current].append(action)
    if figureKey not in groups or not groups[figureKey]:
        raise AssertionError('no %r line for the group of %r in %r'
                             % (ALL, figureKey, titles(subNamed(menu, DELETE))))
    return groups[figureKey][0]


# --------------------------------------------------------------------------
# Nothing open yet
# --------------------------------------------------------------------------

def test_with_no_figure_open_the_menu_names_the_case_view_it_holds(session, qapp):
    menu = session.menu()

    # Nothing has been drawn yet, but the session does hold a window: the case
    # view is a window like any other, and this is the only menu that names it.
    # An empty run leaves the entry on the bar, disabled and holding no line --
    # which is `test_86`, on a session with no case at all.
    assert windowTitles(menu) == [caseTitle(session)]
    assert menu.isEnabled() is True
    assert session.api.figureframes == {}


# --------------------------------------------------------------------------
# Three kinds drawn, and what the menu offers for them
# --------------------------------------------------------------------------

def test_the_three_kinds_are_registered_under_their_own_prefix(session, qapp):
    session.draw(QVizPlotAsSlices, IP, TIME)
    session.draw(QVizPlotAsTable, IP, TIME)
    session.draw(QVizPlotAsStacked, IP)

    assert session.api.GetFiguresKeys(FigureTypes.CURVEPLOTTYPE) == [CURVE_KEY]
    assert session.api.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE) == [TABLE_KEY]
    assert session.api.GetFiguresKeys(FigureTypes.STACKEDPLOTTYPE) == \
        [STACKED_KEY]
    # The nodes a figure holds are recorded next to the figure, under the same
    # key: the "add to this figure" entries read them back from there.
    assert sorted(session.api.figToNodes) == sorted(session.api.figureframes)
    assert len(session.windows()) == 3


def test_the_menu_holds_one_line_per_figure_and_delete_groups_them(qapp,
                                                                  session):
    menu = session.menu()
    delete = subNamed(menu, DELETE)

    # One line per window, at the top level, checked because the window is on the
    # screen: the state of the window is the state of its line, which is the half
    # the old ``Show/Hide`` menu never said.
    assert windowTitles(menu) == [caseTitle(session), TABLE_KEY, STACKED_KEY,
                              CURVE_KEY]
    for action in menu.actions():
        if action.text() in (TABLE_KEY, STACKED_KEY, CURVE_KEY):
            assert action.isCheckable() and action.isChecked()

    # Deleting is the other question, so it is its own sub-menu: one line per
    # window and one *All* per kind, which is what the old ``Delete`` menu did
    # without listing every window twice.
    assert titles(delete) == [caseTitle(session), ALL, '',
                              TABLE_KEY, ALL, '', STACKED_KEY, ALL, '',
                              CURVE_KEY, ALL]


# --------------------------------------------------------------------------
# Hiding, triggered the way the click triggers it
# --------------------------------------------------------------------------

def test_hiding_takes_the_mdi_window_and_the_figure_with_it(session, qapp):
    frame = session.api.figureframes[CURVE_KEY]
    window = frame.parent()
    assert window in session.windows() and window.isVisible()

    actNamed(session.menu(), CURVE_KEY).trigger()
    qapp.processEvents()
    assert window.isVisible() is False
    assert frame.isVisible() is False

    # The line now says what the screen says, because the menu is redrawn on
    # every opening.
    assert actNamed(session.menu(), CURVE_KEY).isChecked() is False

    actNamed(session.menu(), CURVE_KEY).trigger()
    qapp.processEvents()
    assert window.isVisible() is True
    assert frame.isVisible() is True

    # Hiding is a view of the figure, not a change of state: the registries are
    # what they were, so the figure can be hidden and shown again.
    assert session.api.GetFiguresKeys(FigureTypes.CURVEPLOTTYPE) == [CURVE_KEY]


def test_showHide_and_delete_act_on_the_window_under_any_MDI_area(qapp):
    # Measured before this was fixed: the branch was chosen on the *name* of the
    # top-level window ("IMASViz root window"), so on a plain MDI area -- which
    # the application does not build, but a plugin and every test do -- both
    # entries acted on the frame instead of the window it sits in. Show/Hide
    # left an empty window on screen (frame hidden, subwindow still visible,
    # twice over), and Delete closed the frame and left the window visible.
    # The frame is a stand-in: this is about which window an entry addresses,
    # not about what a frame draws.
    area = QMdiArea()
    area.resize(600, 400)
    ownership.keep(area)
    api = Viz_API(parent=area)
    ownership.keep(api)
    frame = QWidget()
    api.figureframes['SlicesPlot1'] = frame
    api.addPlotWidgetToMDI(frame)
    area.show()
    qapp.processEvents()
    window = frame.parent()
    assert window.isVisible() and frame.isVisible()
    # The name that used to decide all of this says the area is not the root.
    assert frame.window().objectName() != ROOT_WINDOW

    api.ShowHideFigure('SlicesPlot1')
    qapp.processEvents()
    assert window.isVisible() is False
    assert frame.isVisible() is False

    api.ShowHideFigure('SlicesPlot1')
    qapp.processEvents()
    assert window.isVisible() is True and frame.isVisible() is True

    api.DeleteFigure('SlicesPlot1')
    qapp.processEvents()
    assert api.figureframes == {}
    assert window.isVisible() is False


# --------------------------------------------------------------------------
# Deleting one figure
# --------------------------------------------------------------------------

def test_deleting_a_figure_takes_it_out_of_both_registries(session, qapp):
    frame = session.api.figureframes[CURVE_KEY]
    ownership.keep(frame)
    window = frame.parent()
    other = session.api.figureframes[TABLE_KEY]

    actNamed(subNamed(session.menu(), DELETE), CURVE_KEY).trigger()
    qapp.processEvents()

    assert CURVE_KEY not in session.api.figureframes
    assert CURVE_KEY not in session.api.figToNodes
    # The two other kinds are untouched, and the table is still on screen.
    assert session.api.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE) == [TABLE_KEY]
    assert other.isVisible()
    # The window is hidden and scheduled for deletion, not destroyed here: it is
    # still a child of the area, and it is no longer a figure the api knows.
    assert window.isVisible() is False
    assert session.api.GetFigureKeyOf(frame) is None


def test_a_deleted_figure_is_offered_no_more(session, qapp):
    assert windowTitles(session.menu()) == [caseTitle(session), TABLE_KEY,
                                            STACKED_KEY]


def test_deleting_all_of_a_kind_leaves_the_other_kind(session, qapp):
    stacked = session.api.figureframes[STACKED_KEY]
    ownership.keep(stacked)

    allOf(session.menu(), STACKED_KEY).trigger()
    qapp.processEvents()

    assert session.api.GetFiguresKeys(FigureTypes.STACKEDPLOTTYPE) == []
    assert session.api.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE) == [TABLE_KEY]


# --------------------------------------------------------------------------
# The numbers a figure is addressed by
# --------------------------------------------------------------------------

def test_the_number_of_a_figure_in_the_middle_is_not_given_back(session, qapp):
    session.draw(QVizPlotAsSlices, IP)
    session.draw(QVizPlotAsSlices, IP)
    keys = session.api.GetFiguresKeys(FigureTypes.CURVEPLOTTYPE)
    assert keys == ['SlicesPlot1', 'SlicesPlot2'], keys
    assert session.api.GetNextKeyForFigure(FigureTypes.CURVEPLOTTYPE) == \
        'SlicesPlot3'

    middle = keys[0]
    ownership.keep(session.api.figureframes[middle])
    actNamed(subNamed(session.menu(), DELETE), middle).trigger()
    qapp.processEvents()

    # The key is how the menu addresses a figure, so a number already handed to a
    # live figure cannot be handed twice: the next curve is one past the highest
    # still open, not the first hole.
    assert session.api.GetFiguresKeys(FigureTypes.CURVEPLOTTYPE) == \
        ['SlicesPlot2']
    assert session.api.GetNextKeyForFigure(FigureTypes.CURVEPLOTTYPE) == \
        'SlicesPlot3'


def test_a_kind_emptied_by_a_delete_hands_its_number_to_the_next_figure(session,
                                                                       qapp,
                                                                       caplog):
    keys = session.api.GetFiguresKeys(FigureTypes.CURVEPLOTTYPE)
    for key in keys:
        ownership.keep(session.api.figureframes[key])
        actNamed(subNamed(session.menu(), DELETE), key).trigger()
    qapp.processEvents()
    assert session.api.GetFiguresKeys(FigureTypes.CURVEPLOTTYPE) == []

    drawn = session.draw(QVizPlotAsSlices, IP)
    qapp.processEvents()

    # Nothing of that kind is left, so the numbering starts over: measured, the
    # new curve is SlicesPlot1 again, and the window title says the same.
    assert session.api.GetFiguresKeys(FigureTypes.CURVEPLOTTYPE) == \
        [FigureTypes.CURVEPLOTTYPE + '1']
    assert drawn[0].parent().windowTitle() == FigureTypes.CURVEPLOTTYPE + '1'


def test_the_X_of_a_window_hides_it_and_keeps_its_key(session, qapp):
    key = session.api.GetFiguresKeys(FigureTypes.TABLEPLOTTYPE)[0]
    frame = session.api.figureframes[key]
    ownership.keep(frame)
    window = frame.parent()

    window.close()
    qapp.processEvents()

    # The box is the user's gesture for "get this out of my way", and a figure
    # costs a read of the case to redraw, so it hides. The key stays with the
    # window: the menu still names it, unchecked, and clicking the line puts it
    # back. Measured before the rule, the box left ``figureframes`` empty, the
    # window hidden inside the area, and the next figure of that kind was handed
    # this key again -- two windows under one name, one of them unreachable.
    assert key in session.api.figureframes
    assert key in session.api.figToNodes
    assert session.api.GetNextKeyForFigure(FigureTypes.TABLEPLOTTYPE) != key
    # The menu still names the window, and says that it is off the screen.
    assert key in windowTitles(session.menu())
    assert actNamed(session.menu(), key).isChecked() is False

    actNamed(session.menu(), key).trigger()
    qapp.processEvents()
    assert window.isVisible() is True


def test_deleting_a_key_that_is_no_longer_registered_costs_nothing(session,
                                                                  qapp,
                                                                  caplog):
    keys = sorted(session.api.figureframes)
    before = dict(session.api.figureframes)

    # A menu built before another entry deleted the figure still holds its
    # action. Triggering it must not raise out of the slot, and must not touch
    # the figures that are open.
    session.api.DeleteFigure('TablePlotView:99')
    qapp.processEvents()

    assert sorted(session.api.figureframes) == keys
    assert session.api.figureframes == before
    assert sorted(session.api.figToNodes) == keys
