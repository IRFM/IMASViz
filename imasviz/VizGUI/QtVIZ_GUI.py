#  Name   : QVizPlotWidget
#
#          Provides startup handling.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
#*******************************************************************************
#     Copyright(c) 2016- F.Ludovic, L.xinyi, D. Penko
#*******************************************************************************

import os
import sys
import logging
from functools import partial
from PyQt5.QtWidgets import QMenuBar, QAction, QMenu, QMainWindow, QStyle, QDockWidget

# Add imasviz source path
sys.path.append((os.environ['VIZ_HOME']))

from PyQt5.QtWidgets import QTabWidget, QWidget, QFormLayout, QApplication, QLineEdit, \
    QPushButton, QVBoxLayout, QComboBox, QPlainTextEdit, QGridLayout
from PyQt5.QtCore import QSize, pyqtSlot, Qt
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizGUI.VizGuiCustomization.QVizDefault import QVizDefault
from imasviz.VizGUI.VizGUICommands.VizOpenViews.QVizOpenShotView import QVizOpenShotView
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues, GlobalIcons


import matplotlib
matplotlib.use('Qt5Agg')

class GUIFrame(QTabWidget):
    def __init__(self, parent):
        super(GUIFrame, self).__init__(parent)

        self.openShotView = QVizOpenShotView()

        #self.setGeometry(300, 300, 300, 200)
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.addTab(self.tab1, "Local data source")
        self.addTab(self.tab2, "Experiment data source")

        self.tabOne()
        self.tabTwo()

        title = "IMAS_VIZ (version " + str(QVizGlobalValues.IMAS_VIZ_VERSION) + ")"
        self.setWindowTitle(title)

        self.contextMenu = None

    def logPanel(self):
        #LOG WIDGET
        self.logWidget = QPlainTextEdit(parent=self)
        #self.logWidget.resize(QSize(500, 300))
        self.logWidget.setReadOnly(True)
        logging.getLogger().setLevel(logging.INFO)
        handler = Logger(self)
        logging.getLogger().addHandler(handler)
        handler.new_record.connect(self.logWidget.appendHtml)
        layout = QVBoxLayout()
        layout.addWidget(self.logWidget)
        return layout

    def tabOne(self):
        layout = QVBoxLayout()
        default_user_name, default_machine, default_run = QVizDefault().getGUIEntries()
        vboxLayout = QFormLayout()
        """Set static text for each GUI box (left from the box itself) """
        self.userName = QLineEdit(default_user_name)
        vboxLayout.addRow('User name', self.userName)
        self.imasDbName = QLineEdit(default_machine)
        vboxLayout.addRow('Tokamak', self.imasDbName)
        self.shotNumber = QLineEdit()
        vboxLayout.addRow('Shot number', self.shotNumber)
        self.runNumber = QLineEdit(default_run)
        vboxLayout.addRow('Run number', self.runNumber)
        button_open1 = QPushButton('Open', self)

        button_open1.clicked.connect(self.OpenDataSourceFromTab1)

        layout.addLayout(vboxLayout)

        vboxLayout2 = QVBoxLayout()
        vboxLayout2.addWidget(button_open1)

        layout.addLayout(vboxLayout2)
        self.tab1.setLayout(layout)

    def OpenDataSourceFromTab1(self, evt):
        try:
            self.CheckInputsFromTab1()
            tokens = self.shotNumber.text().split()
            try:
                for shotNumber in tokens:
                    val = int(shotNumber)

                    """Check if data source is available"""
                    QVizGlobalOperations.check(QVizGlobalValues.IMAS_NATIVE, val)

                    self.openShotView.Open(evt, dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                   imasDbName=self.imasDbName.text(),
                                   userName=self.userName.text(),
                                   runNumber=self.runNumber.text(),
                                   shotNumber=str(val))


            except ValueError as e:
                raise ValueError(str(e))

        except ValueError as e:
            QVizGlobalOperations.message(self, str(e), 'Error')

    def CheckInputsFromTab1(self):
        """Display warning message if the required parameter was not specified"""
        if self.userName.text() == '':
            raise ValueError("'User name' field is empty.")

        if self.imasDbName.text() == '':
            raise ValueError("'Tokamak' field is empty.")

        if self.shotNumber.text() == '' or self.runNumber.text() == '':
            raise ValueError("'Shot number' or 'run number' field is empty.")

    def tabTwo(self):

        layout = QVBoxLayout()
        vboxlayout = QFormLayout()
        """Set static text for each GUI box (left from the box itself) """
        self.shotNumber2 = QLineEdit()
        vboxlayout.addRow('Shot number', self.shotNumber2)
        default_user_name, default_machine, default_run = QVizDefault().getGUIEntries()
        self.runNumber2 = QLineEdit(default_run)
        vboxlayout.addRow('Run number', self.runNumber2)

        publicDatabases = []

        file = open(os.environ['VIZ_HOME'] + '/config/UDA_machines')
        if file is not None:
            UDAmachines = file.readline()
            file.close()
            publicDatabases = UDAmachines.split()
        else:
            logging.warning("Missing UDA_machines file in /config directory. UDA will be disabled!")
            os.environ.get['UDA_DISABLED'] = 1

        if os.environ.get('UDA_DISABLED') == 1:
            print('UDA will be disabled')
            self.tab2.setDisabled(True)
        else:
            if 'UDA_HOST' in os.environ:
                self.tab2.setDisabled(False)
            else:
                print('UDA will be disabled (no UDA_HOST defined')
                self.tab2.setDisabled(True)

        self.cb = QComboBox()
        self.cb.addItems(publicDatabases)
        vboxlayout.addRow('Unified Data Access', self.cb)
        # self.cb.currentIndexChanged.connect(self.cbSelectionchange)

        button_open2 = QPushButton('Open', self)
        button_open2.clicked.connect(self.OpenDataSourceFromTab2)
        layout.addLayout(vboxlayout)

        vboxLayout2 = QVBoxLayout()
        vboxLayout2.addWidget(button_open2)
        layout.addLayout(vboxLayout2)
        self.tab2.setLayout(layout)
        # self.tab2.setDisabled(True)

    def OpenDataSourceFromTab2(self, evt):
        try:
            self.CheckInputsFromTab2()
            self.openShotView.Open(evt,
                                   dataSourceName=QVizGlobalValues.IMAS_UDA,
                                            imasDbName='',
                                            userName='',
                                            runNumber=self.runNumber2.text(),
                                            shotNumber=self.shotNumber2.text(),
                                            UDAMachineName=self.cb.currentText())
        except ValueError as e:
            QVizGlobalOperations.message(self, str(e), 'Error')

    def CheckInputsFromTab2(self):
        machineName = \
            self.cb.currentText()

        if machineName == '':
            raise ValueError("'UDA name' field is empty.")

        if self.shotNumber2.text() == '':
            raise ValueError("'Shot number' field is empty.")

        if self.runNumber2.text() == '':
            raise ValueError("'Run number' field is empty.")

        QVizGlobalOperations.check(QVizGlobalValues.IMAS_UDA, int(self.shotNumber2.text()))

    def contextMenuEvent(self, event):

        # Get position
        self.pos = event.pos()
        self.showPopUpMenu()

    def showPopUpMenu(self):
        """Display the popup menu .
        """
        self.contextMenu = QMenu()
        # Set new popup menu
        self.popupmenu = self.buildContextMenu()

        # Map the menu (in order to show it)
        self.popupmenu.exec_(self.mapToGlobal(self.pos))
        return 1

    def buildContextMenu(self):
        numWindows = len(self.openShotView.api.GetDTVFrames())
        menu_showHide, menu_delete = self.menusShowHideAndDelete(numWindows)
        self.contextMenu.addMenu(menu_showHide)
        self.contextMenu.addMenu(menu_delete)
        return self.contextMenu

    def menusShowHideAndDelete(self, numWindows):

        menu_showHide = QMenu('Show/Hide', self.contextMenu)
        menu_showHide.setIcon(GlobalIcons.getCustomQIcon(QApplication, 'showHide'))
        menu_showHide.setDisabled(True)
        # Create and add empty menu to handle deletion of plot views and
        # figures
        menu_delete = QMenu('Delete', self.contextMenu)
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
                shotNumber = dataSource.shotNumber
                runNumber = dataSource.runNumber
                actionLabel = dataSource.getLongLabel()
                action_showHide_view = QAction(actionLabel, self)
                action_showHide_view.triggered.connect(
                    partial(self.showHideView, i))
                # Add to submenu
                submenu_showHideView.addAction(action_showHide_view)

                # --------------------------------------------------------------
                # Add menu item to delete existing window
                # Set action
                action_delete_view = QAction(actionLabel, self)
                action_delete_view.triggered.connect(
                    partial(self.deleteView, i))
                # Add to submenu
                subMenu_deleteView.addAction(action_delete_view)

            # ------------------------------------------------------------------
            # Add menu item to delete all existing figures
            # Set action
            action_deleteAll_views = QAction('All', self)
            action_deleteAll_views.triggered.connect(partial(
                self.deleteAllViews))
            # Add to submenu
            subMenu_deleteView.addAction(action_deleteAll_views)
            # Bitmap icon
            # TODO
        return menu_showHide, menu_delete

    def showHideView(self, index):
        """Hide/show a DTV.
        Argument:
            index : DTV index in the openedDTVs list
        """
        #dtv = self.openedDTVs[index]
        dtv = self.openShotView.api.GetDTVFrames()[index]
        if dtv.isVisible():
            dtv.hide()
        else:
            dtv.show()

    def deleteView(self, index):
        """Remove a DTV.
        Argument:
            index : DTV index in the openedDTVs list
        """
        #dtv = self.openedDTVs[index]
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

