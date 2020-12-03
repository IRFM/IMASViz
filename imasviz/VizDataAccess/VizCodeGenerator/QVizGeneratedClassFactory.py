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

        if imas_dd_version is None or imas_dd_version == '':
            imas_dd_version = os.environ['IMAS_VERSION']

        if QVizGlobalValues.TESTING:
            imas_dd_version = QVizGlobalValues.TESTING_IMAS_VERSION

        if QVizPreferences.Ignore_GGD == 0:

            className = "IDSDef_XMLParser_Full_Generated_" + \
                QVizGlobalOperations.replaceDotsByUnderScores(imas_dd_version)

            path_user_gencode = IDSDef_parser_path = os.environ['HOME'] + \
                "/.imasviz/VizGeneratedCode/"
            if not os.path.exists(path_user_gencode):
                os.makedirs(path_user_gencode)

            IDSDef_parser_path = os.environ['HOME'] + \
                "/.imasviz/VizGeneratedCode/" + className + ".py"
            print("IDSDef parser path: ", IDSDef_parser_path)
            if not os.path.exists(IDSDef_parser_path):
                print("Generating full parsers for IMAS "
                      f"{os.environ['IMAS_VERSION']}")
                dag = QVizDataAccessCodeGenerator. \
                    QVizDataAccessCodeGenerator(os.environ['IMAS_VERSION'],
                                                GGD_ignore=1)
                print("End of code generation")
            # full_module_name = className
            moduleName = className

            IDSDef_XMLParser_Full_Generated = \
                getattr(importlib.import_module(moduleName), className)

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

        else: # If QVizPreferences.Ignore_GGD == 1
            className = "IDSDef_XMLParser_Partial_Generated_" + \
                QVizGlobalOperations.replaceDotsByUnderScores(imas_dd_version)

            path_user_gencode = IDSDef_parser_path = os.environ['HOME'] + \
                "/.imasviz/VizGeneratedCode/"
            if not os.path.exists(path_user_gencode):
                os.makedirs(path_user_gencode)

            IDSDef_parser_path = os.environ['HOME'] + \
                "/.imasviz/VizGeneratedCode/" + className + ".py"
            print("IDSDef parser path: ", IDSDef_parser_path)
            if not os.path.exists(IDSDef_parser_path):
                print("Generating full parsers for IMAS "
                      f"{os.environ['IMAS_VERSION']}")
                dag = QVizDataAccessCodeGenerator. \
                    QVizDataAccessCodeGenerator(os.environ['IMAS_VERSION'],
                                                GGD_ignore=1)
                print("End of code generation")
            # full_module_name = className
            moduleName = className

            IDSDef_XMLParser_Partial_Generated = \
                getattr(importlib.import_module(moduleName), className)

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
