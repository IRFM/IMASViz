import imas
import numpy as np
import wx
import os, sys
from imasviz.util.GlobalValues import GlobalValues
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import QMessageBox

class GlobalOperations:

    # Check if data source is available
    @staticmethod
    def check(dataSourceName, shotNumber):
        if dataSourceName == GlobalValues.TORE_SUPRA:
            shotMin = 28764  # TODO
            shotMax = 100000  # TODO
            if shotNumber < shotMin:
                raise ValueError("Shot number should be larger than " + str(shotMin))
            if shotNumber > shotMax:
                raise ValueError("Shot number should be smaller than " + str(shotMax))
        elif dataSourceName == GlobalValues.IMAS_NATIVE:
            return
        elif dataSourceName == GlobalValues.IMAS_UDA:
            return
        else:
            raise ValueError("Unknow data source " + dataSourceName + ".")

    @staticmethod
    def isTimeHomogeneous(ids, selectedNodeData):
        to_eval = "ids." + selectedNodeData['IDSName'] + ".ids_properties.homogeneous_time"
        homogeneous_time = eval(to_eval)
        if (homogeneous_time == 0):
            return False
        return True

    @staticmethod
    def getTime(ids, selectedNodeData, coordinate1):
        homogeneous_time = GlobalOperations.isTimeHomogeneous(ids, selectedNodeData)
        t = None
        if not (homogeneous_time):
            t = np.array(eval("ids." + selectedNodeData['IDSName'] + "." + coordinate1))
        else:
            t = np.array(eval("ids." + selectedNodeData['IDSName'] + ".time"))
        return t

    @staticmethod
    def ask(parent=None, message='', default_value=''):
        dlg = wx.TextEntryDialog(parent, message, value=default_value, style=wx.OK)
        dlg.ShowModal()
        result = dlg.GetValue()
        dlg.Destroy()
        return result

    @staticmethod
    def askWithCancel(parent=None, message='', default_value=''):
        dlg = wx.TextEntryDialog(parent, message, value=default_value, style=wx.OK|wx.CANCEL)
        cancel = dlg.ShowModal()
        result = dlg.GetValue()
        dlg.Destroy()
        return (cancel, result)

    @staticmethod
    def showMessage(parent=None, message=''):
        dlg = wx.MessageDialog(parent, message, style=wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    @staticmethod
    def YesNo(parent=None, question=None, caption='Confirm suppression'):
        w = QMessageBox()
        result = QMessageBox.question(w, caption, question, QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.No)
        if result == QMessageBox.Yes:
            return True
        else:
            return False

    @staticmethod # replace '[' by '(' and ']' by ')'
    def replaceBrackets(stringToReplace):
        if stringToReplace == None:
            return None
        c = stringToReplace.replace("[", "(")
        return c.replace("]", ")")

    @staticmethod  # replace '[' by '(' and ']' by ')'
    def replaceDotsBySlashes(stringToReplace):
        if stringToReplace == None:
            return None
        return stringToReplace.replace(".", "/")

    @staticmethod  # replace '[' by '(' and ']' by ')'
    def replaceDotsByUnderScores(stringToReplace):
        if stringToReplace == None:
            return None
        return stringToReplace.replace(".", "_")

    @staticmethod  # replace '[' by '(' and ']' by ')'
    def replaceSpacesByUnderScores(stringToReplace):
        if stringToReplace == None:
            return None
        return stringToReplace.replace(" ", "_")

    @staticmethod
    def getConfFilePath(configName, configType):
        """Get path + filename to configuration file ('.pcfg' or '.lsp').

        Parameters
        ----------

            configName: string
                Name of the configuration file (with no extension).
            configType: string
                Type/Extension of the configuration file, without dot
                ('pcfg' or 'lsp').

        """

        home = os.environ['HOME']
        if home == None:
            raise ValueError("HOME environment variable not defined")
        configurationDirectory = home + "/" + ".imasviz"
        if not os.path.exists(configurationDirectory):
            os.makedirs(configurationDirectory)

        if configType != None:
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
    def checkEnvSettings():
        if not GlobalValues.TESTING:

            print ("IMAS_VIZ production environment.")

            if 'HOME' not in os.environ:
                print ("Environment variable HOME not defined. Exiting.")
                sys.exit()

            if 'TS_MAPPINGS_DIR' not in os.environ:
                print ("Environment variable TS_MAPPINGS_DIR not defined. Exiting.")
                sys.exit()

            if 'IMAS_VERSION' not in os.environ:
                print ("Environment variable IMAS_VERSION not defined. Exiting.")
                sys.exit()

            if 'IMAS_DATA_DICTIONARIES_DIR' not in os.environ:
                print ("Environment variable IMAS_DATA_DICTIONARIES_DIR not defined. Exiting.")
                sys.exit()

            if 'IMAS_MAJOR_VERSION' not in os.environ:
                print ("Environment variable IMAS_MAJOR_VERSION not defined. Exiting.")
                sys.exit()

            if 'USER' not in os.environ:
                print ("Environment variable USER not defined. Exiting.")
                sys.exit()

            if 'VIZ_HOME' not in os.environ:
                print ("Environment variable VIZ_HOME not defined. Exiting.")
                sys.exit()

        else:

            print ("IMAS_VIZ testing environment.")

            if 'TS_MAPPINGS_DIR' not in os.environ:
                os.environ["TS_MAPPINGS_DIR"] = GlobalValues.TESTING_TS_MAPPINGS_DIR
                print ("WARNING: environment variable TS_MAPPINGS_DIR defined from testing environment.")

            if 'IMAS_VERSION' not in os.environ:
                os.environ["IMAS_VERSION"] = GlobalValues.TESTING_IMAS_VERSION
                print ("WARNING: environment variable IMAS_VERSION defined from testing environment.")

            if 'IMAS_DATA_DICTIONARIES_DIR' not in os.environ:
                os.environ["IMAS_DATA_DICTIONARIES_DIR"] = GlobalValues.TESTING_IMAS_DATA_DICTIONARIES_DIR
                print ("WARNING: environment variable IMAS_DATA_DICTIONARIES_DIR defined from testing environment.")

            if 'IMAS_MAJOR_VERSION' not in os.environ:
                os.environ["IMAS_MAJOR_VERSION"] = GlobalValues.TESTING_IMAS_MAJOR_VERSION
                print ("WARNING: environment variable IMAS_MAJOR_VERSION defined from testing environment.")

            if 'USER' not in os.environ:
                os.environ['USER'] = GlobalValues.TESTING_USER
                print ("WARNING: environment variable USER defined from testing environment.")

            if 'VIZ_HOME' not in os.environ:
                os.environ['VIZ_HOME'] = GlobalValues.TESTING_VIZ_HOME


    @staticmethod
    def getIDSDefFile(imas_dd_version):
        return os.environ['IMAS_DATA_DICTIONARIES_DIR'] + '/IDSDef_' + imas_dd_version + '.xml'

    # @staticmethod
    # def getListFromDict(dict):
    #     list = []
    #     for key in dict:
    #         list.append(dict[key])
    #     return list

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
        for i in range(0,len(l)):
            if l[i].endswith("." + configType):
                files.append(l[i])
        return files

    @staticmethod
    def getConfigurationFilesDirectory():
        return os.environ["HOME"] + "/.imasviz"

    # @staticmethod
    # def getSortedSelectedSignals(selectedSignals):
    #     selectedsignalsList = GlobalOperations.getListFromDict(selectedSignals)
    #     selectedsignalsList.sort(key=lambda x: x[2])
    #     return selectedsignalsList

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
        config = None
        if configFile != None:
            config = ET.parse(configFile)

        # Distinguish between the types of the configuration files
        # (.pcfg or .lsp)
        if configFile.endswith('.pcfg'):
            # Get all selectedArray attributes, containing signal paths,
            # from the config file
            selectedArrays = config.findall('.//*selectedArray')

            # Display number of signals, saved in the config file
            print("Config file: Number of signals: ", len(selectedArrays))

            # Extract the paths of the signals and add them to the pathsList
            for selectedSignal in selectedArrays:
                pathsList.append(selectedSignal.get("path"))

        elif configFile.endswith('lsp'):
            # Get all selectedArray attributes, containing signal paths,
            # from the config file
            selectedArrays = config.findall('.//*IDSPath')

            # Display number of signals, saved in the config file
            print("Config file: Number of signals: ", len(selectedArrays))

            # Extract the paths of the signals and add them to the pathsList
            for selectedPath in selectedArrays:
                pathsList.append(selectedPath.get("path"))

        return pathsList

    @staticmethod
    def getNextPanelKey(n, cols):
        a = n // cols
        b = n - (n // cols) * cols
        p = (a, b)
        return p


