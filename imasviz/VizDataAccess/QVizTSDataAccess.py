
import numpy as np


class QVizTSDataAccess:
    def __init__(self, dataSource):
        self.conn = dataSource.conn

    def GetSignal(self, treeNode):
        signalName = treeNode.getDataName()
        shotNumber = treeNode.getShotNumber()

        try:
            if signalName is None:
                return
            signalName.strip()
            if signalName.startswith("'") and signalName.endswith("'"):
                signalName = signalName[1:-1]
            signalName.strip()
            expr = 'gettsbase(' + str(shotNumber) + ', "' + signalName + '")'
            # print expr
            r = self.conn.get('execute($)', expr).data()
            # print r
            expr = 'dim_of(gettsbase(' + str(shotNumber) + ', "' + \
                   signalName + '"))'
            # print expr
            t = self.conn.get('execute($)', expr).data()
            # print t

            if len(r.shape) == 1:
                r = np.array([r])

            if len(t.shape) == 1:
                t = np.array([t])

            return (t, r)

        except:
            raise ValueError("Error while getting the shape of signal " +
                             signalName + " - signal not found ?")

    def GetShapeofSignal(self, selectedNodeData, shotNumber):
        try:
            signalName = selectedNodeData['dataName']  # name of the signal
            signalName.strip()
            if signalName.startswith("'") and signalName.endswith("'"):
                signalName = signalName[1:-1]
            signalName.strip()
            expr = 'gettsbase(' + str(shotNumber) + ', "' + signalName + '")'
            r = self.conn.get('execute($)', expr).data()

            expr = 'dim_of(gettsbase(' + str(shotNumber) + ', "' + signalName + '"))'
            # print expr
            t = self.conn.get('execute($)', expr).data()

            if len(r.shape) == 1:
                r = np.array([r])

            if len(t.shape) == 1:
                t = np.array([t])

            return r.shape, t.shape

        except:
            raise ValueError("Error while getting the shape of signal " +
                             signalName + " - signal not found ?")

# if __name__ == "__main__":
#     import os
#     from imasviz.VizDataSource import DataSourceFactory
#     if 'TS_MAPPINGS_DIR' not in os.environ:
#         os.environ['TS_MAPPINGS_DIR'] = "D:/Dev/IDSVisualization/IMAS_VIZ/ts_mapping_files"
#     ts_dsf = DataSourceFactory()
#     ds = ts_dsf.create(name=QVizGlobalValues.TORE_SUPRA, shotNumber=43970)
#     mdsp = QVizTSDataAccess(ds)
#     selectedNodeData = {}
#     selectedNodeData['dataName'] = "GBFT%3"
#     # selectedNodeData['dataName'] = "GTICXS"
#     # selectedNodeData['dimension'] = 2
#     # selectedNodeData['dataName'] = "GBFT%3"
#     print (mdsp.GetShapeofSignal(selectedNodeData, ds.shotNumber))
#     # print mdsp.GetShapeofSignal(selectedNodeData, ds.shotNumber)[0]
#     signal = mdsp.GetSignal(selectedNodeData, ds.shotNumber)


