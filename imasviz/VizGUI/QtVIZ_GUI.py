#  Name   : QVizPlotWidget
#
#          Provides startup handling.
#
#  Author :
#         Ludovic Fleury, Xinyi Li, Dejan Penko
#  E-mail :
#         ludovic.fleury@cea.fr, xinyi.li@cea.fr, dejan.penko@lecad.fs.uni-lj.si
#
# *****************************************************************************
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
# *****************************************************************************

import os
import sys, getopt
import logging
from functools import partial
from PySide6.QtWidgets import (QTabWidget, QWidget, QFormLayout, QApplication,
                             QMenu, QMainWindow, QDockWidget,
                             QLineEdit, QPushButton, QVBoxLayout, QComboBox,
                             QPlainTextEdit, QGridLayout, QMdiArea, QTableView)
from PySide6.QtCore import Qt
from pathlib import Path


# Append imasviz source path
sys.path.append((os.environ['VIZ_HOME']))

from imasviz.VizGUI.VizGuiCustomization import QVizDefault
from imasviz.VizGUI.VizGUICommands import QVizMainMenuController
from imasviz.VizUtils import QVizGlobalValues, QVizPreferences,QVizGlobalOperations, QVizLogger, UserInputs
from imasviz.VizGUI.VizWidgets.QVizIMASdbBrowserWidget import QVizIMASdbBrowserWidget
from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource


