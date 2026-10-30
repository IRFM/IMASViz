# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The *File* menu of the application window.

A session is the whole screen -- every case view, every figure -- so the gesture
belongs to the window that holds them, on a bar that is on screen whatever the
user is looking at. Before this module it was on no menu at all: the two entries
were hung on the right-click pop-up of the start panel (`GUIFrame.showPopUpMenu`),
under no title, while the manual sent the user to :menuselection:`Actions --> Save
session` -- a menu that exists nowhere, in that panel or in any shot view.

The entries are asked of the menu controller the *Open* gesture was built with,
which the window hands over as `sessionMenu`. That controller is **reached and not
built**: `Viz_API` is not a singleton (`QVizOpenShotView.__init__` makes one), so a
controller of this menu's own would hold a second bookkeeping of the same windows,
and *Save session* would write an empty session while *Load session* would open
windows on an api nothing displays.

The menu is refilled every time it is opened, and not once at construction: a
session saved a minute ago belongs on the *Load session* list without restarting
the application. The shot views rebuild their menus the same way, on
`aboutToShow` (`QVizDataTreeView.addMenuBar`).

The window is held through a `weakref`, and *Quit* is connected to a method of
this object rather than to the window's own `close`: a helper kept by a Qt widget
may not hold a strong reference back through a bound method, or the widget is
freed by the cyclic collector instead of at its refcount -- and on this Qt stack a
widget freed there is freed while Qt still owes it a paint event.
"""

import weakref

from PySide6.QtGui import QAction, QKeySequence


class QVizFileMenu:
    """The *File* menu: the session of this run, and the way out."""

    TITLE = 'File'
    QUIT = 'Quit'

    def __init__(self, menu, window, sessionMenu=None):
        """
        Arguments:
            menu (QMenu) : the menu this object builds. It stays owned by whoever
                added it to its bar; this object only fills it.

            window (QMainWindow) : the application window. Held weakly, and asked
                for one thing -- to close itself, so the confirmation and whatever
                the close does still run.

            sessionMenu (callable) : `menuSession(menu, listenerWidget)`, the two
                session entries as the menu controller that owns the api of the
                session draws them. None while the start window holds no
                controller -- the menu then says *Quit* and nothing else, rather
                than dying in a menu bar.
        """
        self.menu = menu
        self._window = weakref.ref(window)
        self._sessionMenu = sessionMenu

    def show(self):
        """Hang the menu on the bar and keep it filled.

        Connected here and not at construction, so an object built to be thrown
        away -- a probe, a test -- cannot leave a slot on a live menu.
        """
        self.menu.aboutToShow.connect(self.refresh)
        self.refresh()
        return self

    def refresh(self):
        """Refill the menu as the folder and the window are now.

        What is taken out is deleted with its sub-menu: `QMenu.clear()` removes
        the actions and keeps the objects, and those parented on the menu would
        pile up on it -- one more pair for every opening -- while the sub-menu
        would stay a child nobody can reach.
        """
        for action in list(self.menu.actions()):
            submenu = action.menu()
            self.menu.removeAction(action)
            action.deleteLater()
            if submenu is not None:
                submenu.deleteLater()
        if self._window() is None:
            return
        if self._sessionMenu is not None:
            self._sessionMenu(self.menu, self.menu)
        action_quit = QAction(self.QUIT, self.menu)
        action_quit.setShortcut(QKeySequence.Quit)
        action_quit.triggered.connect(self.quit)
        self.menu.addAction(action_quit)

    def entries(self):
        """The titles on the menu, in the order they are drawn."""
        return [action.text() for action in self.menu.actions()]

    def subMenu(self, title):
        """The sub-menu of that title, or None when there is none.

        The *Load session* sub-menu is on the menu only once a session has been
        saved, so its absence is an answer and not a gap.
        """
        for action in self.menu.actions():
            submenu = action.menu()
            if submenu is not None and submenu.title() == title:
                return submenu
        return None

    def quit(self):
        """Close the application window -- its close event asks the way out does.

        Asked of the weak reference, so this object never keeps the window alive;
        a window that is gone answers nothing rather than raising.
        """
        window = self._window()
        if window is None:
            return False
        window.close()
        return True
