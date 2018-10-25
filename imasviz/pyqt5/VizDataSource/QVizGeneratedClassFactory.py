import os

from imasviz.util.GlobalOperations import GlobalValues


class GeneratedClassFactory:
    def __init__(self, IMASDataSource, view, occurrence=0, pathsList = None, async = True):
        self.IMASDataSource = IMASDataSource
        self.view = view
        self.occurrence = occurrence
        self.pathsList = pathsList
        self.async = async

    def create(self):
        generatedDataTree = None

        imas__dd_version = os.environ['IMAS_VERSION']
        if GlobalValues.TESTING:
            imas__dd_version = GlobalValues.TESTING_IMAS_VERSION

        if imas__dd_version == "3.7.0":
            from imasviz.pyqt5.VizDataAccess.generator.ETNativeDataTree_Generated_3_7_0 \
                import ETNativeDataTree_Generated_3_7_0
            generatedDataTree = ETNativeDataTree_Generated_3_7_0(userName=self.IMASDataSource.userName,
                                                           imasDbName=self.IMASDataSource.imasDbName,
                                                           shotNumber=self.IMASDataSource.shotNumber,
                                                           runNumber=self.IMASDataSource.runNumber,
                                                           view=self.view,
                                                           occurrence=self.occurrence,
                                                           pathsList = self.pathsList,
                                                           async=self.async)
        elif imas__dd_version == "3.9.0":
            from imasviz.pyqt5.VizDataAccess \
                import ETNativeDataTree_Generated_3_9_0
            generatedDataTree = ETNativeDataTree_Generated_3_9_0(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.9.1":
            from imasviz.pyqt5.VizDataAccess \
                import ETNativeDataTree_Generated_3_9_1
            generatedDataTree = ETNativeDataTree_Generated_3_9_1(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.11.0":
            from imasviz.pyqt5.VizDataAccess.generator.ETNativeDataTree_Generated_3_11_0 \
                import ETNativeDataTree_Generated_3_11_0
            generatedDataTree = ETNativeDataTree_Generated_3_11_0(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.12.0":
            from imasviz.pyqt5.VizDataAccess.generator.ETNativeDataTree_Generated_3_12_0 \
                import ETNativeDataTree_Generated_3_12_0
            generatedDataTree = ETNativeDataTree_Generated_3_12_0(userName=self.IMASDataSource.userName,
                                                                 imasDbName=self.IMASDataSource.imasDbName,
                                                                 shotNumber=self.IMASDataSource.shotNumber,
                                                                 runNumber=self.IMASDataSource.runNumber,
                                                                 view=self.view,
                                                                 occurrence=self.occurrence,
                                                                 pathsList=self.pathsList,
                                                                 async=self.async)
        elif imas__dd_version == "3.15.0":
            from imasviz.pyqt5.VizDataAccess \
                import ETNativeDataTree_Generated_3_15_0
            generatedDataTree = ETNativeDataTree_Generated_3_15_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.15.1":
            from imasviz.pyqt5.VizDataAccess.generator.ETNativeDataTree_Generated_3_15_1 \
                import ETNativeDataTree_Generated_3_15_1
            generatedDataTree = ETNativeDataTree_Generated_3_15_1(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.16.0":
            from imasviz.pyqt5.VizDataAccess.generator.ETNativeDataTree_Generated_3_16_0 \
                import ETNativeDataTree_Generated_3_16_0
            generatedDataTree = ETNativeDataTree_Generated_3_16_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)

        elif imas__dd_version == "3.17.0":
            from imasviz.pyqt5.VizDataAccess.generator.ETNativeDataTree_Generated_3_17_0 \
                import ETNativeDataTree_Generated_3_17_0
            generatedDataTree = ETNativeDataTree_Generated_3_17_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.17.1":
            from imasviz.pyqt5.VizDataAccess.generator.ETNativeDataTree_Generated_3_17_1 \
                import ETNativeDataTree_Generated_3_17_1
            generatedDataTree = ETNativeDataTree_Generated_3_17_1(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.17.2":
            from imasviz.pyqt5.VizDataAccess \
                import ETNativeDataTree_Generated_3_17_2
            generatedDataTree = ETNativeDataTree_Generated_3_17_2(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.18.0":
            from imasviz.pyqt5.VizDataAccess.generator.ETNativeDataTree_Generated_3_18_0 \
                import ETNativeDataTree_Generated_3_18_0
            generatedDataTree = ETNativeDataTree_Generated_3_18_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.19.1":
            from imasviz.pyqt5.VizDataAccess.generator.ETNativeDataTree_Generated_3_19_1 \
                import ETNativeDataTree_Generated_3_19_1
            generatedDataTree = ETNativeDataTree_Generated_3_19_1(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        elif imas__dd_version == "3.20.0":
            from imasviz.pyqt5.VizDataAccess.generator.ETNativeDataTree_Generated_3_20_0 \
                import ETNativeDataTree_Generated_3_20_0
            generatedDataTree = ETNativeDataTree_Generated_3_20_0(userName=self.IMASDataSource.userName,
                                                              imasDbName=self.IMASDataSource.imasDbName,
                                                              shotNumber=self.IMASDataSource.shotNumber,
                                                              runNumber=self.IMASDataSource.runNumber,
                                                              view=self.view,
                                                              occurrence=self.occurrence,
                                                              pathsList=self.pathsList,
                                                              async=self.async)
        else:
            raise ValueError("IMAS dictionary version not supported")

        return generatedDataTree