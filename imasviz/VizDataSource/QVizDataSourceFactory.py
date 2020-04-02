import os
from imasviz.VizDataSource.QVizToreSupraDataSource import ToreSupraDataSource
from imasviz.VizDataSource.QvizIMASPublicDataSource import QVizIMASPublicDataSource

from imasviz.VizDataSource.QVizIMASDataSource import QVizIMASDataSource
from imasviz.VizUtils import QVizGlobalValues


#A factory for creating a Tore-Supra or MDS+ native data-source for IMAS
class QVizDataSourceFactory:

    def __init__(self):
        pass

    def createUDADatasource(self, UDAMachineName, shotNumber, runNumber = 0):
        return self.create(shotNumber, runNumber, None, None,
                           QVizGlobalValues.IMAS_UDA, UDAMachineName)

    def create(self, shotNumber, runNumber = 0, userName = None,
               imasDbName = None, dataSourceName = QVizGlobalValues.IMAS_NATIVE,
               machineName = None):

        #Check UDA prerequisites

        #Check if UDA log directory exists and create it otherwise
        UDALogDir = os.environ['HOME'] + '/logs/uda'
        if not os.path.exists(UDALogDir):
            os.makedirs(UDALogDir)

        if machineName == 'TCV' or machineName == 'AUG':
            exp2imasFile = os.environ['HOME'] + '/.exp2imas'
            if not os.path.exists(exp2imasFile):
                raise ValueError('Access to ' + machineName + ' requires a file named ''.exp2imas''  located in '
                                                              'your home directory containing one line:'
                                 + machineName + ' username password')

        if machineName == 'WEST':
            west_tunnel_file = os.environ['HOME'] + '/.west_tunnel'
            if not os.path.exists(west_tunnel_file):
                raise ValueError('Access to ' + machineName + ' requires a file named ''.west_tunnel''  located in '
                                                              'your home directory containing one line:'
                                 + machineName + ' username password')

        if dataSourceName is None or dataSourceName == '':
            raise ValueError("A datasource name is required for creating a datasource")

        if dataSourceName == QVizGlobalValues.IMAS_NATIVE:
            dataSource = QVizIMASDataSource(dataSourceName, userName, imasDbName,
                                            shotNumber, runNumber)
            return dataSource

        elif dataSourceName == QVizGlobalValues.TORE_SUPRA:
            #raise ValueError("Tore-Supra datasource is not currently available")
            dataSource = ToreSupraDataSource(QVizGlobalValues.TORE_SUPRA,
                                             shotNumber, runNumber)
            return dataSource

        else: # UDA datasource

            if machineName is None or machineName == '':
                raise ValueError("A machine name is required for UDA datasource")

            elif machineName in QVizGlobalValues.ExternalSources:
                #print "Creating QVizIMASPublicDataSource..."
                if machineName == 'WEST': #WORK AROUND of IMAS-2701 issue
                    os.environ['UDA_PLUGIN'] = 'west_tunnel'
                else:
                    os.environ['UDA_PLUGIN'] = 'IMAS_MAPPING'
                dataSource = QVizIMASPublicDataSource(dataSourceName, machineName,
                                                      shotNumber, runNumber)
                return dataSource
            else:
                raise ValueError("UDA public datasource '" + machineName
                    + "' is not supported by UDA")
