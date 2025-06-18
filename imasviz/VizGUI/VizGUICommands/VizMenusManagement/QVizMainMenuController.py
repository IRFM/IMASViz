# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

from functools import partial
from PySide6.QtWidgets import QWidget, QApplication, QMenu, QStyle
from PySide6.QtGui import QAction
from imasviz.VizUtils import GlobalIcons
from imasviz.VizGUI.VizGUICommands.VizOpenViews.QVizOpenShotView import QVizOpenShotView
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Signal

from functools import partial


class QVizMainMenuController:

    def __init__(self, parent=None):
        self.parent = parent
        self.openShotView = QVizOpenShotView(parent.getMDI())
        #self.hideAddPublicDBCommand = False

    def updateMenu(self, menu, listenerWidget):
        numWindows = len(self.openShotView.api.GetDTVFrames())
        self.menusShowHideAndDelete(numWindows, menu, listenerWidget)
        #if not self.hideAddPublicDBCommand:
        self.menuAddPublicDB(menu, listenerWidget)
        self.menuAddSpecificUserDB(menu, listenerWidget)

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

            # Create and add empty submenu to handle windows show/hide
            submenu_showHideView = menu_showHide.addMenu('Views')
            submenu_showHideView.setIcon(
                GlobalIcons.getCustomQIcon(QApplication, 'Figure'))
            # Create and add empty submenu to handle windows deletion
            subMenu_deleteView = menu_delete.addMenu('Views')
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
        """Hide/show a DTV.
        Argument:
            index : DTV index in the openedDTVs list
        """
        dtv = self.openShotView.api.GetDTVFrames()[index]

        if dtv.window().objectName() == "IMASViz root window":
            # Hide/Show MDI subwindow
            if dtv.parent().isVisible():
                # dtv.parent() is QMdiSubWindow
                dtv.parent().hide()
            else:
                # To show the DTV frame, closed with X button, then both MDI
                # subwindow AND the embedded frame must be shown
                dtv.show()
                dtv.parent().show()
        else:
            # Hide/Show DTVframe window (e.g. when running examples)
            if dtv.isVisible():
                dtv.window().hide()
            else:
                dtv.window().show()

    def deleteView(self, index):
        """Remove a DTV.
        Argument:
            index : DTV index in the openedDTVs list
        """
        dtv = self.openShotView.api.GetDTVFrames()[index]

        if dtv.window().objectName() == "IMASViz root window":
            # Delete MDI subwindow
            if dtv.parent().isVisible():
                # dtv.parent() is QMdiSubWindow
                dtv.parent().hide()
                # TODO: results in a bug when trying to run the delete DTV
                # feature the second time
                # dtv.parent().deleteLater()
        else:
            # Delete DTVframe window (e.g. when running examples)
            if dtv.isVisible():
                dtv.hide()
                # dtv.deleteLater()

        self.openShotView.api.RemoveDTVFrame(dtv)

    def deleteAllViews(self, index):
        """Remove a DTV.
        Argument:
            index : DTV index in the openedDTVs list
        """
        for i in range(0, len(self.openShotView.api.GetDTVFrames())):
            dtv = self.openShotView.api.GetDTVFrames()[index]
            if dtv.window().objectName() == "IMASViz root window":
                if dtv.window().isVisible():
                    dtv.parent().hide()
                    # dtv.parent().deleteLater()
            else:
                if dtv.isVisible():
                    dtv.hide()
                    # dtv.deleteLater()
            self.openShotView.api.RemoveDTVFrame(dtv)

    def addPublicDB(self):
        self.parent.IMASdbBrowserWidget.addUserDB("public")
        
    def addSpecificUserDB(self):
        username = self.parent.IMASdbBrowserWidget.getActiveUsername()
        self.parent.IMASdbBrowserWidget.addUserDB(username)
        
    def getMDI(self):
        if self.parent.getMDI() != None:
            return self.parent.getMDI()
        return None
        
