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

from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMenuRefill import refill


class QVizFileMenu:
    """The *File* menu: the session of this run, and the way out."""

    TITLE = 'File'
    QUIT = 'Quit'
    NEW_PLUGIN = 'New plugin...'
    MANAGE = 'Plugins...'
    AGENT = 'Agent'

    def __init__(self, menu, window, sessionMenu=None):
        """
        Arguments:
            menu (QMenu) : the menu this object builds. It stays owned by whoever
                added it to its bar; this object only fills it.

            window (QMainWindow) : the application window. Held weakly, and asked
                for one thing -- to close itself, so the confirmation and whatever
                the close does still run.

            sessionMenu (callable) : `menuSession(menu, listenerWidget)`, the
                session entries -- *New session*, *Save session* and *Load
                session* -- as the menu controller that owns the api of the
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
        refill(self.menu)
        if self._window() is None:
            return
        if self._sessionMenu is not None:
            self._sessionMenu(self.menu, self.menu)

        # The two plugin entries, and both are said by name: *New plugin...* to
        # write one, *Plugins...* to look at the whole set -- what IMASViz ships
        # and what this user wrote -- and edit their own. They belong on this bar
        # because a plugin is not a gesture on one node: it is part of the session,
        # and the folder it lives in is reached whether or not a case is open.
        # And the agent, one window for the session: the LLM that drives this
        # run's gestures, opened whether or not a case is on screen -- the same
        # reason the plugin lines stay, and reached the same way.
        for title, slot in ((self.NEW_PLUGIN, self.openPluginCreator),
                            (self.MANAGE, self.openPluginManager),
                            (self.AGENT, self.openAgent)):
            action = QAction(title, self.menu)
            action.triggered.connect(slot)
            self.menu.addAction(action)

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

    def openPluginCreator(self):
        """Write a plugin of this user's own, from a name and an IDS.

        The box stays open after it writes, saying where the file went and which
        gesture runs it: the plugin is on the menu of the next right click already,
        and that is the answer to the question a user asks at that moment.
        """
        window = self._window()
        if window is None:
            return None
        from imasviz.VizPlugins.QVizPluginCreatorDialog \
            import QVizPluginCreatorDialog

        dialog = QVizPluginCreatorDialog(window)
        dialog.exec()
        watcher = getattr(window, 'pluginWatcher', None)
        if watcher is not None:
            # The folder may not have existed until this moment.
            watcher.watch()
        return dialog.created

    def openPluginManager(self):
        """Open the table of every plugin this session can offer.

        The api and the watcher are asked of the window, which is where both
        already are -- the api because it belongs to the controller the *Open*
        gesture was built with, the watcher because one watcher serves the session
        and not one per window that happens to look at the folder.
        """
        window = self._window()
        if window is None:
            return None
        from imasviz.VizPlugins.QVizPluginManager import QVizPluginManager

        manager = QVizPluginManager(
            window, apiOf=getattr(window, 'sessionApi', None),
            watcher=getattr(window, 'pluginWatcher', None))
        manager.show()
        return manager

    def openAgent(self):
        """Open the agent: the LLM that drives this session's own gestures.

        One window for the session, reached the way the *Windows* menu reaches
        its windows -- through the session's api -- so it sits on that menu
        alongside the figures the user drew. It is **reused**, not rebuilt: a
        second panel would be a second loop on the same api, and a second line
        on a menu that already named it. The first click builds it; the next
        click brings the one that is there back to the front.

        The stack it is built on is the session's own parts -- the gestures
        (`McpGuiCore`) drive the api the *Open* gesture owns, and the loop runs
        off a worker thread through the same `GuiDispatcher` the MCP surface
        uses. The LLM is **not** reached at construction: the endpoint, the
        model and the key come from `QVizPreferences` (the local llama-server by
        default), and the first turn is what connects.
        """
        window = self._window()
        if window is None:
            return None

        from imasviz.VizUtils import FigureTypes
        from imasviz.VizAgent.core import McpGuiCore
        from imasviz.VizAgent.dispatcher import GuiDispatcher
        from imasviz.VizAgent.llm_client import LLMClient
        from imasviz.VizAgent.agent import AgentLoop
        from imasviz.VizAgent.panel import QVizAgentPanel

        # The session's api, reached and not moved: the one the *Windows* menu
        # reads, so the panel lands on that menu like every other window.
        apiOf = getattr(window, 'sessionApi', None)
        api = apiOf() if callable(apiOf) else None

        if api is not None and isinstance(getattr(api, 'figureframes', None), dict):
            prefix = FigureTypes.AGENTTYPE
            for key, frame in list(api.figureframes.items()):
                if key.startswith(prefix) and isinstance(frame, QVizAgentPanel):
                    frame.show()
                    frame.raise_()
                    return frame

        core = McpGuiCore(main_window=window, api=api)
        # Built on this (GUI) thread: its signal hand-off only means something
        # where the events that drain it are pumped -- the worker that runs the
        # loop is not the one that answers. No Qt parent: the panel it serves is
        # registered in the session's figureframes, and that is the anchor that
        # keeps the panel, and then the agent and this dispatcher, together.
        dispatcher = GuiDispatcher()
        agent = AgentLoop(core, LLMClient(), dispatcher,
                          main_window=window, api=api)
        panel = QVizAgentPanel(main_window=window, api=api, agent=agent)
        panel.show()
        return panel