class VizMainWindow(QMainWindow):
    def __init__(self, parent):
        super(VizMainWindow, self).__init__(parent)
        ex = GUIFrame(None)
        title = "IMAS_VIZ (version " + str(QVizGlobalValues.IMAS_VIZ_VERSION) + ")"
        self.setWindowTitle(title)
        self.setCentralWidget(ex)
        self.logPanel()
        #self.

    def logPanel(self):
        # #LOG WIDGET
        # self.logWidget = QPlainTextEdit(parent=self)
        # self.logWidget.resize(QSize(500, 200))
        # self.logWidget.setReadOnly(True)
        # logging.getLogger().setLevel(logging.INFO)
        # handler = Logger(self)
        # logging.getLogger().addHandler(handler)
        # handler.new_record.connect(self.logWidget.appendHtml)
        # layout = QVBoxLayout()
        # layout.addWidget(self.logWidget)
        # return layout
        self.logWidget = QPlainTextEdit(parent=self)
        self.logWidget.setReadOnly(True)
        self.dockWidget_log = QDockWidget("Log", self)
        self.dockWidget_log.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_log.setObjectName("DockWidget_LOG")
        self.dockWidgetContents_log = QWidget()
        self.dockWidgetContents_log.setObjectName("DockWidgetContents_LOG")
        self.gridLayout_log = QGridLayout(self.dockWidgetContents_log)
        #- Set dockwidget size
        #self.dockWidget_log.resize(QSize(, ref_height / 4))
        self.gridLayout_log.setObjectName("GridLayout_LOG")
        self.gridLayout_log.addWidget(self.logWidget, 0, 0, 1, 1)
        self.dockWidget_log.setWidget(self.dockWidgetContents_log)

        self.addDockWidget(Qt.DockWidgetArea(8), self.dockWidget_log)
        logging.getLogger().setLevel(logging.INFO)
        handler = Logger(self)
        logging.getLogger().addHandler(handler)
        handler.new_record.connect(self.logWidget.appendHtml)

    def closeEvent(self, event):
        """Modify close event to request confirmation trough dialog. If
        confirmed, close the application.
        """
        # Get Yes/No answer (returns True/False)
        answer = \
            QVizGlobalOperations.YesNo(question='Exit IMAS_VIZ?',
                                       caption='Please confirm')
        if answer==True:
            event.accept()
        else:
            event.ignore()

from PyQt5.QtCore import pyqtSignal, QObject
import logging

class Logger(QObject, logging.Handler):
    """ Logger for handling passing the information and error messages to logWidget.
    """
    new_record = pyqtSignal(object)

    def __init__(self, parent):
        super().__init__(parent)
        super(logging.Handler).__init__()
        formatter = Formatter('%(asctime)s|%(levelname)s|%(message)s|', '%d/%m/%Y %H:%M:%S')
        self.setFormatter(formatter)

    def emit(self, record):
        msg = self.format(record)

        if 'ERROR' in msg:
            msg = "<font color='red'>" + msg + "</font>"
        elif 'INFO' in msg:
            msg = "<font color='black'>" + msg + "</font>"

        self.new_record.emit(msg)


class Formatter(logging.Formatter):
    def formatException(self, ei):
        result = super(Formatter, self).formatException(ei)
        return result

    def format(self, record):
        s = super(Formatter, self).format(record)
        if record.exc_text:
            s = s.replace('\n', '')
        return s

def main():
    app = QApplication(sys.argv)
    QVizGlobalOperations.checkEnvSettings()
    window = VizMainWindow(None);
    window.setGeometry(400, 400, 600, 500)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
