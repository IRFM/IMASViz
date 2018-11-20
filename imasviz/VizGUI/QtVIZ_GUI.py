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

# Add imasviz source path
# sys.path.append((os.environ['VIZ_HOME']))

import os
import sys

from PyQt5.QtWidgets import QTabWidget, QWidget, QFormLayout, QApplication, QLineEdit, \
    QPushButton, QVBoxLayout, QComboBox
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizGUI.VizGuiCustomization.QVizDefault import QVizDefault
from imasviz.VizGUI.VizGUICommands.VizOpenViews.QVizOpenShotView import QVizOpenShotView
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues


class GUIFrame(QTabWidget):
    def __init__(self, parent):
        super(GUIFrame, self).__init__(parent)

        self.openShotView = QVizOpenShotView()

        self.setGeometry(300, 300, 600, 200)
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.addTab(self.tab1, "Local data source")
        self.addTab(self.tab2, "Experiment data source")

        self.tabOne()
        self.tabTwo()

        title = "IMAS_VIZ (version " + str(QVizGlobalValues.IMAS_VIZ_VERSION) + ")"
        self.setWindowTitle(title)

        self.handlerValue = 0
        self.shell = None

    def closeEvent(self, event):
        if QVizGlobalOperations.YesNo(self, "Exit IMAS_VIZ ?", "Please confirm"):
            sys.exit(0)

    def tabOne(self):
        layout = QVBoxLayout()
        default_user_name, default_machine, default_run = QVizDefault().getGUIEntries()
        vboxLayout = QFormLayout()
        """Set static text for each GUI box (left from the box itself) """
        self.userName = QLineEdit(default_user_name)
        vboxLayout.addRow('User name', self.userName)
        self.imasDbName = QLineEdit(default_machine)
        vboxLayout.addRow('IMAS database name', self.imasDbName)
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
            self.openShotView.Open(evt, dataSourceName=QVizGlobalValues.IMAS_NATIVE,
                                   imasDbName=self.imasDbName.text(),
                                   userName=self.userName.text(),
                                   runNumber=self.runNumber.text(),
                                   shotNumber=self.shotNumber.text())
        except ValueError as e:
            QVizGlobalOperations.message(self, str(e), 'Error opening file')

    def CheckInputsFromTab1(self):
        """Display warning message if the required parameter was not specified"""
        if self.userName.text() == '':
            raise ValueError("'User name' field is empty.")

        if self.imasDbName.text() == '':
            raise ValueError("'IMAS database name' field is empty.")

        if self.shotNumber.text() == '' or self.runNumber.text() == '':
            raise ValueError("'Shot number' or 'run number' field is empty.")

        """Check if data source is available"""
        QVizGlobalOperations.check(QVizGlobalValues.IMAS_NATIVE, int(self.shotNumber.text()))

    def tabTwo(self):

        layout = QVBoxLayout()
        vboxlayout = QFormLayout()
        """Set static text for each GUI box (left from the box itself) """
        self.shotNumber2 = QLineEdit()
        vboxlayout.addRow('Shot number', self.shotNumber2)
        default_user_name, default_machine, default_run = QVizDefault().getGUIEntries()
        self.runNumber2 = QLineEdit(default_run)
        vboxlayout.addRow('Run number', self.runNumber2)

        if 'UDA_LOG' in os.environ:
            publicDatabases = ['WEST', 'TCV', 'JET', 'AUG']
        else:
            publicDatabases = ['WEST']

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

    def OpenDataSourceFromTab2(self, evt):
        try:
            self.CheckInputsFromTab2()
            openShotView = QVizOpenShotView()
            openShotView.Open(evt, dataSourceName=QVizGlobalValues.IMAS_UDA,
                                            imasDbName='',
                                            userName='',
                                            runNumber=self.runNumber2.text(),
                                            shotNumber=self.shotNumber2.text(),
                                            UDAMachineName=self.cb.currentText())
        except ValueError as e:
            QVizGlobalOperations.message(self, str(e), 'Error opening file')

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


def main():
    app = QApplication(sys.argv)
    QVizGlobalOperations.checkEnvSettings()
    #label = "IMAS_VIZ (version " + str(QVizGlobalValues.IMAS_VIZ_VERSION) + ")"
    ex = GUIFrame(None)
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
