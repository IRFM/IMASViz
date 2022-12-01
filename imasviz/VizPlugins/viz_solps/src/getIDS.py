#! /usr/bin/env python3

import sys
import os
import logging

from PySide2.QtCore import Slot, QThread, Signal, pyqtProperty
from PySide2.QtWidgets import (QApplication, QDialog, QLineEdit, QPushButton,
                             QGridLayout, QDialogButtonBox, QWidget,
                             QFormLayout, QLabel)
from PySide2.QtGui import QIntValidator
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

class GetIDSVars:
    names = ['Shot', 'Run', 'User', 'Device', 'IMAS Major Version']
    numOfParams = len(names)
    shot, run, user, device, version = range(numOfParams)

    defaultValues = {}
    defaultValues[shot] = '0'
    defaultValues[run] = '0'
    defaultValues[user] = os.getenv('USER')
    defaultValues[device] = ''
    defaultValues[version] = '3'

class GetIDSDialog(QDialog):
    """Dialog Demanding the shot, run, name and device for getting the data
    from IDS.
    """

    def __init__(self, parent=None):
        super(GetIDSDialog, self).__init__(parent)

    def prepareWidgets(self, parameters, title='IDS Variables', note=''):

        self.setModal(True)

        self.setWindowTitle(title)

        formLayout = QFormLayout(self)

        self.lineEditContainer = {}

        for i in range(GetIDSVars.numOfParams):
            currLineEdit = QLineEdit()
            currLineEdit.setText(GetIDSVars.names[i])
            self.lineEditContainer[i] = currLineEdit
            if parameters[i]:
                currLineEdit.setText(parameters[i])
            else:
                currLineEdit.setText(GetIDSVars.defaultValues[i])

            formLayout.addRow(GetIDSVars.names[i], currLineEdit)

        # Setting integer validator for run and shot numbers.
        self.lineEditContainer[GetIDSVars.run].setValidator(QIntValidator())
        self.lineEditContainer[GetIDSVars.shot].setValidator(QIntValidator())

        # Adding the Ok and Cancel button.
        dialog_button_box = QDialogButtonBox()
        dialog_button_box.setStandardButtons(QDialogButtonBox.Ok |
                                             QDialogButtonBox.Cancel)
        dialog_button_box.accepted.connect(self.accept)
        dialog_button_box.rejected.connect(self.reject)
        formLayout.addRow(dialog_button_box)

        # Add qlabel note below if given:
        if note != '':
            note_qlabel = QLabel(note)
            formLayout.addRow(note_qlabel)

    def getValue(self, Id):
        return self.lineEditContainer[Id].text()

    def on_close(self):
        # Returning a dictionary of values. The values are defined in
        # enumerator class GetIDSVars.

        variables = {}

        for i in range(GetIDSVars.numOfParams):
            variables[i] = self.getValue(i)

        # Checking if validating Integers.
        try:
            variables[GetIDSVars.shot] = int(variables[GetIDSVars.shot])
            variables[GetIDSVars.run] = int(variables[GetIDSVars.run])
        except ValueError as e:
            variables[GetIDSVars.shot] = -1
            variables[GetIDSVars.run] = -1

        return variables

