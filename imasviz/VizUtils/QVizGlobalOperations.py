# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import os
import sys

import numpy as np
from PySide6.QtWidgets import QMessageBox, QInputDialog, QLineEdit
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues


class QVizGlobalOperations:

    # Check if data source is available
    @staticmethod
    def check(dataSourceName):
        if dataSourceName == QVizGlobalValues.IMAS_NATIVE:
            return
        elif dataSourceName == QVizGlobalValues.IMAS_UDA:
            return
        else:
            raise ValueError("Unknow data source " + dataSourceName + ".")

    @staticmethod
    def isTimeHomogeneous(selectedNode):
        selectedNodeData = selectedNode.getData()
        to_eval = selectedNodeData['IDSName'] + ".ids_properties.homogeneous_time"
        homogeneous_time = selectedNode.evalPath(to_eval)
        if homogeneous_time == 0:
            return False
        return True

    @staticmethod
    def getCoordinate_array(selectedNode, coordinate):
        if coordinate is None:
            return None
        selectedNodeData = selectedNode.getData()
        homogeneous_time = QVizGlobalOperations.isTimeHomogeneous(selectedNode)
        t = None
        try:
            if not homogeneous_time:
                t = np.array(selectedNode.evalPath(selectedNodeData['IDSName'] + "." + coordinate))
            else:
                t = np.array(selectedNode.evalPath(selectedNodeData['IDSName'] + ".time"))
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
    def replaceDashesByUnderScores(stringToReplace):
        if stringToReplace is None:
            return None
        return stringToReplace.replace("-", "_")

    @staticmethod  # replace '[' by '(' and ']' by ')'
    def replaceSpacesByUnderScores(stringToReplace):
        if stringToReplace is None:
            return None
        return stringToReplace.replace(" ", "_")

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
    def getNextPanelKey(n, ncols):
        a = n // ncols
        b = n - (n // ncols) * ncols
        p = (a, b)
        return p

    @staticmethod
    def makeIMASPaths(paths):
        i = 0
        paths_copy = paths
        paths = []
        for path in paths_copy:
            paths.append(QVizGlobalOperations.makeIMASPath(path))
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

    @staticmethod
    def makePythonPath(path):
        path = path.replace('(', '[')
        path = path.replace(')', ']')
        path = path.replace('/', '.')
        path = path.replace('(:)', '')
        return path

    @staticmethod
    def askForShot():
        uri = None
        uri, ok = QInputDialog.getText(None, "URI",
                                             "enter an URI")
        return (ok, uri)
