import os
import sys
import importlib

import logging
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

        imas_dd_version = os.environ['IMAS_VERSION']
        ids_dd_version = self.IMASDataSource.data_dictionary_version

        if (( ids_dd_version is not None and ids_dd_version != '') and ids_dd_version < '3.26.0'):
            if imas_dd_version >  ids_dd_version:
                logging.warning("Non backward compatible change infos are not available for"
                                " IDSs created with DD version prior to 3.26.0. You should use"
                                " an older version of IMAS Access Layer to access data for DD "
                                "fields that have been renamed. If it is the case, quit IMASViz and load an older "
                                "IMAS Access Layer for DD version = " + ids_dd_version + ".")

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
                      f"{imas_dd_version}")
                dag = QVizDataAccessCodeGenerator. \
                    QVizDataAccessCodeGenerator(imas_dd_version,
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
                      f"{imas_dd_version}")
                dag = QVizDataAccessCodeGenerator. \
                    QVizDataAccessCodeGenerator(imas_dd_version,
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
