import os

from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalValues


class QVizGeneratedClassFactory:
    def __init__(self, IMASDataSource, view, IDSName, occurrence=0, pathsList = None, async = True):
        self.IDSName = IDSName
        self.IMASDataSource = IMASDataSource
        self.view = view
        self.occurrence = occurrence
        self.pathsList = pathsList
        self.async = async


    def create(self):
        generatedDataTree = None

        imas__dd_version = os.environ['IMAS_VERSION']
        if QVizGlobalValues.TESTING:
            imas__dd_version = QVizGlobalValues.TESTING_IMAS_VERSION

        if imas__dd_version == "3.7.0":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_7_0 \
                import IDSDef_XMLParser_Generated_3_7_0
            generatedDataTree = IDSDef_XMLParser_Generated_3_7_0(userName=self.IMASDataSource.userName,
                                                           imasDbName=self.IMASDataSource.imasDbName,
                                                           shotNumber=self.IMASDataSource.shotNumber,
                                                           runNumber=self.IMASDataSource.runNumber,
                                                           view=self.view,
                                                           IDSName=self.IDSName,
                                                           occurrence=self.occurrence,
                                                           pathsList = self.pathsList,
                                                           async=self.async)
        elif imas__dd_version == "3.9.0":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_9_0 \
                import IDSDef_XMLParser_Generated_3_9_0
            generatedDataTree = IDSDef_XMLParser_Generated_3_9_0(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 IDSName=self.IDSName,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.9.1":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_9_1 \
                import IDSDef_XMLParser_Generated_3_9_1
            generatedDataTree = IDSDef_XMLParser_Generated_3_9_1(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 IDSName=self.IDSName,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.11.0":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_11_0 \
                import IDSDef_XMLParser_Generated_3_11_0
            generatedDataTree = IDSDef_XMLParser_Generated_3_11_0(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 IDSName=self.IDSName,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.12.0":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_12_0 \
                import IDSDef_XMLParser_Generated_3_12_0
            generatedDataTree = IDSDef_XMLParser_Generated_3_12_0(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 IDSName=self.IDSName,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.15.0":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_15_0 \
                import IDSDef_XMLParser_Generated_3_15_0
            generatedDataTree = IDSDef_XMLParser_Generated_3_15_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              IDSName=self.IDSName,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.15.1":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_15_1 \
                import IDSDef_XMLParser_Generated_3_15_1
            generatedDataTree = IDSDef_XMLParser_Generated_3_15_1(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              IDSName=self.IDSName,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.16.0":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_16_0 \
                import IDSDef_XMLParser_Generated_3_16_0
            generatedDataTree = IDSDef_XMLParser_Generated_3_16_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              IDSName=self.IDSName,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)

        elif imas__dd_version == "3.17.0":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_17_0 \
                import IDSDef_XMLParser_Generated_3_17_0
            generatedDataTree = IDSDef_XMLParser_Generated_3_17_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              IDSName=self.IDSName,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.17.1":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_17_1 \
                import IDSDef_XMLParser_Generated_3_17_1
            generatedDataTree = IDSDef_XMLParser_Generated_3_17_1(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              IDSName=self.IDSName,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.17.2":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_17_2 \
                import IDSDef_XMLParser_Generated_3_17_2
            generatedDataTree = IDSDef_XMLParser_Generated_3_17_2(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              IDSName=self.IDSName,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.18.0":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_18_0 \
                import IDSDef_XMLParser_Generated_3_18_0
            generatedDataTree = IDSDef_XMLParser_Generated_3_18_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              IDSName=self.IDSName,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.19.1":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_19_1 \
                import IDSDef_XMLParser_Generated_3_19_1
            generatedDataTree = IDSDef_XMLParser_Generated_3_19_1(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              IDSName=self.IDSName,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.20.0":
            from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Generated_3_20_0 \
                import IDSDef_XMLParser_Generated_3_20_0
            generatedDataTree = IDSDef_XMLParser_Generated_3_20_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              IDSName=self.IDSName,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        else:
            raise ValueError("IMAS dictionary version not supported:" + imas__dd_version)

        return generatedDataTree