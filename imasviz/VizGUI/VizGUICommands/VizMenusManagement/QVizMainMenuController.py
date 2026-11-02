# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import logging
from functools import partial
from PySide6.QtWidgets import QApplication, QMenu, QInputDialog
from PySide6.QtGui import QAction
from imasviz.VizUtils import GlobalIcons
from imasviz.VizGUI.VizConfigurations.QVizSessionFile import QVizSessionFile
from imasviz.VizGUI.VizGUICommands.VizOpenViews.QVizOpenShotView import QVizOpenShotView
from imasviz.VizGUI.VizGUICommands.VizSession.QVizSaveSession import QVizSaveSession
from imasviz.VizGUI.VizGUICommands.VizSession.QVizRestoreSession import QVizRestoreSession


class QVizMainMenuController:

    def __init__(self, parent=None):
        self.parent = parent
        self.openShotView = QVizOpenShotView(parent.getMDI())
        #self.hideAddPublicDBCommand = False

    def updateMenu(self, menu, listenerWidget):
        # The windows of the run are not here: they are on the *Windows* menu of
        # the application bar and of each shot view, filled by ``QVizWindowMenu``
        # from ``Viz_API.openWindows`` -- one list, case views and figures
        # together. This pop-up used to be the only place able to bring a hidden
        # case view back, on a panel nobody right-clicks looking for a menu.
        # The session entries are not here either: a session is the whole screen
        # -- every case view and every figure -- so it belongs to the *File* menu
        # of the application window, which is on screen whatever the user is
        # looking at (T46). This pop-up only exists on the start panel, under no
        # title, and the manual named a menu (``Actions -> Save session``) that
        # is nowhere.
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

        The caller rebuilds this on every opening of its menu, so a session saved
        a moment ago is on the list without restarting the application.
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

    def dialogParent(self):
        """The window a dialog of this controller belongs to.

        `window()` answers the top-level window a widget lives in -- the
        application window when the frame is embedded, the widget itself when it
        is not, which is how a test drives these slots. Asking the frame directly
        centres the dialog on the left panel of the start window.
        """
        if self.parent is None:
            return None
        return self.parent.window()

    def saveSession(self):
        """Ask a name, then write the session under it.

        The name is asked here, in the slot the user clicked, and not inside the
        command: a command that opens a dialog cannot be run by a script, and the
        session commands are exactly what a script would want to run. The guard
        on the name -- that it stays inside the configuration folder -- belongs
        to the format, and its refusal lands in the log panel below.
        """
        name, ok = QInputDialog.getText(self.dialogParent(), 'Save session',
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
        
    def addPublicDB(self):
        self.parent.IMASdbBrowserWidget.addUserDB("public")

    def addSpecificUserDB(self):
        username = self.parent.IMASdbBrowserWidget.getActiveUsername()
        self.parent.IMASdbBrowserWidget.addUserDB(username)