class GetIDS(QWidget):
    """ Push button used for plugin."""
    finished = Signal()

    def __init__(self, parent=None):
        super(GetIDS, self).__init__(parent)

        self.vars = {}
        for i in range(GetIDSVars.numOfParams):
            # At the begining clear all parameters
            self.vars[i] = ''

        self.thread = GetIDSQThread(self)
        self.thread.finished.connect(self.cleanUp)

        self.pushButton = QPushButton(self)
        self.pushButton.setText("Get IDS")
        self.pushButton.clicked.connect(self.getFromIDS)
        self.pushButton.setEnabled(ENABLED)

        layout = QGridLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pushButton)
        self.setLayout(layout)

        self.thread.startFlag.connect(self.pushButton.setEnabled)
        self.thread.finished.connect(self.finished)

    @Slot(str)
    def setUser(self, user):
        self.vars[GetIDSVars.user] = user

    def getUser(self):
        return self.vars[GetIDSVars.user]

    user = pyqtProperty(str, getUser, setUser)

    @Slot(str)
    def setDevice(self, device):
        self.vars[GetIDSVars.device] = device

    def getDevice(self):
        return self.vars[GetIDSVars.device]

    device = pyqtProperty(str, getDevice, setDevice)

    @Slot(str)
    def setVersion(self, version):
        self.vars[GetIDSVars.device] = version

    def getVersion(self):
        return self.vars[GetIDSVars.device]

    version = pyqtProperty(str, getVersion, setVersion)

    @Slot(str)
    def setRun(self, run):
        self.vars[GetIDSVars.run] = run

    def getRun(self):
        return self.vars[GetIDSVars.run]

    runNumber = pyqtProperty(str, getRun, setRun)

    @Slot(str)
    def setShot(self, shot):
        self.vars[GetIDSVars.shot] = shot

    def getShot(self):
        return self.vars[GetIDSVars.shot]

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
            dialog = GetIDSDialog(self)
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

    @Slot()
    def getFromIDS(self):
        if not self.checkParameters():
            logging.warning('Not all parameters are set! Canceling.')
            self.cleanUp()
            return
        else:
            logging.info('All parameters set. Continuing.')

        if not self.checkDestination:
            return

    @Slot()
    def cleanUp(self):
        for key in self.vars:
            self.vars[key] = ''

class GetIDSQThread(QThread):
    """QThread for getting data from an IDS from a separate thread.
    """
    startFlag = Signal(bool)

    def __init__(self, parent=None):
        super(GetIDSQThread, self).__init__(parent)
        self.parent = parent
        self.vars = {}
        for i in range(GetIDSVars.numOfParams):
            self.vars[i] = None
        self.finished.connect(self.on_finish)
        self.started.connect(self.on_start)

    def setParameters(self, parameters):
        """Function that sets the parameters necessary for accessing IDS.
        """
        for key in parameters:
            self.vars[key] = parameters[key]

    def run(self):
        ids = GetIDSWrapper(self.vars)
        # if ids.state:
        #     ids.plotData()
        # else:
        #     logging.warning('IDS did not open correctly.')

    @Slot()
    def on_start(self):
        logging.info('Plugin start')
        self.startFlag.emit(False)

    @Slot()
    def on_finish(self):
        logging.info('Plugin finished')
        self.startFlag.emit(True)


class GetIDSWrapper:
    """This class gets the data from an IDS.

    You provide the necessary id parameters so the IDS can be accessed.

    Attributes:

    """

    def __init__(self, parameters):
        self.vars = {}
        self.setParameters(parameters)
        self.ids = imas.ids(self.vars[GetIDSVars.shot], self.vars[GetIDSVars.run])
        self.state = self.openIDS()

    def setParameters(self, parameters):
        for key in parameters:
            self.vars[key] = parameters[key]

    def openIDS(self):
        logging.info('Opening IDS')
        self.ids.open_env(self.vars[GetIDSVars.user],
                          self.vars[GetIDSVars.device],
                          self.vars[GetIDSVars.version])
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
                Vars[GetIDSVars.shot] = int(arg)
            elif opt in ("-r", "--run"):
                Vars[GetIDSVars.run] = int(arg)
            elif opt in ("-u", "--user"):
                Vars[GetIDSVars.user] = arg
            elif opt in ("-t", "--device"):
                Vars[GetIDSVars.device] = arg
            elif opt in ("-v", "--version"):
                Vars[GetIDSVars.version] = arg
            if opt in ("-h", "--help"):
                print(Help % (os.environ['USER'], os.path.expanduser('~')))
                sys.exit()

    except Exception:
        print('Supplied option not recognized!')
        print('For help: -h / --help')
        sys.exit(2)

    if len(Vars) < GetIDSVars.numOfParams:
        print('Not enough variables defined!')
        print('For help: -h / --help')
        sys.exit(2)
    elif len(Vars) > GetIDSVars.numOfParams:
        print('Too many variables defined!')
        print('For help: -h / --help')
        sys.exit(2)

    # app = QApplication(sys.argv)
    # ids = GetIDSWrapper(Vars).getIDS()
    # sys.exit(app.exec_())

    app = QApplication(sys.argv)
    t = GetIDSQThread()
    t.setParameters(Vars)
    t.finished.connect(app.exit)
    t.start()
    sys.exit(app.exec_())
