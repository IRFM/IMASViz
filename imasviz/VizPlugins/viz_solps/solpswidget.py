#! /usr/bin/env python3

import sys
# import tarfile
# import base64
import os
import logging

from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, pyqtProperty
from PyQt5.QtWidgets import (QApplication, QDialog, QLineEdit, QPushButton,
                             QGridLayout, QDialogButtonBox, QWidget,
                             QFormLayout)
from PyQt5.QtGui import QIntValidator
import getopt

# try:
#     import BytesIO
# except ImportError as e:
#     from io import BytesIO


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


class GetDialog(QDialog):
    """Dialog Demanding the shot, run, name and device for getting the data
    from IDS.
    """

    def __init__(self, parent=None):
        super(GetDialog, self).__init__(parent)

    def prepareWidgets(self, parameters, title='IDS Variables',):

        self.setModal(True)

        self.setWindowTitle(title)

        formLayout = QFormLayout(self)

        self.lineEditContainer = {}

        for i in range(GetVars.numOfParams):
            currLineEdit = QLineEdit()
            currLineEdit.setText(GetVars.names[i])
            self.lineEditContainer[i] = currLineEdit
            if parameters[i]:
                currLineEdit.setText(parameters[i])
            else:
                currLineEdit.setText(GetVars.defaultValues[i])

            formLayout.addRow(GetVars.names[i], currLineEdit)

        # Setting integer validator for run and shot numbers.
        self.lineEditContainer[GetVars.run].setValidator(QIntValidator())
        self.lineEditContainer[GetVars.shot].setValidator(QIntValidator())

        # Adding the Ok and Cancel button.
        dialog_button_box = QDialogButtonBox()
        dialog_button_box.setStandardButtons(QDialogButtonBox.Ok |
                                             QDialogButtonBox.Cancel)
        dialog_button_box.accepted.connect(self.accept)
        dialog_button_box.rejected.connect(self.reject)
        formLayout.addRow(dialog_button_box)

    def getValue(self, Id):
        return self.lineEditContainer[Id].text()

    def on_close(self):
        # Returning a dictionary of values. The values are defined in
        # enumerator class GetVars.

        variables = {}

        for i in range(GetVars.numOfParams):
            variables[i] = self.getValue(i)

        # Checking if validating Integers.
        try:
            variables[GetVars.shot] = int(variables[GetVars.shot])
            variables[GetVars.run] = int(variables[GetVars.run])
        except ValueError as e:
            variables[GetVars.shot] = -1
            variables[GetVars.run] = -1

        return variables


class GetSOLPSWidget(QWidget):
    """ Push button used for plugin."""
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super(GetSOLPSWidget, self).__init__(parent)

        self.vars = {}
        for i in range(GetVars.numOfParams):
            # At the begining clear all parameters
            self.vars[i] = ''

        self.thread = GetSOLPSWidgetQThread(self)
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


class GetSOLPSWidgetQThread(QThread):
    """QThread for getting data from an IDS from a separate thread.
    """
    startFlag = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(GetSOLPSWidgetQThread, self).__init__(parent)
        self.parent = parent
        self.vars = {}
        for i in range(GetVars.numOfParams):
            self.vars[i] = None
        self.finished.connect(self.on_finish)
        self.started.connect(self.on_start)

    def setParameters(self, parameters):
        """Function that sets the parameters necessary for accessing IDS.
        """
        for key in parameters:
            self.vars[key] = parameters[key]

    def run(self):
        ids = GetSOLPSWidgetWrapper(self.vars)
        # Data is saved if the self.dirpath and self.runName were provided.
        if ids.state:
            ids.plotData()
        else:
            logging.warning('IDS did not open correctly.')

    @pyqtSlot()
    def on_start(self):
        logging.info('Getting IDS...')
        self.startFlag.emit(False)

    @pyqtSlot()
    def on_finish(self):
        logging.info('Finished reading from IDS.')
        self.startFlag.emit(True)


class GetSOLPSWidgetWrapper:
    """This class gets the data from an IDS and save it to a directory.

    You provide the necessary id parameters so the IDS can be accessed, then
    the data is written to the directory you specify.

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

    def plotData(self):
        """Plots edge data to 2D VTK.
        """
        pass
        # TODO


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

    app = QApplication(sys.argv)
    t = GetSOLPSWidgetQThread()
    t.setParameters(Vars)
    t.finished.connect(app.exit)
    t.start()
    sys.exit(app.exec_())