class GUIFrame(QTabWidget):
    def __init__(self, parent):
        super(GUIFrame, self).__init__(parent)

        #self.setGeometry(300, 300, 300, 200)
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.addTab(self.tab1, "Legacy parameters")
        self.addTab(self.tab2, "URI")

        self.tabOne()
        self.tabTwo()

        title = "IMAS_VIZ (version " + str(QVizGlobalValues.IMAS_VIZ_VERSION) + ")"
        self.setWindowTitle(title)

        self.mainMenuController = QVizMainMenuController(self)

        if UserInputs.inputs is not None and len(UserInputs.inputs) == 9:
            UserInputs.enable = True
            self.OpenDataSourceFromTab1(None)

        self.contextMenu = None

    # def logPanel(self):
    #     #LOG WIDGET
    #     self.logWidget = QPlainTextEdit(parent=self)
    #     #self.logWidget.resize(QSize(500, 300))
    #     self.logWidget.setReadOnly(True)
    #     logging.getLogger('logPanel').setLevel(logging.INFO)
    #     handler = QVizLogger()
    #     logging.getLogger('logPanel').addHandler(handler)
    #     handler.new_signal_emiter.new_signal.connect(self.logWidget.appendHtml)
    #     layout = QVBoxLayout()
    #     layout.addWidget(self.logWidget)
    #     return layout

    def tabOne(self):
        layout = QVBoxLayout()
        default_user_name, default_machine, default_run = \
            QVizDefault().getGUIEntries()
        vboxLayout = QFormLayout()
        """Set static text for each GUI box (left from the box itself) """
        self.userName = QLineEdit(default_user_name)
        self.userName.setStatusTip("Name of the user under which the case is "
                                   "being stored.")
        self.userName.setToolTip("Name of the user under which the case is "
                                 "being stored.")
        vboxLayout.addRow('User name', self.userName)
        self.imasDbName = QLineEdit(default_machine)
        self.imasDbName.setStatusTip("Database label under which the case is "
                                     "being stored.")
        self.imasDbName.setToolTip("Database label under which the case is "
                                   "being stored.")
        vboxLayout.addRow('Database', self.imasDbName)
        self.shotNumber = QLineEdit()
        self.shotNumber.setStatusTip("Shot case identifier.")
        self.shotNumber.setToolTip("Shot case identifier.")
        vboxLayout.addRow('Shot number', self.shotNumber)
        self.runNumber = QLineEdit(default_run)
        self.runNumber.setStatusTip("Run case identifier.")
        self.runNumber.setToolTip("Run case identifier.")
        vboxLayout.addRow('Run number', self.runNumber)

        self.IMASdbBrowserWidget = QVizIMASdbBrowserWidget(parent=self)
        self.IMASdbBrowserWidget.onItemDoubleClick.connect(self.updateIDSparam)
        self.userName.editingFinished.connect(self.onUserNameEditFinished)

        self.backend = 13 #first item
        self.backendCombo = QComboBox()
        vboxLayout.addRow('Backend', self.backendCombo)
        self.backendCombo.addItems(['HDF5', 'MDS+'])
        self.backendCombo.activated.connect(self.onActivated)

        button_open1 = QPushButton('Open', self)
        button_open1.setStatusTip("Open the case for the given parameters.")
        button_open1.setToolTip("Open the case for the given parameters.")
        button_open1.clicked.connect(self.OpenDataSourceFromTab1)

        layout.addLayout(vboxLayout)
        layout.addWidget(self.IMASdbBrowserWidget)

        vboxLayout2 = QVBoxLayout()
        vboxLayout2.addWidget(button_open1)

        layout.addLayout(vboxLayout2)
        self.tab1.setLayout(layout)

    def onActivated(self, index):
        if index == 0:
            self.backend = 13
        elif index == 1:
            self.backend = 12

    def OpenDataSourceFromTab1(self, evt):
        try:
            if UserInputs.enable:
                try:
                    opts, args = getopt.getopt(UserInputs.inputs[1:], 'u:d:s:r:b:')
                    for opt, arg in opts:
                        if opt == '-u':
                            self.userName.setText(arg)
                        elif opt in ("-d"):
                            self.imasDbName.setText(arg)
                        elif opt in ("-s"):
                            self.shotNumber.setText(arg)
                        elif opt in ("-r"):
                            self.runNumber.setText(arg)
                        elif opt in ("-b"):
                            self.backend = int(arg)
                            if self.backend == 13:
                                self.backendCombo.setCurrentIndex(0)
                            elif self.backend == 12:
                                self.backendCombo.setCurrentIndex(1)
                            else:
                                raise ValueError("Backend id should be 12 or 13")
                except getopt.GetoptError:
                    logging.getLogger('logPanel').error('Bad user input.')
                    sys.exit(-1)
                    pass

                UserInputs.enable = False

            self.CheckInputsFromTab1()
            tokens = self.shotNumber.text().split()
            try:
                for shotNumber in tokens:

                    """Check if data source is available"""
                    QVizGlobalOperations.check(QVizGlobalValues.IMAS_NATIVE)

                    uri, legacy_attributes = QVizIMASDataSource.build_uri(
                        backend_id=self.backend, 
                        shot=int(shotNumber), 
                        run=int(self.runNumber.text()), 
                        user_name=self.userName.text(), 
                        db_name=self.imasDbName.text(), 
                        data_version='3', 
                        options='')
                    print("QtVizGui::legacy_attributes=", legacy_attributes)
                    self.mainMenuController.openShotView.Open(evt, uri, legacy_attributes)

            except Exception as e:
                raise ValueError(str(e))

        except ValueError as e:
            logging.getLogger('logPanel').error(str(e))

    def CheckInputsFromTab1(self):
        """Display warning message if the required parameter was not specified"""
        if self.userName.text() == '':
            raise ValueError("'User name' field is empty.")

        if self.imasDbName.text() == '':
            raise ValueError("'Database' field is empty.")

        if self.shotNumber.text() == '' or self.runNumber.text() == '':
            raise ValueError("'Shot number' or 'run number' field is empty.")

    def updateIDSparam(self):
        """Update IDS parameters widgets.
        """
        self.userName.setText(self.IMASdbBrowserWidget.getActiveUsername())
        self.imasDbName.setText(self.IMASdbBrowserWidget.getActiveDatabase())
        self.shotNumber.setText(self.IMASdbBrowserWidget.getActiveShot())
        self.runNumber.setText(self.IMASdbBrowserWidget.getActiveRun())
        self.backend = self.IMASdbBrowserWidget.getActiveBackend()
        if self.backend == 13:
            self.backendCombo.setCurrentIndex(0)
        elif self.backend == 12:
            self.backendCombo.setCurrentIndex(1)
        else:
            raise ValueError("Unexpected backend id provided by the database browser.")

    def onUserNameEditFinished(self):
        self.IMASdbBrowserWidget.setActiveUsername(self.userName.text())

    def tabTwo(self):

        layout = QVBoxLayout()
        vboxlayout = QFormLayout()
        """Set static text for each GUI box (left from the box itself) """
        self.URI = QLineEdit()
        vboxlayout.addRow('URI', self.URI)

        button_open2 = QPushButton('Open', self)
        button_open2.clicked.connect(self.OpenDataSourceFromTab2)
        layout.addLayout(vboxlayout)

        if QVizIMASDataSource.getVersion() == 4:
            self.URI.setEnabled(False)
            button_open2.setEnabled(False)

        vboxLayout2 = QVBoxLayout()
        vboxLayout2.addWidget(button_open2)
        layout.addLayout(vboxLayout2)
        self.tab2.setLayout(layout)

    def OpenDataSourceFromTab2(self, evt):
        import imas
        try:
            try:
                self.CheckInputsFromTab2()
                self.mainMenuController.openShotView.Open(evt, self.URI.text())

            except Exception as e:
                raise ValueError(str(e))

        except ValueError as e:
            logging.getLogger('logPanel').error('Unable to open URI ' + self.URI.text() + ': ' + str(e))

    def CheckInputsFromTab2(self):

        if self.URI.text() == '':
            raise ValueError("'URI' field is empty.")


    def contextMenuEvent(self, event):

        # Get position
        self.pos = event.pos()
        self.showPopUpMenu()

    def showPopUpMenu(self):
        """Display the popup menu .
        """
        self.contextMenu = QMenu()
        # Set new popup menu
        self.mainMenuController.updateMenu(self.contextMenu, self)

        # Map the menu (in order to show it)
        self.contextMenu.exec(self.mapToGlobal(self.pos))
        return 1

    def getMDI(self):
        """ Get MDI area through the root IMASViz main window.
        """
        if self.window().objectName() == "IMASViz root window":
            return self.window().getMDI()
        return None

    # def keyPressEvent(self, event):
    #     # Note Qt.Key_Enter is Enter key on numpad
    #     if event.key() == Qt.Key_Return:
    #         self.OpenDataSourceFromTab1(event)
    #     event.accept()


