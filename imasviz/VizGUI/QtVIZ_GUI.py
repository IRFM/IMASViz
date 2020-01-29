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
#     Copyright(c) 2016- L. Fleury, X. Li, D. Penko
#*******************************************************************************

import os
import sys
import logging
from functools import partial
from PyQt5.QtWidgets import QMenuBar, QAction, QMenu, QMainWindow, QStyle, QDockWidget
from PyQt5.QtWidgets import QMdiArea, QMdiSubWindow

# Add imasviz source path
sys.path.append((os.environ['VIZ_HOME']))

from pathlib import Path
from imasviz.VizUtils.QVizLogger import QVizLogger
from PyQt5.QtWidgets import QTabWidget, QWidget, QFormLayout, QApplication, QLineEdit, \
    QPushButton, QVBoxLayout, QComboBox, QPlainTextEdit, QGridLayout
from PyQt5.QtCore import QSize, pyqtSlot, Qt
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizGUI.VizGuiCustomization.QVizDefault import QVizDefault
# from imasviz.VizGUI.VizGUICommands.VizOpenViews.QVizOpenShotView import QVizOpenShotView
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues, GlobalIcons, QVizPreferences
from imasviz.VizGUI.VizGUICommands.VizMenusManagement.QVizMainMenuController import QVizMainMenuController


import matplotlib
matplotlib.use('Qt5Agg')

class GUIFrame(QTabWidget):
    def __init__(self, parent):
        super(GUIFrame, self).__init__(parent)

        #self.setGeometry(300, 300, 300, 200)
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.addTab(self.tab1, "Local data source")
        self.addTab(self.tab2, "Experiment data source")

        self.tabOne()
        self.tabTwo()

        title = "IMAS_VIZ (version " + str(QVizGlobalValues.IMAS_VIZ_VERSION) + ")"
        self.setWindowTitle(title)

        self.mainMenuController = QVizMainMenuController(parent)
        self.contextMenu = None

    def logPanel(self):
        #LOG WIDGET
        self.logWidget = QPlainTextEdit(parent=self)
        #self.logWidget.resize(QSize(500, 300))
        self.logWidget.setReadOnly(True)
        logging.getLogger().setLevel(logging.INFO)
        handler = QVizLogger.getHandler()
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

                    self.mainMenuController.openShotView.Open(evt, dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                                              imasDbName=self.imasDbName.text(),
                                                              userName=self.userName.text(),
                                                              runNumber=self.runNumber.text(),
                                                              shotNumber=str(val))


            except Exception as e:
                raise ValueError(str(e))

        except ValueError as e:
            logging.error(str(e))

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


        if os.environ.get('UDA_DISABLED') != 1:
            udaConfigFilePath = Path(os.environ['VIZ_HOME'] + '/config/UDA_machines')
            if udaConfigFilePath.is_file():
                udaConfigFile = open(udaConfigFilePath)
                UDAmachines = udaConfigFile.readline()
                udaConfigFile.close()
                publicDatabases = UDAmachines.split()
            else:
                logging.warning("Missing UDA_machines file in /config directory. UDA will be disabled!")
                os.environ.get['UDA_DISABLED'] = 1
                self.tab2.setDisabled(True)
        else:
            print('UDA will be disabled (UDA_DISABLED=1)')
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
            try:
                self.CheckInputsFromTab2()
                self.mainMenuController.openShotView.Open(evt,
                                                          dataSourceName=QVizGlobalValues.IMAS_UDA,
                                                          imasDbName='',
                                                          userName='',
                                                          runNumber=self.runNumber2.text(),
                                                          shotNumber=self.shotNumber2.text(),
                                                          UDAMachineName=self.cb.currentText())
            except Exception as e:
                raise ValueError(str(e))

        except ValueError as e:
            logging.error('Unable to open UDA data source, the reason is: ' + str(e))

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
        self.mainMenuController.updateMenu(self.contextMenu, self)

        # Map the menu (in order to show it)
        self.contextMenu.exec_(self.mapToGlobal(self.pos))
        return 1

    def getMDI(self):
        """ Get MDI area through the root IMASViz main window.
        """
        if self.window().objectName() == "IMASViz root window":
            return self.window().getMDI()
        return None


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
        self.logWidget.setReadOnly(True)
        self.dockWidget_log = QDockWidget("Log", self)
        self.dockWidget_log.setFeatures(QDockWidget.DockWidgetFloatable)
        self.dockWidget_log.setObjectName("DockWidget_LOG")
        self.dockWidgetContents_log = QWidget()
        self.dockWidgetContents_log.setObjectName("DockWidgetContents_LOG")
        self.gridLayout_log = QGridLayout(self.dockWidgetContents_log)
        #- Set dockwidget size
        self.gridLayout_log.setObjectName("GridLayout_LOG")
        self.gridLayout_log.addWidget(self.logWidget, 0, 0, 1, 1)
        self.dockWidget_log.setWidget(self.dockWidgetContents_log)

        self.addDockWidget(Qt.DockWidgetArea(8), self.dockWidget_log)
        logging.getLogger().setLevel(logging.INFO)
        QVizLogger.getHandler().new_record.connect(self.logWidget.appendHtml)

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
        """ Get MDI area through the root IMASViz main window.
        """
        if self.window().objectName() == "IMASViz root window":
            return self.window().getMDI()
        return None

class QVizMDI(QMdiArea):
    """Class for MDI area.
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

        # Set MDI (Multiple Document Interface)
        self.MDI = QVizMDI(self)
        # Set central widget
        centralWidget = QWidget(self)
        # Set start window
        self.startWindow = QVizStartWindow(self)

        # Set layout and add start window and MDI to it
        layout = QGridLayout(centralWidget)
        layout.setColumnStretch(0,1)
        layout.setColumnStretch(1,7)

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

def main():
    app = QApplication(sys.argv)
    QVizGlobalOperations.checkEnvSettings()
    QVizPreferences().build()
    window = QVizMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
