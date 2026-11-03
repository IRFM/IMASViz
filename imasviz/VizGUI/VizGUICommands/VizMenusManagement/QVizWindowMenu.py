# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The *Windows* menu: one line per window the run holds.

Before this module the question "which windows are open, and is this one on the
screen?" was answered in three places, none of them complete:

* the right-click pop-up of the *start panel* held the case views -- the only
  place in the application able to bring a hidden case view back, on a panel
  that looks like a form and is not where anyone looks for a menu;
* the right-click pop-up of a *signal node* held the figures;
* the shot view's ``Plot windows`` menu bar entry held the figures too.

So a user had to know which *kind* of window they were after before knowing
where to look, and the figures were listed twice over -- once under
``Show/Hide``, once under ``Delete`` -- with a sub-menu per kind in each. Two
consequences of that shape were worse than the navigation: hiding the last case
view takes its menu bar off the screen with it, which leaves no gesture at all
for a figure that is hidden; and nothing on screen said whether the window a
line named was shown or hidden, which is why the manual has a sentence warning
that clicking one does the other.

This menu answers both once. One line per window, checked when it is on the
screen, and the click toggles it -- the state is the line. Case views and
figures share the list, grouped by kind with a separator, so the one question a
user asks ("where is my window?") has one place to be asked. Closing a window
for good is a ``Delete`` sub-menu, which keeps what today's menus do best --
deleting every window of one kind at a time -- without listing anything twice.

Two hang points, one object: the application menu bar (on screen whatever the
user is looking at, which is the argument that moved the session entries to
``File``, T46) and each shot view's menu bar, where the gesture was. They cannot
drift apart because they are filled by this same class from the same answer --
``Viz_API.openWindows()``.

The menu is refilled on ``aboutToShow`` and not built once, like the *File*
menu: a figure drawn a minute ago belongs on the list without restarting the
application. What it replaces is deleted by :func:`refill` -- ``QMenu.clear()``
would keep the sub-menus parented on it and pile up a branch nobody can reach.

