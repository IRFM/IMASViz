# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import logging
from functools import partial
from PySide6.QtWidgets import (QWidget, QApplication, QMenu, QStyle,
                               QTreeWidget, QTreeWidgetItem, QInputDialog)
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal
from imasviz.VizUtils import GlobalIcons
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import QVizSessionFile
from imasviz.VizGUI.VizGUICommands.VizOpenViews.QVizOpenShotView import QVizOpenShotView
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession import QVizSaveSession
from imasviz.VizGUI.VizGUICommands.VizSession.QVizRestoreSession import QVizRestoreSession

from functools import partial


class QVizMainMenuController:

    def __init__(self, parent=None):
        self.parent = parent
        self.openShotView = QVizOpenShotView(parent.getMDI())
        #self.hideAddPublicDBCommand = False

    def updateMenu(self, menu, listenerWidget):
        numWindows = len(self.openShotView.api.GetDTVFrames())
        self.menusShowHideAndDelete(numWindows, menu, listenerWidget)
        self.menuSession(menu, listenerWidget)
        #if not self.hideAddPublicDBCommand:
        self.menuAddPublicDB(menu, listenerWidget)
        self.menuAddSpecificUserDB(menu, listenerWidget)

    def menuSession(self, menu, listenerWidget):
        """Save the session, and put back one that was saved.

        *Load session* lists the sessions the folder holds rather than asking for
        a name: the point of saving a session is to come back to it without
        remembering what it was called. An empty list leaves no sub-menu on
        screen -- the same reason the Plugins sub-menu answers how many lines it
        added -- and *Save session* is still there to make the first one.
        """
        action_saveSession = QAction('Save session', listenerWidget)
        action_saveSession.triggered.connect(self.saveSession)
        menu.addAction(action_saveSession)

        sessions = QVizSessionFile.listing()
        if not sessions:
            return
        submenu_loadSession = QMenu('Load session', menu)
        menu.addMenu(submenu_loadSession)
        for name in sessions:
            action_loadSession = QAction(name, listenerWidget)
            action_loadSession.triggered.connect(partial(self.loadSession, name))
            submenu_loadSession.addAction(action_loadSession)

    def saveSession(self):
        """Ask a name, then write the session under it.

        The name is asked here, in the slot the user clicked, and not inside the
        command: a command that opens a dialog cannot be run by a script, and the
        session commands are exactly what a script would want to run. The guard
        on the name -- that it stays inside the configuration folder -- belongs
        to the format, and its refusal lands in the log panel below.
        """
        name, ok = QInputDialog.getText(self.parent, 'Save session',
                                        'Name of the session:',
                                        text=self.defaultSessionName())
        if not ok:
            return
        try:
            QVizSaveSession(self.openShotView.api, name=name).execute()
        except ValueError as e:
            logging.getLogger('logPanel').error(str(e))

    def defaultSessionName(self):
        """A name the user does not have to invent: the case of the first view."""
        frames = self.openShotView.api.GetDTVFrames()
        if not frames:
            return 'session'
        return frames[0].dataTreeView.dataSource.getShortLabel()

    def loadSession(self, name):
        """Put back the session saved under that name."""
        try:
            QVizRestoreSession(self.openShotView.api, name=name).execute()
        except ValueError as e:
            logging.getLogger('logPanel').error(str(e))

    def menuAddPublicDB(self, menu, listenerWidget):
        action_addPublicDB = QAction('Add public databases', listenerWidget)
        #action_addPublicDB.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'publicdbs'))
        action_addPublicDB.triggered.connect(self.addPublicDB)
        # Add to menu
        menu.addAction(action_addPublicDB)
        
    def menuAddSpecificUserDB(self, menu, listenerWidget):
        username = self.parent.IMASdbBrowserWidget.getActiveUsername()
        if username == "":
            return
        action_addSpecificUserDB = QAction('Add databases from user ' + username, listenerWidget)
        action_addSpecificUserDB.triggered.connect(self.addSpecificUserDB)
        # Add to menu
        menu.addAction(action_addSpecificUserDB)
        
    def menusShowHideAndDelete(self, numWindows, menu, listenerWidget):
        menu_showHide = QMenu('Show/Hide shot views', menu)
        menu_showHide.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'showHide'))
        menu_showHide.setDisabled(True)
        # Create and add empty menu to handle deletion of plot views and
        # figures
        menu_delete = QMenu('Delete', menu)
        menu_delete.setIcon(GlobalIcons.getStandardQIcon(QApplication,
                                                         QStyle.SP_DialogDiscardButton))
        menu_delete.setDisabled(True)

        if numWindows > 0:
            menu_showHide.setDisabled(False)
            menu_delete.setDisabled(False)

            # Create and add empty submenu to handle windows show/hide. The
            # submenu is built with its parent at construction: the QMenu that
            # `addMenu(title)` hands out belongs to the Python wrapper it comes
            # back in, so it is deleted as soon as this method returns and the
            # QAction is left pointing at nothing (measured: reading the
            # submenu back answers "Internal C++ object already deleted").
            submenu_showHideView = QMenu('Views', menu_showHide)
            menu_showHide.addMenu(submenu_showHideView)
            submenu_showHideView.setIcon(
                GlobalIcons.getCustomQIcon(QApplication, 'Figure'))
            # Create and add empty submenu to handle windows deletion
            subMenu_deleteView = QMenu('Views', menu_delete)
            menu_delete.addMenu(subMenu_deleteView)
            subMenu_deleteView.setIcon(
                GlobalIcons.getCustomQIcon(QApplication, 'Figure'))

            for i in range(0, numWindows):
                # --------------------------------------------------------------
                # Add menu item to show/hide existing window
                # Set action
                dtv = self.openShotView.api.GetDTVFrames()[i]
                dataSource = dtv.dataTreeView.dataSource
                actionLabel = dataSource.getLongLabel()
                action_showHide_view = QAction(actionLabel, listenerWidget)
                action_showHide_view.triggered.connect(
                    partial(self.showHideView, i))
                # Add to submenu
                submenu_showHideView.addAction(action_showHide_view)

                # --------------------------------------------------------------
                # Add menu item to delete existing window
                # Set action
                action_delete_view = QAction(actionLabel, listenerWidget)
                action_delete_view.triggered.connect(
                    partial(self.deleteView, i))
                # Add to submenu
                subMenu_deleteView.addAction(action_delete_view)

            # ------------------------------------------------------------------
            # Add menu item to delete all existing figures
            # Set action
            action_deleteAll_views = QAction('All', listenerWidget)
            action_deleteAll_views.triggered.connect(self.deleteAllViews)
            # Add to submenu
            subMenu_deleteView.addAction(action_deleteAll_views)
            # Bitmap icon
            # TODO
        menu.addMenu(menu_showHide)
        menu.addMenu(menu_delete)

    def showHideView(self, index):
        """Hide/show a shot view.
        Argument:
            index : DTV index in the openedDTVs list
        """
        frame = self.openShotView.api.GetDTVFrames()[index]
        window = self.openShotView.api.mdiWindowOf(frame)

        if window is not None:
            # Hide/Show the MDI window the frame is embedded in
            if window.isVisible():
                window.hide()
            else:
                # To show the DTV frame, closed with X button, then both MDI
                # subwindow AND the embedded frame must be shown
                window.show()
                frame.show()
        else:
            # Hide/Show the DTV frame itself (e.g. when running examples)
            if frame.isVisible():
                frame.hide()
            else:
                frame.show()

    def deleteView(self, index):
        """Remove a shot view.
        Argument:
            index : DTV index in the openedDTVs list
        """
        self.closeView(self.openShotView.api.GetDTVFrames()[index])

    def deleteAllViews(self):
        """Remove every shot view.

        The QAction that drives this is a checkable trigger: it answers with a
        `checked` flag, not with an index. The parameter this method used to
        take was therefore fed `False`, which behaved as index 0 and emptied
        the list only because the loop bound shrank with it.
        """
        for frame in list(self.openShotView.api.GetDTVFrames()):
            self.closeView(frame)

    def closeView(self, frame):
        """Take one shot view off the screen and out of the bookkeeping.

        Hiding the window is not enough: a hidden window stays in the MDI area,
        and nothing but the frame lists is left to reach it. Measured on this
        Qt stack, four openings and two deletions leave **8** windows in the
        area for **2** live views. Releasing it is safe here -- deleting one,
        deleting a second, and re-opening the case afterwards all answer no
        exception; what the old commented-out `deleteLater()` blamed on Qt is
        not a Qt bug.
        """
        window = self.openShotView.api.mdiWindowOf(frame)
        if window is not None:
            window.hide()
            window.deleteLater()
        else:
            frame.hide()
            frame.deleteLater()

        self.openShotView.api.RemoveDTVFrame(frame)

    def addPublicDB(self):
        self.parent.IMASdbBrowserWidget.addUserDB("public")

    def addSpecificUserDB(self):
        username = self.parent.IMASdbBrowserWidget.getActiveUsername()
        self.parent.IMASdbBrowserWidget.addUserDB(username)

