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
                 viewLoadingStrategy=None, asynch=True):
        self.IDSName = IDSName
        self.IMASDataSource = IMASDataSource
        self.view = view
        self.occurrence = occurrence
        self.viewLoadingStrategy = None
        from imasviz.VizGUI.VizTreeView.QVizViewLoadingStrategy import QVizViewLoadingStrategy
        if viewLoadingStrategy is None:
            viewLoadingStrategy = QVizViewLoadingStrategy.getDefaultStrategy()
        self.viewLoadingStrategy = viewLoadingStrategy
        self.asynch = asynch

    def create(self, progressBar=None):
        dd_version = os.environ['IMAS_VERSION']
        ids_dd_version = self.IMASDataSource.data_dictionary_version

        if (ids_dd_version is not None and ids_dd_version != '') and ids_dd_version < '3.26.0':
            if dd_version > ids_dd_version:
                logging.getLogger(self.view.uri).warning("Non backward compatible change infos are not available for"
                                " IDSs created with DD version prior to 3.26.0. You should use"
                                " an older version of IMAS Access Layer to access data for DD "
                                "fields that have been renamed. If it is the case, quit IMASViz and load an older "
                                "IMAS Access Layer for DD version = " + ids_dd_version + ".")

        if QVizGlobalValues.TESTING:
            dd_version = QVizGlobalValues.TESTING_IMAS_VERSION

        generated_code_folder = os.environ['HOME'] + "/.imasviz/VizGeneratedCode/"

        if QVizPreferences.Ignore_GGD == 0:

            className = "IDSDef_XMLParser_Full_Generated_" + \
                        QVizGlobalOperations.replaceDotsByUnderScores(dd_version)

            className = QVizGlobalOperations.replaceDashesByUnderScores(className)

            path_user_gencode = os.environ['HOME'] + "/.imasviz/VizGeneratedCode/"
            if not os.path.exists(path_user_gencode):
                os.makedirs(path_user_gencode)


            IDSDef_parser_path = generated_code_folder + className + ".py"
            #print("IDSDef parser path: ", IDSDef_parser_path)
            self.removeParserIfTooOld(IDSDef_parser_path)

            if not os.path.exists(IDSDef_parser_path):
                print("Generating full parsers for IMAS "
                      f"{dd_version}")
                QVizDataAccessCodeGenerator. \
                    QVizDataAccessCodeGenerator(dd_version)
                print("End of code generation")

            moduleName = className


            IDSDef_XMLParser_Full_Generated = \
                getattr(importlib.import_module(moduleName), className)

            # raise ValueError("IMAS dictionary version not supported:" + dd_version)
            XMLParser = IDSDef_XMLParser_Full_Generated(
                uri=self.IMASDataSource.uri,
                view=self.view,
                IDSName=self.IDSName,
                occurrence=self.occurrence,
                viewLoadingStrategy=self.viewLoadingStrategy,
                asynch=self.asynch)

        else:  # If QVizPreferences.Ignore_GGD == 1
            className = "IDSDef_XMLParser_Partial_Generated_" + \
                        QVizGlobalOperations.replaceDotsByUnderScores(dd_version)

            className = QVizGlobalOperations.replaceDashesByUnderScores(className)

            path_user_gencode = os.environ['HOME'] + "/.imasviz/VizGeneratedCode/"
            if not os.path.exists(path_user_gencode):
                os.makedirs(path_user_gencode)

            IDSDef_parser_path = generated_code_folder + className + ".py"
            #print("IDSDef parser path: ", IDSDef_parser_path)
            self.removeParserIfTooOld(IDSDef_parser_path)

            if not os.path.exists(IDSDef_parser_path):
                print("Generating partial parsers for IMAS "
                      f"{dd_version}")
                QVizDataAccessCodeGenerator. \
                    QVizDataAccessCodeGenerator(dd_version)
                print("End of code generation")

            moduleName = className

            IDSDef_XMLParser_Partial_Generated = \
                getattr(importlib.import_module(moduleName), className)

            XMLParser = IDSDef_XMLParser_Partial_Generated(
                uri=self.IMASDataSource.uri,
                view=self.view,
                IDSName=self.IDSName,
                occurrence=self.occurrence,
                viewLoadingStrategy=self.viewLoadingStrategy,
                asynch=self.asynch)

        XMLParser.setProgressBar(progressBar)

        return XMLParser

    def removeParserIfTooOld(self, IDSDef_parser_path):
        from datetime import datetime
        dt_obj = datetime.strptime('14.12.2023 13:00:00,00',
                                   '%d.%m.%Y %H:%M:%S,%f')
        millisec = dt_obj.timestamp() * 1000
        if os.path.exists(IDSDef_parser_path):
            parser_age = 1000 * os.stat(IDSDef_parser_path).st_mtime
            if parser_age < millisec:
                logging.getLogger(self.view.uri).info("Removing obsolete parser: " + IDSDef_parser_path + ".")
                os.remove(IDSDef_parser_path)
