
import os
import sys
import logging
from functools import partial
from PyQt5.QtWidgets import QMenuBar, QAction, QMenu, QMainWindow, QStyle, QDockWidget
from PyQt5.QtWidgets import QTabWidget, QWidget, QFormLayout, QApplication, QLineEdit, \
    QPushButton, QVBoxLayout, QComboBox, QPlainTextEdit, QGridLayout
from PyQt5.QtCore import QSize, pyqtSlot, Qt
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues, GlobalIcons, QVizPreferences
from imasviz.VizGUI.VizGUICommands.VizOpenViews.QVizOpenShotView import QVizOpenShotView

class QVizMainMenuController:

    def __init__(self, parent=None):
        self.openShotView = QVizOpenShotView(parent.getMDI())
    def updateMenu(self, menu, listenerWidget):
        numWindows = len(self.openShotView.api.GetDTVFrames())
        self.menusShowHideAndDelete(numWindows, menu, listenerWidget)

    def menusShowHideAndDelete(self, numWindows, menu, listenerWidget):
        menu_showHide = QMenu('Show/Hide shot views', menu)
        menu_showHide.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'showHide'))
        menu_showHide.setDisabled(True)
        # Create and add empty menu to handle deletion of plot views and
        # figures
        menu_delete = QMenu('Delete', menu)
        menu_delete.setIcon(GlobalIcons.getStandardQIcon(QApplication, QStyle.SP_DialogDiscardButton))
        menu_delete.setDisabled(True)

        if numWindows > 0:
            menu_showHide.setDisabled(False)
            menu_delete.setDisabled(False)

            # Create and add empty submenu to handle windows show/hide
            submenu_showHideView = menu_showHide.addMenu('Views')
            submenu_showHideView.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Figure'))
            # Create and add empty submenu to handle windows deletion
            subMenu_deleteView = menu_delete.addMenu('Views')
            subMenu_deleteView.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'Figure'))

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
            action_deleteAll_views.triggered.connect(partial(
                self.deleteAllViews))
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

        # Check if DTV is shown in MDI (DTV is then embedded to subwindow and
        # subwindow to MDI window) and show/hide accordingly
        print(dtv)
        if dtv.getMDI() != None:
            if dtv.isVisible():
                dtv.parent().hide()
            else:
                dtv.parent().show()
        else:
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
        if dtv.isVisible():
            dtv.hide()
        self.openShotView.api.removeDTVFrame(dtv)

    def deleteAllViews(self, index):
        """Remove a DTV.
        Argument:
            index : DTV index in the openedDTVs list
        """
        for i in range(0, len(self.openShotView.api.GetDTVFrames())):
            dtv = self.openShotView.api.GetDTVFrames()[index]
            if dtv.isVisible():
                dtv.hide()
            self.openShotView.api.removeDTVFrame(dtv)

    def getMDI(self):
        if self.parent.getMDI() != None:
            return self.parent.getMDI()
        return None
