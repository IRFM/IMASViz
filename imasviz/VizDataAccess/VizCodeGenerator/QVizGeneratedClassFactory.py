import os
import sys
import importlib

from imasviz.VizUtils import QVizGlobalValues, QVizGlobalOperations
from imasviz.VizUtils import QVizPreferences
from imasviz.VizDataAccess.VizCodeGenerator import QVizDataAccessCodeGenerator

# Append imasviz source path
sys.path.append(os.environ['HOME'] + "/.imasviz/VizGeneratedCode")

class QVizGeneratedClassFactory:
    def __init__(self, IMASDataSource, view, IDSName, occurrence=0,
                 asynch=True):
        self.IDSName = IDSName
        self.IMASDataSource = IMASDataSource
        self.view = view
        self.occurrence = occurrence
        self.asynch = asynch

    def create(self, progressBar=None):

        XMLParser = None

        imas_dd_version = self.IMASDataSource.data_dictionary_version

        if imas_dd_version is None or imas_dd_version is '':
            imas_dd_version = os.environ['IMAS_VERSION']

        if QVizGlobalValues.TESTING:
            imas_dd_version = QVizGlobalValues.TESTING_IMAS_VERSION

        if QVizPreferences.Ignore_GGD == 0:

            if imas_dd_version == "3.7.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_7_0 \
                    import IDSDef_XMLParser_Full_Generated_3_7_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.9.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_9_0 \
                    import IDSDef_XMLParser_Full_Generated_3_9_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.9.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_9_1 \
                    import IDSDef_XMLParser_Full_Generated_3_9_1 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.11.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_11_0 \
                    import IDSDef_XMLParser_Full_Generated_3_11_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.12.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_12_0 \
                    import IDSDef_XMLParser_Full_Generated_3_12_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.15.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_15_0 \
                    import IDSDef_XMLParser_Full_Generated_3_15_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.15.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_15_1 \
                    import IDSDef_XMLParser_Full_Generated_3_15_1 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.16.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_16_0 \
                    import IDSDef_XMLParser_Full_Generated_3_16_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.17.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_17_0 \
                    import IDSDef_XMLParser_Full_Generated_3_17_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.17.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_17_1 \
                    import IDSDef_XMLParser_Full_Generated_3_17_1 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.17.2":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_17_2 \
                    import IDSDef_XMLParser_Full_Generated_3_17_2 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.18.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_18_0 \
                    import IDSDef_XMLParser_Full_Generated_3_18_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.19.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_19_0 \
                    import IDSDef_XMLParser_Full_Generated_3_19_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.19.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_19_1 \
                    import IDSDef_XMLParser_Full_Generated_3_19_1 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.20.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_20_0 \
                    import IDSDef_XMLParser_Full_Generated_3_20_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.21.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_21_0 \
                    import IDSDef_XMLParser_Full_Generated_3_21_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.21.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_21_1 \
                    import IDSDef_XMLParser_Full_Generated_3_21_1 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.22.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_22_0 \
                    import IDSDef_XMLParser_Full_Generated_3_22_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.23.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_23_1 \
                    import IDSDef_XMLParser_Full_Generated_3_23_1 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.23.2":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_23_2 \
                    import IDSDef_XMLParser_Full_Generated_3_23_2 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.23.3":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_23_3 \
                    import IDSDef_XMLParser_Full_Generated_3_23_3 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.24.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_24_0 \
                    import IDSDef_XMLParser_Full_Generated_3_24_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.25.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_25_0 \
                    import IDSDef_XMLParser_Full_Generated_3_25_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.26.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_26_0 \
                    import IDSDef_XMLParser_Full_Generated_3_26_0 as IDSDef_XMLParser_Full_Generated
            elif imas_dd_version == "3.27.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_27_0 \
                    import IDSDef_XMLParser_Full_Generated_3_27_0 as IDSDef_XMLParser_Full_Generated
            else:
                className = "IDSDef_XMLParser_Full_Generated_" + \
                    QVizGlobalOperations.replaceDotsByUnderScores(imas_dd_version)
                IDSDef_parser_path = os.environ['HOME'] + "/.imasviz/VizGeneratedCode/" \
                    + className + ".py"
                print("IDSDef parser path: ", IDSDef_parser_path)
                if not os.path.exists(IDSDef_parser_path):
                    print(f"Generating full parsers for IMAS {os.environ['IMAS_VERSION']}")
                    dag = QVizDataAccessCodeGenerator.QVizDataAccessCodeGenerator(os.environ['IMAS_VERSION'], GGD_ignore=1)
                    print("End of code generation")
                # full_module_name = className
                moduleName = className

                IDSDef_XMLParser_Full_Generated = getattr(importlib.import_module(moduleName), className)

                # raise ValueError("IMAS dictionary version not supported:" + imas_dd_version)
            XMLParser = IDSDef_XMLParser_Full_Generated(
                userName=self.IMASDataSource.userName,
                imasDbName=self.IMASDataSource.imasDbName,
                shotNumber=self.IMASDataSource.shotNumber,
                runNumber=self.IMASDataSource.runNumber,
                view=self.view,
                IDSName=self.IDSName,
                occurrence=self.occurrence,
                asynch=self.asynch)

        else:

            if imas_dd_version == "3.7.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_7_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_7_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.9.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_9_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_9_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.9.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_9_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_9_1 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.11.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_11_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_11_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.12.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_12_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_12_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.15.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_15_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_15_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.15.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_15_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_15_1 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.16.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_16_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_16_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.17.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_17_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_17_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.17.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_17_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_17_1 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.17.2":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_17_2 \
                    import IDSDef_XMLParser_Partial_Generated_3_17_2 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.18.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_18_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_18_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.19.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_19_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_19_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.19.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_19_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_19_1 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.20.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_20_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_20_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.21.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_21_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_21_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.21.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_21_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_21_1 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.22.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_22_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_22_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.23.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_23_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_23_1 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.23.2":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_23_2 \
                    import IDSDef_XMLParser_Partial_Generated_3_23_2 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.23.3":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_23_3 \
                    import IDSDef_XMLParser_Partial_Generated_3_23_3 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.24.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_24_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_24_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.25.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_25_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_25_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.26.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_26_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_26_0 as IDSDef_XMLParser_Partial_Generated
            elif imas_dd_version == "3.27.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_27_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_27_0 as IDSDef_XMLParser_Partial_Generated
            else:
                className = "IDSDef_XMLParser_Partial_Generated_" + \
                    QVizGlobalOperations.replaceDotsByUnderScores(imas_dd_version)
                IDSDef_parser_path = os.environ['HOME'] + "/.imasviz/VizGeneratedCode/" \
                    + className + ".py"
                print("IDSDef parser path: ", IDSDef_parser_path)
                if not os.path.exists(IDSDef_parser_path):
                    print(f"Generating full parsers for IMAS {os.environ['IMAS_VERSION']}")
                    dag = QVizDataAccessCodeGenerator.QVizDataAccessCodeGenerator(os.environ['IMAS_VERSION'], GGD_ignore=1)
                    print("End of code generation")
                # full_module_name = className
                moduleName = className

                IDSDef_XMLParser_Partial_Generated = getattr(importlib.import_module(moduleName), className)

                # raise ValueError("IMAS dictionary version not supported:" + imas_dd_version)

            XMLParser = IDSDef_XMLParser_Partial_Generated(
                userName=self.IMASDataSource.userName,
                imasDbName=self.IMASDataSource.imasDbName,
                shotNumber=self.IMASDataSource.shotNumber,
                runNumber=self.IMASDataSource.runNumber,
                view=self.view,
                IDSName=self.IDSName,
                occurrence=self.occurrence,
                asynch=self.asynch)

        XMLParser.setProgressBar(progressBar)

        return XMLParser
