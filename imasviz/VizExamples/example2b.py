#!/usr/bin/python
"""This example demonstrates the procedure of plotting multiple data to one
plot.
"""

import sys

from PyQt5.QtWidgets import QApplication
from imasviz.util.GlobalOperations import GlobalOperations

from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource import DataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues

app = QApplication(sys.argv)

GlobalOperations.checkEnvSettings()

api = Viz_API()

dataSourceFactory = DataSourceFactory()

f = []
n_shot = [52702, 52703]

for i in range(0, 2):
    dataSource = dataSourceFactory.create(dataSourceName=QVizGlobalValues.IMAS_NATIVE, shotNumber=n_shot[i], runNumber=0,
                                          userName='imas_public', imasDbName='west')
    f.append(api.CreateDataTree(dataSource))

paths1 = []
for i in range(1, 3):
    paths1.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

paths2 = []
for i in range(1, 3):
    paths2.append('magnetics/bpol_probe(' + str(i) + ')/field/data')

api.SelectSignals(f[0], paths1)
api.SelectSignals(f[1], paths2)
api.PlotSelectedSignalsFrom(f)

f[0].show()
f[1].show()
app.exec()