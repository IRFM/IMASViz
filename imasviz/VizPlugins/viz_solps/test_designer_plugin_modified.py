# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'designer_plugin_1.ui'
#
# Created by: PyQt5 UI code generator 5.9.1
#
# WARNING! All changes made in this file will be lost!

# This is first example of the plugin that was produced using Qt Designer + '.ui
# to .py' converter. It had to be further modified in order for it to be
# usable in IMASViz too
# TODO: set source plugin files in a way that no Qt designer created plugin must
# be additionally modified in order for it to be compatible with IMASViz

import sys
import os
# Add imasviz source path
sys.path.append(os.environ['VIZ_HOME'])
sys.path.append((os.environ['VIZ_HOME'] + '/imasviz/VizPlugins/viz_solps'))
from imasviz.VizPlugins.VizPlugins import VizPlugins

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(VizPlugins):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(537, 560)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.parent = MainWindow
        self.plotEPGGD = plotEPGGD(parent=self.centralwidget)
        self.plotEPGGD.setGeometry(QtCore.QRect(10, 10, 518, 472))
        self.plotEPGGD.setObjectName("plotEPGGD")
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(30, 480, 83, 25))
        self.pushButton.setObjectName("pushButton")
        self.pushButton_2 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_2.setGeometry(QtCore.QRect(120, 480, 83, 25))
        self.pushButton_2.setObjectName("pushButton_2")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 537, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.pushButton.clicked.connect(self.plotEPGGD.checkIDS)
        self.pushButton_2.clicked.connect(self.plotEPGGD.plotData)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.pushButton.setText(_translate("MainWindow", "GetIDS"))
        self.pushButton_2.setText(_translate("MainWindow", "Run plot"))

from plotEPGGD import plotEPGGD

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

