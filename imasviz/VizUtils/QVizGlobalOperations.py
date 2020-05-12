import os
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QLineEdit
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues


class QVizGlobalOperations:

    # Check if data source is available
    @staticmethod
    def check(dataSourceName, shotNumber):
        if dataSourceName == QVizGlobalValues.TORE_SUPRA:
            shotMin = 28764  # TODO
            shotMax = 100000  # TODO
            if shotNumber < shotMin:
                raise ValueError("Shot number should be larger than "
                                 + str(shotMin))
            if shotNumber > shotMax:
                raise ValueError("Shot number should be smaller than "
                                 + str(shotMax))
        elif dataSourceName == QVizGlobalValues.IMAS_NATIVE:
            return
        elif dataSourceName == QVizGlobalValues.IMAS_UDA:
            return
        else:
            raise ValueError("Unknow data source " + dataSourceName + ".")

    @staticmethod
    def isTimeHomogeneous(ids, selectedNodeData):
        to_eval = "ids." + selectedNodeData['IDSName'] \
            + ".ids_properties.homogeneous_time"
        homogeneous_time = eval(to_eval)
        if (homogeneous_time == 0):
            return False
        return True

    @staticmethod
    def getCoordinate1D_array(ids, selectedNodeData, coordinate1):
        if coordinate1 is None:
            return None
        homogeneous_time = QVizGlobalOperations.isTimeHomogeneous(ids, selectedNodeData)
        t = None
        try:
            if not homogeneous_time:
                t = np.array(eval("ids." + selectedNodeData['IDSName'] + "."
                             + coordinate1))
            else:
                t = np.array(eval("ids." + selectedNodeData['IDSName']
                             + ".time"))
            return t
        except ValueError:
            return None

    @staticmethod
    def message(parent=None, message='', title=''):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle(title)
        msg.exec_()

    @staticmethod
    def askWithCancel(parent=None, title='', message='', default_value=''):
        # Set and show dialog
        dlg = QInputDialog()
        text, ok = dlg.getText(parent, title, message)
        # If text was not defined (input dialog was left empty)
        if text == '':
            text = default_value
        # Return text and OK/CANCEL value (True/False)
        return text, ok

    @staticmethod
    def YesNo(parent=None, question=None, caption='Confirm suppression'):
        w = QMessageBox()
        result = QMessageBox.question(w, caption, question,
                                      QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.No)
        if result == QMessageBox.Yes:
            return True
        else:
            return False

    @staticmethod  # replace '[' by '(' and ']' by ')'
    def replaceBrackets(stringToReplace):
        if stringToReplace is None:
            return None
        c = stringToReplace.replace("[", "(")
        return c.replace("]", ")")

    @staticmethod  # replace '[' by '(' and ']' by ')'
    def replaceDotsBySlashes(stringToReplace):
        if stringToReplace is None:
            return None
        return stringToReplace.replace(".", "/")

    @staticmethod  # replace '[' by '(' and ']' by ')'
    def replaceDotsByUnderScores(stringToReplace):
        if stringToReplace is None:
            return None
        return stringToReplace.replace(".", "_")

    @staticmethod  # replace '[' by '(' and ']' by ')'
    def replaceSpacesByUnderScores(stringToReplace):
        if stringToReplace is None:
            return None
        return stringToReplace.replace(" ", "_")

    @staticmethod
    def getConfFilePath(configName, configType):
        """Get path + filename to configuration file ('.pcfg' or '.lsp').

        Arguments
            configName (str) : Name of the configuration file (with no
                               extension).
            configType (str) : Type/Extension of the configuration file,
                               without dot ('pcfg' or 'lsp').
        """

        home = os.environ['HOME']
        if home is None:
            raise ValueError("HOME environment variable not defined")
        configurationDirectory = home + "/" + ".imasviz"
        if not os.path.exists(configurationDirectory):
            os.makedirs(configurationDirectory)

        if configType is not None:
            configurationFilePath = configurationDirectory + "/" + \
                configName + "." + configType
        else:
            print('getConfFilePath: File type not specified!')
            return

        return configurationFilePath

    @staticmethod
    def printCode(file, text, level):
        n = level + 1
        tabs = ''
        i = 0
        while i < n:
            tabs += '\t'
            i += 1

        file.write(tabs + text.encode("utf-8") + "\n")

    @staticmethod
    def checkEnvSettings_generator():
        """Check if the mandatory systems variables are set.
        """
        if not QVizGlobalValues.TESTING:

            print("IMAS_VIZ production environment.")

            if 'HOME' not in os.environ:
                print("Environment variable HOME not defined. Exiting.")
                sys.exit()

            if 'TS_MAPPINGS_DIR' not in os.environ:
                print("Environment variable TS_MAPPINGS_DIR not defined. Exiting.")
                sys.exit()

            if 'IMAS_DATA_DICTIONARIES_DIR' not in os.environ:
                print("Environment variable IMAS_DATA_DICTIONARIES_DIR not defined. Exiting.")
                sys.exit()

            if 'USER' not in os.environ:
                print("Environment variable USER not defined. Exiting.")
                sys.exit()

            if 'VIZ_HOME' not in os.environ:
                print("Environment variable VIZ_HOME not defined. Exiting.")
                sys.exit()

        else:

            print("IMAS_VIZ testing environment.")

            if 'TS_MAPPINGS_DIR' not in os.environ:
                os.environ["TS_MAPPINGS_DIR"] = QVizGlobalValues.TESTING_TS_MAPPINGS_DIR
                print("WARNING: environment variable TS_MAPPINGS_DIR defined from testing environment.")

            if 'IMAS_DATA_DICTIONARIES_DIR' not in os.environ:
                os.environ["IMAS_DATA_DICTIONARIES_DIR"] = QVizGlobalValues.TESTING_IMAS_DATA_DICTIONARIES_DIR
                print("WARNING: environment variable IMAS_DATA_DICTIONARIES_DIR defined from testing environment.")

            if 'USER' not in os.environ:
                os.environ['USER'] = QVizGlobalValues.TESTING_USER
                print("WARNING: environment variable USER defined from testing environment.")

            if 'VIZ_HOME' not in os.environ:
                os.environ['VIZ_HOME'] = QVizGlobalValues.TESTING_VIZ_HOME

    @staticmethod
    def checkEnvSettings():
        """Check if the mandatory systems variables are set.
        """
        if not QVizGlobalValues.TESTING:

            print("IMAS_VIZ production environment.")

            if 'HOME' not in os.environ:
                print("Environment variable HOME not defined. Exiting.")
                sys.exit()

            if 'TS_MAPPINGS_DIR' not in os.environ:
                print("Environment variable TS_MAPPINGS_DIR not defined. Exiting.")
                sys.exit()

            if 'IMAS_VERSION' not in os.environ:
                print("Environment variable IMAS_VERSION not defined. Exiting.")
                sys.exit()

            if 'IMAS_DATA_DICTIONARIES_DIR' not in os.environ:
                print("Environment variable IMAS_DATA_DICTIONARIES_DIR not defined. Exiting.")
                sys.exit()

            if 'IMAS_MAJOR_VERSION' not in os.environ:
                print("Environment variable IMAS_MAJOR_VERSION not defined. Exiting.")
                sys.exit()

            if 'USER' not in os.environ:
                print("Environment variable USER not defined. Exiting.")
                sys.exit()

            if 'VIZ_HOME' not in os.environ:
                print("Environment variable VIZ_HOME not defined. Exiting.")
                sys.exit()

        else:

            print("IMAS_VIZ testing environment.")

            if 'TS_MAPPINGS_DIR' not in os.environ:
                os.environ["TS_MAPPINGS_DIR"] = QVizGlobalValues.TESTING_TS_MAPPINGS_DIR
                print("WARNING: environment variable TS_MAPPINGS_DIR defined from testing environment.")

            if 'IMAS_VERSION' not in os.environ:
                os.environ["IMAS_VERSION"] = QVizGlobalValues.TESTING_IMAS_VERSION
                print("WARNING: environment variable IMAS_VERSION defined from testing environment.")

            if 'IMAS_DATA_DICTIONARIES_DIR' not in os.environ:
                os.environ["IMAS_DATA_DICTIONARIES_DIR"] = QVizGlobalValues.TESTING_IMAS_DATA_DICTIONARIES_DIR
                print("WARNING: environment variable IMAS_DATA_DICTIONARIES_DIR defined from testing environment.")

            if 'IMAS_MAJOR_VERSION' not in os.environ:
                os.environ["IMAS_MAJOR_VERSION"] = QVizGlobalValues.TESTING_IMAS_MAJOR_VERSION
                print("WARNING: environment variable IMAS_MAJOR_VERSION defined from testing environment.")

            if 'USER' not in os.environ:
                os.environ['USER'] = QVizGlobalValues.TESTING_USER
                print("WARNING: environment variable USER defined from testing environment.")

            if 'VIZ_HOME' not in os.environ:
                os.environ['VIZ_HOME'] = QVizGlobalValues.TESTING_VIZ_HOME

    @staticmethod
    def getIDSDefFile(imas_dd_version):
        """Get IDSDef.xml file. If not present in IMASViz try to find it in
        $IMAS_PREFIX
        """
        # An optional system variable for setting path to IDSDef.xml file in
        # case they're located on some non-standard location.
        # Note that other paths won't be
        IDSDef_path = None
        if "IDSDEF_PATH" in os.environ:
            IDSDef_path = os.environ['IDSDEF_PATH'] + "/IDSDef.xml"
        else:
            IDSDef_path = os.environ['IMAS_DATA_DICTIONARIES_DIR'] \
                + '/IDSDef_' + imas_dd_version + '.xml'

        if os.path.exists(IDSDef_path) is False and 'IMAS_PREFIX' in os.environ:
            # Assuming that the IDSDef.xml file is present in
            # $IMAS_PREFIX/include directory (method used on both the ITER HPC
            # and on the GATEWAY clusters)
            IDSDef_path = os.environ['IMAS_PREFIX'] + "/include/IDSDef.xml"

        if IDSDef_path is None:
            print("WARNING: no suitable IDSDef.xml file found for given IMAS "
                  "version " + imas_dd_version + ".")
        return IDSDef_path

    @staticmethod
    def getIDSDefParserFilePath(imas_dd_version, GGD=False):
        """Get IDSDef_XMLParser file.
        """

        filePath = None

        if GGD is True:
            filePath = os.environ["HOME"] + "/.imasviz/VizGeneratedCode/" + \
                           "IDSDef_XMLParser_Full_Generated_" + \
                           QVizGlobalOperations.replaceDotsByUnderScores(imas_dd_version) + \
                           ".py"
        else:
            filePath = os.environ["HOME"] + "/.imasviz/VizGeneratedCode/" + \
                       "IDSDef_XMLParser_Partial_Generated_" + \
                       QVizGlobalOperations.replaceDotsByUnderScores(imas_dd_version) + \
                       ".py"

        if not os.path.exists(filePath):
            print("WARNING: No suitable IDSDef_XMLParser file found.")

    @staticmethod
    def getConfFilesList(configType):
        """Get a list of configuration files of certain type.

        Parameters
        ----------

        configType: string
            Type/Extension of the configuration file, without dot
            (e.c. 'pcfg', 'lsp'...).

        """
        files = []
        configurationDirectory = os.environ["HOME"] + "/.imasviz"
        if not os.path.exists(configurationDirectory):
            os.makedirs(configurationDirectory)
        l = os.listdir(configurationDirectory)
        for i in range(0, len(l)):
            if l[i].endswith("." + configType):
                files.append(l[i])
        return files

    @staticmethod
    def getConfigurationFilesDirectory():
        return os.environ["HOME"] + "/.imasviz"

    @staticmethod
    def getSignalsPathsFromConfigurationFile(configFile):
        """Get the signal paths from the configuration file (.pcfg or .lsp).

        Parameters
        ----------

        configFile: string
            Full path to configuration file including file name
            (.pcfg or .lsp file).
        """

        selectedsignalsMap = {}
        pathsList = []
        occurrencesList = []
        pathsMap = {}
        config = None
        if configFile != None:
            config = ET.parse(configFile)

        # Distinguish between the types of the configuration files
        # (.pcfg or .lsp)
        if configFile.endswith('.pcfg'):
            # Get all selectedArray attributes, containing signal paths,
            # from the config file
            selectedArrays = config.findall('.//*sourceInfo')

            # Display number of signals, saved in the config file
            print("Config file: Number of signals: ", len(selectedArrays))

            # Extract the paths of the signals and add them to the pathsList
            for selectedSignal in selectedArrays:
                pathsList.append(selectedSignal.get("path"))
                occurrencesList.append(selectedSignal.get("occurrence"))

        elif configFile.endswith('lsp'):
            # Get all selectedArray attributes, containing signal paths,
            # from the config file
            selectedArrays = config.findall('.//*IDSPath')

            # Display number of signals, saved in the config file
            print("Config file: Number of signals: ", len(selectedArrays))

            # Extract the paths of the signals and add them to the pathsList
            for selectedPath in selectedArrays:
                pathsList.append(selectedPath.get("path"))
                occurrencesList.append(selectedPath.get("occurrence"))

        pathsMap['paths'] = pathsList
        pathsMap['occurrences'] = occurrencesList
        return pathsMap

    @staticmethod
    def getNextPanelKey(n, ncols):
        a = n // ncols
        b = n - (n // ncols) * ncols
        p = (a, b)
        return p

    @staticmethod
    def makeIMASPaths(paths):
        i = 0
        for path in paths:
            paths[i] = QVizGlobalOperations.makeIMASPath(path)
            i += 1
        return paths

    @staticmethod
    def makeIMASPath(path):
        path = path.replace('[', '(')
        path = path.replace(']', ')')
        path = path.replace('.', '/')
        return path

    @staticmethod
    def makePythonPaths(paths):
        i = 0
        for path in paths:
            paths[i] = QVizGlobalOperations.makePythonPath(path)
            i += 1
        return paths

    def makePythonPath(path):
        path = path.replace('(', '[')
        path = path.replace(')', ']')
        path = path.replace('/', '.')
        path = path.replace('(:)', '')
        return path

    @staticmethod
    def askForShot():
        shotNumber = None
        runNumber = None
        userName = None
        database = None
        shotNumber, ok = QInputDialog.getInt(None, "Shot number",
                                             "enter a shot number")
        if not ok:
            return (ok, shotNumber, runNumber, userName, database)
        else:
            runNumber, ok = QInputDialog.getInt(None, "Run number",
                                                "enter the run number of shot " + str(shotNumber))
            if not ok:
                return (ok, shotNumber, runNumber, userName, database)
            else:
                userName, ok = QInputDialog.getText(None, 'User name',
                                                    "enter user name",
                                                    QLineEdit.Normal, "")
                if not ok:
                    return (ok, shotNumber, runNumber, userName, database)
                else:
                    database, ok = QInputDialog.getText(None, 'database',
                                                        "enter database",
                                                        QLineEdit.Normal, "")
                    if not ok:
                        return (ok, shotNumber, runNumber, userName, database)

        return (ok, shotNumber, runNumber, userName, database)
