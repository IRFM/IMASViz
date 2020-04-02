import os

from imasviz.VizUtils import QVizGlobalValues
from imasviz.VizUtils import QVizPreferences

class QVizGeneratedClassFactory:
    def __init__(self, IMASDataSource, view, IDSName, occurrence=0, asynch=True):
        self.IDSName = IDSName
        self.IMASDataSource = IMASDataSource
        self.view = view
        self.occurrence = occurrence
        self.asynch = asynch


    def create(self, progressBar=None):

        XMLParser = None

        imas__dd_version = self.IMASDataSource.data_dictionary_version

        if imas__dd_version is None or imas__dd_version is '':
            imas__dd_version = os.environ['IMAS_VERSION']

        if QVizGlobalValues.TESTING:
            imas__dd_version = QVizGlobalValues.TESTING_IMAS_VERSION

        if QVizPreferences.Ignore_GGD == 0:

            if imas__dd_version == "3.7.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_7_0 \
                    import IDSDef_XMLParser_Full_Generated_3_7_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_7_0(userName=self.IMASDataSource.userName,
                                                               imasDbName=self.IMASDataSource.imasDbName,
                                                               shotNumber=self.IMASDataSource.shotNumber,
                                                               runNumber=self.IMASDataSource.runNumber,
                                                               view=self.view,
                                                               IDSName=self.IDSName,
                                                               occurrence=self.occurrence,
                                                               asynch=self.asynch)
            elif imas__dd_version == "3.9.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_9_0 \
                    import IDSDef_XMLParser_Full_Generated_3_9_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_9_0(userName=self.IMASDataSource.userName,
                                                                     imasDbName=self.IMASDataSource.imasDbName,
                                                                     shotNumber=self.IMASDataSource.shotNumber,
                                                                     runNumber=self.IMASDataSource.runNumber,
                                                                     view=self.view,
                                                                     IDSName=self.IDSName,
                                                                     occurrence=self.occurrence,
                                                                     asynch=self.asynch)
            elif imas__dd_version == "3.9.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_9_1 \
                    import IDSDef_XMLParser_Full_Generated_3_9_1
                XMLParser = IDSDef_XMLParser_Full_Generated_3_9_1(userName=self.IMASDataSource.userName,
                                                                     imasDbName=self.IMASDataSource.imasDbName,
                                                                     shotNumber=self.IMASDataSource.shotNumber,
                                                                     runNumber=self.IMASDataSource.runNumber,
                                                                     view=self.view,
                                                                     IDSName=self.IDSName,
                                                                     occurrence=self.occurrence,
                                                                     asynch=self.asynch)
            elif imas__dd_version == "3.11.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_11_0 \
                    import IDSDef_XMLParser_Full_Generated_3_11_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_11_0(userName=self.IMASDataSource.userName,
                                                                     imasDbName=self.IMASDataSource.imasDbName,
                                                                     shotNumber=self.IMASDataSource.shotNumber,
                                                                     runNumber=self.IMASDataSource.runNumber,
                                                                     view=self.view,
                                                                     IDSName=self.IDSName,
                                                                     occurrence=self.occurrence,
                                                                     asynch=self.asynch)
            elif imas__dd_version == "3.12.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_12_0 \
                    import IDSDef_XMLParser_Full_Generated_3_12_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_12_0(userName=self.IMASDataSource.userName,
                                                                     imasDbName=self.IMASDataSource.imasDbName,
                                                                     shotNumber=self.IMASDataSource.shotNumber,
                                                                     runNumber=self.IMASDataSource.runNumber,
                                                                     view=self.view,
                                                                     IDSName=self.IDSName,
                                                                     occurrence=self.occurrence,
                                                                     asynch=self.asynch)
            elif imas__dd_version == "3.15.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_15_0 \
                    import IDSDef_XMLParser_Full_Generated_3_15_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_15_0(userName=self.IMASDataSource.userName,
                                                                  imasDbName=self.IMASDataSource.imasDbName,
                                                                  shotNumber=self.IMASDataSource.shotNumber,
                                                                  runNumber=self.IMASDataSource.runNumber,
                                                                  view=self.view,
                                                                  IDSName=self.IDSName,
                                                                  occurrence=self.occurrence,
                                                                  asynch=self.asynch)
            elif imas__dd_version == "3.15.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_15_1 \
                    import IDSDef_XMLParser_Full_Generated_3_15_1
                XMLParser = IDSDef_XMLParser_Full_Generated_3_15_1(userName=self.IMASDataSource.userName,
                                                                  imasDbName=self.IMASDataSource.imasDbName,
                                                                  shotNumber=self.IMASDataSource.shotNumber,
                                                                  runNumber=self.IMASDataSource.runNumber,
                                                                  view=self.view,
                                                                  IDSName=self.IDSName,
                                                                  occurrence=self.occurrence,
                                                                  asynch=self.asynch)
            elif imas__dd_version == "3.16.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_16_0 \
                    import IDSDef_XMLParser_Full_Generated_3_16_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_16_0(userName=self.IMASDataSource.userName,
                                                                  imasDbName=self.IMASDataSource.imasDbName,
                                                                  shotNumber=self.IMASDataSource.shotNumber,
                                                                  runNumber=self.IMASDataSource.runNumber,
                                                                  view=self.view,
                                                                  IDSName=self.IDSName,
                                                                  occurrence=self.occurrence,
                                                                  asynch=self.asynch)

            elif imas__dd_version == "3.17.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_17_0 \
                    import IDSDef_XMLParser_Full_Generated_3_17_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_17_0(userName=self.IMASDataSource.userName,
                                                                  imasDbName=self.IMASDataSource.imasDbName,
                                                                  shotNumber=self.IMASDataSource.shotNumber,
                                                                  runNumber=self.IMASDataSource.runNumber,
                                                                  view=self.view,
                                                                  IDSName=self.IDSName,
                                                                  occurrence=self.occurrence,
                                                                  asynch=self.asynch)
            elif imas__dd_version == "3.17.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_17_1 \
                    import IDSDef_XMLParser_Full_Generated_3_17_1
                XMLParser = IDSDef_XMLParser_Full_Generated_3_17_1(userName=self.IMASDataSource.userName,
                                                                  imasDbName=self.IMASDataSource.imasDbName,
                                                                  shotNumber=self.IMASDataSource.shotNumber,
                                                                  runNumber=self.IMASDataSource.runNumber,
                                                                  view=self.view,
                                                                  IDSName=self.IDSName,
                                                                  occurrence=self.occurrence,
                                                                  asynch=self.asynch)
            elif imas__dd_version == "3.17.2":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_17_2 \
                    import IDSDef_XMLParser_Full_Generated_3_17_2
                XMLParser = IDSDef_XMLParser_Full_Generated_3_17_2(userName=self.IMASDataSource.userName,
                                                                  imasDbName=self.IMASDataSource.imasDbName,
                                                                  shotNumber=self.IMASDataSource.shotNumber,
                                                                  runNumber=self.IMASDataSource.runNumber,
                                                                  view=self.view,
                                                                  IDSName=self.IDSName,
                                                                  occurrence=self.occurrence,
                                                                  asynch=self.asynch)
            elif imas__dd_version == "3.18.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_18_0 \
                    import IDSDef_XMLParser_Full_Generated_3_18_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_18_0(userName=self.IMASDataSource.userName,
                                                                  imasDbName=self.IMASDataSource.imasDbName,
                                                                  shotNumber=self.IMASDataSource.shotNumber,
                                                                  runNumber=self.IMASDataSource.runNumber,
                                                                  view=self.view,
                                                                  IDSName=self.IDSName,
                                                                  occurrence=self.occurrence,
                                                                  asynch=self.asynch)
            elif imas__dd_version == "3.19.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_19_0 \
                    import IDSDef_XMLParser_Full_Generated_3_19_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_19_0(userName=self.IMASDataSource.userName,
                                                                  imasDbName=self.IMASDataSource.imasDbName,
                                                                  shotNumber=self.IMASDataSource.shotNumber,
                                                                  runNumber=self.IMASDataSource.runNumber,
                                                                  view=self.view,
                                                                  IDSName=self.IDSName,
                                                                  occurrence=self.occurrence,
                                                                  asynch=self.asynch)
            elif imas__dd_version == "3.19.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_19_1 \
                    import IDSDef_XMLParser_Full_Generated_3_19_1
                XMLParser = IDSDef_XMLParser_Full_Generated_3_19_1(userName=self.IMASDataSource.userName,
                                                                  imasDbName=self.IMASDataSource.imasDbName,
                                                                  shotNumber=self.IMASDataSource.shotNumber,
                                                                  runNumber=self.IMASDataSource.runNumber,
                                                                  view=self.view,
                                                                  IDSName=self.IDSName,
                                                                  occurrence=self.occurrence,
                                                                  asynch=self.asynch)
            elif imas__dd_version == "3.20.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_20_0 \
                    import IDSDef_XMLParser_Full_Generated_3_20_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_20_0(userName=self.IMASDataSource.userName,
                                                                  imasDbName=self.IMASDataSource.imasDbName,
                                                                  shotNumber=self.IMASDataSource.shotNumber,
                                                                  runNumber=self.IMASDataSource.runNumber,
                                                                  view=self.view,
                                                                  IDSName=self.IDSName,
                                                                  occurrence=self.occurrence,
                                                                  asynch=self.asynch)
            elif imas__dd_version == "3.21.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_21_0 \
                    import IDSDef_XMLParser_Full_Generated_3_21_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_21_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.21.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_21_1 \
                    import IDSDef_XMLParser_Full_Generated_3_21_1
                XMLParser = IDSDef_XMLParser_Full_Generated_3_21_1(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.22.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_22_0 \
                    import IDSDef_XMLParser_Full_Generated_3_22_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_22_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.23.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_23_1 \
                    import IDSDef_XMLParser_Full_Generated_3_23_1
                XMLParser = IDSDef_XMLParser_Full_Generated_3_23_1(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)

            elif imas__dd_version == "3.23.2":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_23_2 \
                    import IDSDef_XMLParser_Full_Generated_3_23_2
                XMLParser = IDSDef_XMLParser_Full_Generated_3_23_2(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)

            elif imas__dd_version == "3.23.3":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_23_3 \
                    import IDSDef_XMLParser_Full_Generated_3_23_3
                XMLParser = IDSDef_XMLParser_Full_Generated_3_23_3(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)

            elif imas__dd_version == "3.24.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_24_0 \
                    import IDSDef_XMLParser_Full_Generated_3_24_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_24_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)

            elif imas__dd_version == "3.25.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_25_0 \
                    import IDSDef_XMLParser_Full_Generated_3_25_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_25_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)

            elif imas__dd_version == "3.26.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_26_0 \
                    import IDSDef_XMLParser_Full_Generated_3_26_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_26_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.27.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Full_Generated_3_27_0 \
                    import IDSDef_XMLParser_Full_Generated_3_27_0
                XMLParser = IDSDef_XMLParser_Full_Generated_3_27_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            else:
                raise ValueError("IMAS dictionary version not supported:" + imas__dd_version)

        else:

            if imas__dd_version == "3.7.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_7_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_7_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_7_0(userName=self.IMASDataSource.userName,
                                                                     imasDbName=self.IMASDataSource.imasDbName,
                                                                     shotNumber=self.IMASDataSource.shotNumber,
                                                                     runNumber=self.IMASDataSource.runNumber,
                                                                     view=self.view,
                                                                     IDSName=self.IDSName,
                                                                     occurrence=self.occurrence,
                                                                     asynch=self.asynch)
            elif imas__dd_version == "3.9.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_9_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_9_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_9_0(userName=self.IMASDataSource.userName,
                                                                     imasDbName=self.IMASDataSource.imasDbName,
                                                                     shotNumber=self.IMASDataSource.shotNumber,
                                                                     runNumber=self.IMASDataSource.runNumber,
                                                                     view=self.view,
                                                                     IDSName=self.IDSName,
                                                                     occurrence=self.occurrence,
                                                                     asynch=self.asynch)
            elif imas__dd_version == "3.9.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_9_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_9_1
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_9_1(userName=self.IMASDataSource.userName,
                                                                     imasDbName=self.IMASDataSource.imasDbName,
                                                                     shotNumber=self.IMASDataSource.shotNumber,
                                                                     runNumber=self.IMASDataSource.runNumber,
                                                                     view=self.view,
                                                                     IDSName=self.IDSName,
                                                                     occurrence=self.occurrence,
                                                                     asynch=self.asynch)
            elif imas__dd_version == "3.11.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_11_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_11_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_11_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.12.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_12_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_12_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_12_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.15.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_15_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_15_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_15_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.15.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_15_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_15_1
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_15_1(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.16.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_16_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_16_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_16_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)

            elif imas__dd_version == "3.17.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_17_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_17_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_17_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.17.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_17_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_17_1
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_17_1(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.17.2":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_17_2 \
                    import IDSDef_XMLParser_Partial_Generated_3_17_2
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_17_2(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.18.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_18_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_18_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_18_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.19.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_19_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_19_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_19_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.19.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_19_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_19_1
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_19_1(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.20.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_20_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_20_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_20_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.21.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_21_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_21_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_21_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.21.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_21_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_21_1
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_21_1(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.22.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_22_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_22_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_22_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.23.1":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_23_1 \
                    import IDSDef_XMLParser_Partial_Generated_3_23_1
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_23_1(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)

            elif imas__dd_version == "3.23.2":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_23_2 \
                    import IDSDef_XMLParser_Partial_Generated_3_23_2
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_23_2(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)

            elif imas__dd_version == "3.23.3":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_23_3 \
                    import IDSDef_XMLParser_Partial_Generated_3_23_3
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_23_3(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)

            elif imas__dd_version == "3.24.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_24_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_24_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_24_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)

            elif imas__dd_version == "3.25.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_25_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_25_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_25_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.26.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_26_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_26_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_26_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            elif imas__dd_version == "3.27.0":
                from imasviz.VizDataAccess.VizGeneratedCode.IDSDef_XMLParser_Partial_Generated_3_27_0 \
                    import IDSDef_XMLParser_Partial_Generated_3_27_0
                XMLParser = IDSDef_XMLParser_Partial_Generated_3_27_0(userName=self.IMASDataSource.userName,
                                                                      imasDbName=self.IMASDataSource.imasDbName,
                                                                      shotNumber=self.IMASDataSource.shotNumber,
                                                                      runNumber=self.IMASDataSource.runNumber,
                                                                      view=self.view,
                                                                      IDSName=self.IDSName,
                                                                      occurrence=self.occurrence,
                                                                      asynch=self.asynch)
            else:
                raise ValueError("IMAS dictionary version not supported:" + imas__dd_version)

        XMLParser.setProgressBar(progressBar)

        return XMLParser