The api is held weakly. On a shot view this menu hangs in a menu bar the frame
owns, and the api holds that frame: a strong reference either way is a cycle
through a Qt widget, which is freed on the cyclic collector while Qt still owes
it a paint event.
"""

import logging
import weakref
from functools import partial

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMenu, QStyle

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMenuRefill import refill
from imasviz.VizUtils import GlobalIcons, QVizPreferences


class QVizWindowMenu:
    """The list of windows, drawn from the api that holds them."""

    TITLE = 'Windows'
    SHOW_ALL = 'Show all'
    HIDE_ALL = 'Hide all'
    DELETE = 'Delete'
    ALL = 'All'
    DISPOSITION = 'Disposition'
    ISOLATE = 'Show only this case'
    CLOSE_CASE = 'Close this case'
    HIDE_OTHERS = 'Hide others'
    CLOSE_OTHERS = 'Close others'
    NEXT = 'Next window'
    PREVIOUS = 'Previous window'

    def __init__(self, menu, api, applicationBar=False):
        """
        Arguments:
            menu (QMenu) : the menu this object fills. It stays owned by the bar
                it hangs on.

            api (Viz_API) : the bookkeeping the windows live in -- held weakly,
                and asked on every opening rather than once, so a menu is never
                a second list of windows that disagrees with the first.

            applicationBar (bool) : whether this is the menu of the application
                window. Only that one carries the keyboard entries: two actions
                with the same shortcut in one top-level window make both
                ambiguous, and neither fires. And *next window* is a question
                about the MDI area, which is not what a shot view's bar is for.
        """
        self.menu = menu
        # A shot view can be built with no api at all -- the tree view's own
        # constructor takes None there, and the tests that walk a tree alone hand
        # it. Such a view holds no bookkeeping, so the honest answer is the one
        # the menu already gives for an api that went away: no window, a disabled
        # entry. ``weakref.ref(None)`` would answer TypeError instead.
        self._api = weakref.ref(api) if api is not None else lambda: None
        self.applicationBar = applicationBar

    def show(self):
        """Hang the menu on its bar and keep it filled.

        Connected here and not at construction, so an object built to be thrown
        away -- a probe, a test -- cannot leave a slot on a live menu.
        """
        self.menu.aboutToShow.connect(self.refresh)
        self.refresh()
        return self

    # -------------------------------------------------------------- the drawing
    def refresh(self):
        """Draw the menu as the windows are now, grouped by case first.

        The *Windows* menu is where the question "which windows are open, and
        how do I get a handle on them?" is asked, and it is asked about a run
        that holds several cases at once -- so the windows are grouped by the
        case (URI) that owns them, not by the figure kind the flat list used to
        show. A case and its figures sit together in one sub-menu; a figure that
        serves several cases sits in each of them (the shared figure case); a
        window a plugin drew, which serves no case, stays at the top level. The
        *All* gestures act on the run, the *Disposition* sub-menu acts on the
        MDI area, and the *Delete* sub-menu still closes by kind.
        """
        refill(self.menu)
        windows = self.windows()
        # A bar entry that appears and disappears is a target that moves under
        # the hand, so on a bar the entry stays and says there is nothing in it:
        # no window to manage, no gesture to offer -- including the *Disposition
        # sub-menu, which rearranges windows that are already on the screen, and
        # which has nothing to rearrange yet. The layout a future case opens into
        # is set from the preferences file, not from this menu.
        self.menu.setEnabled(bool(windows))
        if not windows:
            return

        caseUris = []
        for record in windows:
            for uri in record.cases:
                if uri not in caseUris:
                    caseUris.append(uri)
        for uri in caseUris:
            self.caseMenu(uri, windows)
        for record in windows:
            if not record.cases:
                self.menu.addAction(self.lineFor(record))

        if windows:
            self.menu.addSeparator()

        for title, slot in ((self.SHOW_ALL, self.showAll),
                            (self.HIDE_ALL, self.hideAll),
                            (self.HIDE_OTHERS, self.hideOthers),
                            (self.CLOSE_OTHERS, self.closeOthers)):
            action = QAction(title, self.menu)
            action.triggered.connect(slot)
            self.menu.addAction(action)

        if windows:
            self.deleteMenu(windows)
        if self.applicationBar:
            self.dispositionMenu()
            self.menu.addSeparator()
            for title, keys, slot in ((self.NEXT, 'Ctrl+Tab', self.nextWindow),
                                      (self.PREVIOUS, 'Ctrl+Shift+Tab',
                                       self.previousWindow)):
                action = QAction(title, self.menu)
                action.setShortcut(QKeySequence(keys))
                action.triggered.connect(slot)
                self.menu.addAction(action)

    def caseMenu(self, uri, windows):
        """One sub-menu per case URI, with the gestures that case owns.

        The windows a record serves are in this sub-menu, in the same
        kind order they would hold in the flat listing they replace. The two
        case gestures (*Show only this case* and *Close this case*) act on the
        URI: a figure that serves this case and another stays shown when
        *Show only this case* is picked, and is hidden -- not closed -- when
        *Close this case* is picked. The header is the case's short label
        (`caseLabel`) and the whole URI is in the tooltip. `caseLabel` is
        imported here and not at module load: it lives in ``VizDataSource``,
        which the tree view imports from this module -- a top-level import
        would be a cycle that stops the very first import.
        """
        from imasviz.VizDataSource.QVizIMASDataSource import caseLabel
        sub = QMenu(caseLabel(uri), self.menu)
        sub.setToolTip(uri)
        lastKind = None
        for record in windows:
            if uri not in record.cases:
                continue
            if lastKind is not None and record.kindLabel != lastKind:
                sub.addSeparator()
            lastKind = record.kindLabel
            sub.addAction(self.lineFor(record))
        sub.addSeparator()
        action = QAction(self.ISOLATE, sub)
        action.setToolTip('Show this case, hide every other case')
        action.triggered.connect(partial(self.isolate, uri))
        sub.addAction(action)
        action = QAction(self.CLOSE_CASE, sub)
        action.setToolTip('Close this case for good; shared figures hidden, kept')
        action.triggered.connect(partial(self.closeCase, uri))
        sub.addAction(action)
        self.menu.addMenu(sub)

    def lineFor(self, record):
        """One window: checked while it is on the screen, and the click bounces it."""
        action = QAction(record.label, self.menu)
        action.setCheckable(True)
        action.setChecked(record.visible())
        self.setIcon(action, record.iconLabel)
        action.setToolTip('%s window: %s' % (record.kindLabel, record.label))
        action.triggered.connect(partial(self.showHide, record))
        return action

    def deleteMenu(self, windows):
        """The windows that can be closed for good, in groups by kind.

        One line per window and one ``All`` per kind, which is what today's
        ``Delete`` menu does -- and what it will be the only way to do, now that
        the close box hides by default.
        """
        menu = QMenu(self.DELETE, self.menu)
        menu.setIcon(GlobalIcons.getStandardQIcon(QApplication,
                                                  QStyle.SP_DialogDiscardButton))
        for kindLabel, records in self.grouped(windows):
            for record in records:
                action = QAction(record.label, menu)
                self.setIcon(action, record.iconLabel)
                action.setToolTip('Close the %s window %s for good'
                                  % (kindLabel, record.label))
                action.triggered.connect(partial(self.closeOne, record))
                menu.addAction(action)
            action = QAction(self.ALL, menu)
            action.setToolTip('Close every %s window' % kindLabel.lower())
            action.triggered.connect(partial(self.closeKind, kindLabel))
            menu.addAction(action)
            menu.addSeparator()
        while menu.actions() and menu.actions()[-1].isSeparator():
            menu.removeAction(menu.actions()[-1])
        self.menu.addMenu(menu)

    def setIcon(self, action, iconLabel):
        if iconLabel is None:
            return
        icon = GlobalIcons.getCustomQIcon(QApplication, iconLabel)
        if icon is not None:
            action.setIcon(icon)

    # ----------------------------------------------------------- what is open
    def windows(self):
        """Every window the api holds, or nothing if the api is gone."""
        api = self._api()
        return api.openWindows() if api is not None else []

    def grouped(self, windows):
        """The same windows, in groups of one kind each, in the menu's order."""
        groups = []
        for record in windows:
            if not groups or groups[-1][0] != record.kindLabel:
                groups.append((record.kindLabel, []))
            groups[-1][1].append(record)
        return groups

    # ---------------------------------------------------------------- gestures
    def showHide(self, record):
        """Bounce one window between the screen and off it."""
        api, frame = record.api(), record.frame()
        if api is None or frame is None:
            return False
        return api.showHideWindow(frame)

    def showAll(self):
        for record in self.windows():
            if not record.visible():
                self.showHide(record)

    def hideAll(self):
        for record in self.windows():
            if record.visible():
                self.showHide(record)

    def closeOne(self, record):
        """Close one window for good: out of the screen, the bookkeeping, the session."""
        api, frame = record.api(), record.frame()
        if api is None or frame is None:
            return False
        return api.closeWindow(frame)

    def closeKind(self, kindLabel):
        """Close every window of one kind -- what the old ``All`` line did."""
        for record in self.windows():
            if record.kindLabel == kindLabel:
                self.closeOne(record)

    def isolate(self, uri):
        """Show this case and its figures, hide every other case's windows."""
        api = self._api()
        if api is None:
            return
        api.isolateCase(uri)

    def closeCase(self, uri):
        """Close this case for good; its shared figures hidden, not closed."""
        api = self._api()
        if api is None:
            return
        api.closeCase(uri)

    def activeFrame(self):
        """The frame behind the window the user is looking at, or None.

        *Hide/Close others* act on "the one I am working in", and the MDI area
        answers that with its active sub-window -- the tab, the window in front,
        or the window with the keyboard focus, whichever mode the area wears.
        No active window is a gesture with nothing to leave behind, so it is
        refused, not spent.
        """
        api = self._api()
        mdi = api.getMDI() if api is not None else None
        if mdi is None:
            return None
        sub = mdi.activeSubWindow()
        if sub is None:
            return None
        return sub.widget()

    def hideOthers(self):
        """Hide every window except the one on the screen the user is in."""
        api = self._api()
        frame = self.activeFrame()
        if api is None or frame is None:
            return
        api.hideOthers(frame)

    def closeOthers(self):
        """Close every window except the one on the screen the user is in."""
        api = self._api()
        frame = self.activeFrame()
        if api is None or frame is None:
            return
        api.closeOthers(frame)

    def dispositionMenu(self):
        """The *Disposition* sub-menu: how the MDI area lays its windows out.

        Four checkable lines, the one the preference currently answers checked.
        The choice is written to the preference as the user changes it, so the
        next start-up opens the first case into the layout they last left.
        """
        sub = QMenu(self.DISPOSITION, self.menu)
        modes = (('windowed', 'Windows'),
                 ('tabbed', 'Tabs'),
                 ('tiled', 'Tiled'),
                 ('cascaded', 'Cascaded'))
        for mode, label in modes:
            action = QAction(label, sub)
            action.setCheckable(True)
            action.setChecked(QVizPreferences.Mdi_view_mode == mode)
            action.setToolTip('Lay every window out as %s' % label.lower())
            action.triggered.connect(partial(self.layout, mode))
            sub.addAction(action)
        self.menu.addMenu(sub)

    def layout(self, mode):
        """Ask the MDI area to lay its windows out in `mode`, and remember it."""
        api = self._api()
        if api is None:
            return
        try:
            api.mdiLayout(mode)
        except ValueError as e:
            logging.getLogger('logPanel').error(str(e))

    def nextWindow(self):
        return self.activateWindow(next=True)

    def previousWindow(self):
        return self.activateWindow(next=False)

    def activateWindow(self, next):
        """Bring the next (or previous) window of the MDI area forward."""
        api = self._api()
        mdi = api.getMDI() if api is not None else None
        if mdi is None:
            return False
        if next:
            mdi.activateNextSubWindow()
        else:
            mdi.activatePreviousSubWindow()
        return True
