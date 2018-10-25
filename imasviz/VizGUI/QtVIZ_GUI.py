import os
import sys

from PyQt5.QtWidgets import QTabWidget, QWidget, QFormLayout, QApplication, QLineEdit, \
    QPushButton, QVBoxLayout, QComboBox
from imasviz.VizUtils.GlobalOperations import GlobalOperations

from imasviz.VizGUI.VizGuiCustomization.QtDefault import QtDefault
from imasviz.VizGUI.VizGUICommands.VizOpenViews.QtOpenShotView import QtOpenShotView
from imasviz.VizUtils.GlobalValues import GlobalValues


class GUIFrame(QTabWidget):
    def __init__(self, parent):
        super(GUIFrame, self).__init__(parent)

        self.openShotView = QtOpenShotView()

        self.setGeometry(300,300,600,200)
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.addTab(self.tab1, "Local data source")
        self.addTab(self.tab2, "Experiment data source")

        self.tabOne()
        self.tabTwo()

        title = "IMAS_VIZ (version " + str(GlobalValues.IMAS_VIZ_VERSION) + ")"
        self.setWindowTitle(title)

        self.handlerValue = 0
        self.shell = None

    def closeEvent(self, event):
         if GlobalOperations.YesNo(self, "Exit IMAS_VIZ ?", "Please confirm"):
             sys.exit(0)

    def tabOne(self):
        layout = QVBoxLayout()
        default_user_name, default_machine, default_run = QtDefault().getGUIEntries()
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
            # openShotView = QtOpenShotView()
            self.openShotView.Open(evt, dataSourceName=GlobalValues.IMAS_NATIVE,
                                        imasDbName=self.imasDbName.text(),
                                        userName=self.userName.text(),
                                        runNumber=self.runNumber.text(),
                                        shotNumber=self.shotNumber.text())
        except ValueError as e:
            self.logFromTab1.error(str(e))

    def CheckInputsFromTab1(self):
        """Display warning message if the required parameter was not specified"""
        if self.userName.text() == '':
            raise ValueError("'User name' field is empty.")

        if self.imasDbName.text() == '':
            raise ValueError("'IMAS database name' field is empty.")

        if self.shotNumber.text() == '' or self.runNumber.text() == '':
            raise ValueError("'Shot number' or 'run number' field is empty.")

        """Check if data source is available"""
        GlobalOperations.check(GlobalValues.IMAS_NATIVE, int(self.shotNumber.text()))

    def tabTwo(self):

        layout = QVBoxLayout()

        vboxlayout = QFormLayout()
        """Set static text for each GUI box (left from the box itself) """
        self.shotNumber2 = QLineEdit()
        vboxlayout.addRow('Shot number', self.shotNumber2)
        self.runNumber2 = QLineEdit()
        vboxlayout.addRow('Run number', self.runNumber2)

        if 'UDA_LOG' in os.environ:
            publicDatabases = ['WEST', 'TCV', 'JET', 'AUG']
        else:
            publicDatabases = ['WEST']

        self.cb = QComboBox()
        self.cb.addItems(publicDatabases)
        vboxlayout.addRow('Unified Data Access', self.cb)
        #self.cb.currentIndexChanged.connect(self.cbSelectionchange)

        button_open2 = QPushButton('Open', self)
        button_open2.clicked.connect(self.OpenDataSourceFromTab2)
        layout.addLayout(vboxlayout)

        vboxLayout2 = QVBoxLayout()
        vboxLayout2.addWidget(button_open2)
        layout.addLayout(vboxLayout2)

        # vboxLayout3 = QVBoxLayout()
        # qlabel = QLabel('Log window')
        # vboxLayout3.addWidget(qlabel)
        # self.logWindow2 = QTextEdit("Welcome to IMAS_VIZ!")
        # self.logFromTab2 = TextCtrlLogger(self.logWindow2)
        # vboxLayout3.addWidget(self.logWindow2)
        # layout.addLayout(vboxLayout3)

        self.tab2.setLayout(layout)

    def OpenDataSourceFromTab2(self, evt):
        try:
            self.CheckInputsFromTab2()
            openShotView = QtOpenShotView(dataSourceName=GlobalValues.IMAS_UDA,
                                        imasDbName='',
                                        userName='',
                                        runNumber=self.runNumber2.text(),
                                        shotNumber=self.shotNumber2.text())
            openShotView.Open(evt)
        except ValueError as e:
            self.logFromTab2.error(str(e))

    def CheckInputsFromTab2(self):
        machineName = \
            self.cb.currentText()

        if machineName == '':
            raise ValueError("'UDA name' field is empty.")

        if self.shotNumber2.text() == '':
            raise ValueError("'Shot number' field is empty.")

        if self.runNumber2.text() == '':
            raise ValueError("'Run number' field is empty.")

        GlobalOperations.check(GlobalValues.IMAS_UDA, int(self.shotNumber2.text()))

def main():
    app = QApplication(sys.argv)
    GlobalOperations.checkEnvSettings()
    #label = "IMAS_VIZ (version " + str(GlobalValues.IMAS_VIZ_VERSION) + ")"
    ex = GUIFrame(None)
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
