#! /usr/bin/env python3

import sys
import os
import logging

from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, pyqtProperty
from PyQt5.QtWidgets import (QApplication, QDialog, QLineEdit, QPushButton,
                             QGridLayout, QDialogButtonBox, QWidget,
                             QFormLayout)
from PyQt5.QtGui import QIntValidator
import getopt

ENABLED = True

if 'IMAS_PREFIX' not in os.environ and 'IMAS_VERSION' not in os.environ:
    if __name__ == '__main__':
        print('IMAS module is not loaded.')
        sys.exit(2)
    else:
        ENABLED = False

else:

    try:
        import imas
    except ImportError:
        if __name__ == '__main__':
            print('There is no IMAS module... Exiting.')
            sys.exit(2)
        else:
            ENABLED = False
    except FileNotFoundError:
        print( __name__, 'Corrupted IMAS module!')
        if __name__ == '__main__':
            sys.exit(2)
        else:
            ENABLED = False

class GetVars:
    names = ['SHOT', 'RUN', 'USER', 'DEVICE', 'VERSION']
    numOfParams = len(names)
    shot, run, user, device, version = range(numOfParams)

    defaultValues = {}
    defaultValues[shot] = '122264'
    defaultValues[run] = '1'
    defaultValues[user] = os.getenv('USER')
    defaultValues[device] = 'iter'
    defaultValues[version] = '3'

class GetIDS(QWidget):
    """ Push button used for plugin."""
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super(GetIDS, self).__init__(parent)

        self.vars = {}
        for i in range(GetVars.numOfParams):
            # At the begining clear all parameters
            self.vars[i] = ''

        self.pushButton = QPushButton(self)
        self.pushButton.setText("Get IDS")
        self.pushButton.clicked.connect(self.getFromIDS)
        self.pushButton.setEnabled(ENABLED)

        layout = QGridLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pushButton)
        self.setLayout(layout)

    @pyqtSlot(str)
    def setUser(self, user):
        self.vars[GetVars.user] = user

    def getUser(self):
        return self.vars[GetVars.user]

    user = pyqtProperty(str, getUser, setUser)

    @pyqtSlot(str)
    def setDevice(self, device):
        self.vars[GetVars.device] = device

    def getDevice(self):
        return self.vars[GetVars.device]

    device = pyqtProperty(str, getDevice, setDevice)

    @pyqtSlot(str)
    def setVersion(self, version):
        self.vars[GetVars.device] = version

    def getVersion(self):
        return self.vars[GetVars.device]

    version = pyqtProperty(str, getVersion, setVersion)

    @pyqtSlot(str)
    def setRun(self, run):
        self.vars[GetVars.run] = run

    def getRun(self):
        return self.vars[GetVars.run]

    runNumber = pyqtProperty(str, getRun, setRun)

    @pyqtSlot(str)
    def setShot(self, shot):
        self.vars[GetVars.shot] = shot

    def getShot(self):
        return self.vars[GetVars.shot]

    shotNumber = pyqtProperty(str, getShot, setShot)

    def checkParameters(self):
        state = True
        for key in self.vars:
            if not self.vars[key]:
                state = False
                break
        if state:
            return True

        else:
            # Not all variables are set
            logging.warning('Not all parameters are specified!')
            dialog = GetDialog(self)
            dialog.prepareWidgets(self.vars)
            if dialog.exec_():
                self.vars = dialog.on_close()
                return self.checkParameters()
            else:
                # Canceled!
                return False

    def checkDestination(self):
        if self.dirpath == '' and self.runName == '':
            logging.warning('No location specified, saving stopped!')
            return False

        dir_path = self.dirpath + '/' + self.runName

        if os.path.exists(dir_path):
            logging.error('Directory already exists... Canceling!')
            return False

        return True

    @pyqtSlot()
    def getFromIDS(self):
        if not self.checkParameters():
            logging.warning('Not all parameters are set! Canceling.')
            self.cleanUp()
            return
        else:
            logging.info('All parameters set. Continuing.')

        if not self.checkDestination:
            return

        self.thread.setParameters(self.vars)
        self.thread.start()

    @pyqtSlot()
    def cleanUp(self):
        for key in self.vars:
            self.vars[key] = ''

class GetIDSWrapper:
    """This class gets the data from an IDS.

    You provide the necessary id parameters so the IDS can be accessed.

    Attributes:

    """

    def __init__(self, parameters):
        self.vars = {}
        self.setParameters(parameters)
        self.ids = imas.ids(self.vars[GetVars.shot], self.vars[GetVars.run])
        self.state = self.openIDS()

    def setParameters(self, parameters):
        for key in parameters:
            self.vars[key] = parameters[key]

    def openIDS(self):
        logging.info('Opening IDS')
        self.ids.open_env(self.vars[GetVars.user],
                          self.vars[GetVars.device],
                          self.vars[GetVars.version])
        if self.ids.isConnected():
            logging.info('IDS opened OK!')
            return True
        else:
            logging.error('IDS open failed!')
            return False

    def getIDS(self):
        return self.ids

if __name__ == '__main__':
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    root.addHandler(ch)

    # For launching python script directly from terminal with python command
    Vars = {}
    Help = """
            This is used for testing the plotting data from an edge_profilesIDS.

            In order to run this plugin, shot, run, user, device and version must
            be defined. Example (terminal):

            python3 solpswidget.py --shot=122264 --run=1 --user=penkod \
            --device=iter --version=3
            """
    try:
        opts, args = getopt.getopt(sys.argv[1:], "srudvh", ["dirpath=",
                                                            "shot=", "run=",
                                                            "user=", "device=",
                                                           "version=",
                                                           "help"])
        for opt, arg in opts:
            #print opt, arg
            if opt in ("-s", "--shot"):
                Vars[GetVars.shot] = int(arg)
            elif opt in ("-r", "--run"):
                Vars[GetVars.run] = int(arg)
            elif opt in ("-u", "--user"):
                Vars[GetVars.user] = arg
            elif opt in ("-t", "--device"):
                Vars[GetVars.device] = arg
            elif opt in ("-v", "--version"):
                Vars[GetVars.version] = arg
            if opt in ("-h", "--help"):
                print(Help % (os.environ['USER'], os.path.expanduser('~')))
                sys.exit()

    except Exception:
        print('Supplied option not recognized!')
        print('For help: -h / --help')
        sys.exit(2)

    if len(Vars) < GetVars.numOfParams:
        print('Not enough variables defined!')
        print('For help: -h / --help')
        sys.exit(2)
    elif len(Vars) > GetVars.numOfParams:
        print('Too many variables defined!')
        print('For help: -h / --help')
        sys.exit(2)

    ids = GetIDSWrapper(Vars).getIDS()
    from plotEPGGD import plotEPGGD
    plotEPGGD(ids).plotData()