class QVizStartWindow(QMainWindow):
    def __init__(self, parent):
        super(QVizStartWindow, self).__init__(parent)
        ex = GUIFrame(parent)
        self.setCentralWidget(ex)
        # self.setWidget(ex)
        self.logPanel()

    def logPanel(self):
        # #LOG WIDGET
        self.logWidget = QPlainTextEdit(parent=self)
        self.logWidget.setStatusTip("Log panel.")
        self.logWidget.setReadOnly(True)
        self.dockWidget_log = QDockWidget("Log", self)
        self.dockWidget_log.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_log.setObjectName("DockWidget_LOG")
        self.dockWidgetContents_log = QWidget()
        self.dockWidgetContents_log.setObjectName("DockWidgetContents_LOG")
        self.gridLayout_log = QGridLayout(self.dockWidgetContents_log)
        # Set dockwidget size
        self.gridLayout_log.setObjectName("GridLayout_LOG")
        self.gridLayout_log.addWidget(self.logWidget, 0, 0, 1, 1)
        self.dockWidget_log.setWidget(self.dockWidgetContents_log)

        self.addDockWidget(Qt.DockWidgetArea(8), self.dockWidget_log)
        logging.getLogger('logPanel').setLevel(logging.INFO)
        handler = QVizLogger()
        logging.getLogger('logPanel').addHandler(handler)
        handler.new_signal_emiter.new_signal.connect(self.logWidget.appendHtml)
        

    def closeEvent(self, event):
        """Modify close event to request confirmation trough dialog. If
        confirmed, close the application.
        """
        # Get Yes/No answer (returns True/False)
        answer = \
            QVizGlobalOperations.YesNo(question='Exit IMAS_VIZ?',
                                       caption='Please confirm')
        if answer == True:
            event.accept()
        else:
            event.ignore()

    def getMDI(self):
        """ Get MDI area through the root IMASViz main window.
        """
        if self.window().objectName() == "IMASViz root window":
            return self.window().getMDI()
        return None


class QVizMDI(QMdiArea):
    """Class for Multiple Document Interface (MDI) area.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("MDI")
        self.setObjectName("MDI")


class QVizMainWindow(QMainWindow):
    """ Class for IMASViz main window, which contains MDI and all
    sub-main windows, widgets etc.
    """
    def __init__(self):
        super(QVizMainWindow, self).__init__()

        # Set title
        title = "IMASVIZ (version " + str(QVizGlobalValues.IMAS_VIZ_VERSION) + ")"
        self.setWindowTitle(title)
        # Set name of this main window as the root
        self.setObjectName("IMASViz root window")
        # set status bar
        self.setStatusBar()

        # Set MDI (Multiple Document Interface)
        self.MDI = QVizMDI(self)
        # Set central widget
        centralWidget = QWidget(self)
        # Set start window
        self.startWindow = QVizStartWindow(self)

        # Set layout and add start window and MDI to it
        layout = QGridLayout(centralWidget)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 7)

        layout.addWidget(self.startWindow, 0, 0, 1, 1)
        layout.addWidget(self.MDI, 0, 1, 1, 1)
        # Set central widget of the main window
        self.setCentralWidget(centralWidget)
        # Resize to full screen
        self.showMaximized()

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

    def getMDI(self):
        if self.MDI != None:
            return self.MDI
        return None

    def getStartWindow(self):
        return self.startWindow

    def setStatusBar(self):
        self.statusBar().show()

def help():
    try:
        if len(sys.argv[1:]) != 1:
            return
        opts, args = getopt.getopt(sys.argv[1:], 'h', ['help'])
        for opt, arg in opts:
            if opt in ('-h', '--help'):
                print("-------------------------------------------------------------------------------")
                print("")
                print("Help:")
                print("")
                print("1. Options for specifying user, database, shot, run numbers and backend at startup time:")
                print("viz -u <user> -d <database> -s <shot> -r <run> -b <backend>")
                print("")
                print("2. User guide for IMASViz:")
                print ("viz_doc")
                print("-------------------------------------------------------------------------------")
                print("")
                sys.exit(0)
    except getopt.GetoptError:
        print("usage: viz -u <user> -d <database> -s <shot> -r <run> -b <backend>")
        print ("or: viz --help")
        sys.exit(-1)

def main():
    help()
    UserInputs().setUserInputs(sys.argv)
    app = QApplication(sys.argv)
    QVizGlobalOperations.checkEnvSettings()
    QVizPreferences().build()
    window = QVizMainWindow()
    logging.getLogger('logPanel').info("Welcome to Viz!")
    logging.getLogger('logPanel').info("Please report any issue to ITER JIRA: https://jira.iter.org/")

    if QVizIMASDataSource.getVersion() == 4:
        logging.getLogger("logPanel").warning("You are using IMAS AL4. URI input are not available:")
        logging.getLogger("logPanel").warning("--> URI input are not available for this version of the AL")
        logging.getLogger("logPanel").warning("--> UDA is not available for this version of the AL")

    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
