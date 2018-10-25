#!/usr/bin/python

import sys

from PyQt5.QtWidgets import QApplication
from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations

from imasviz.Viz_API import Viz_API
from imasviz.VizDataSource.QVizDataSourceFactory import QVizDataSourceFactory
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues

app = QApplication(sys.argv)

QVizGlobalOperations.checkEnvSettings()

api = Viz_API()

dataSourceFactory = QVizDataSourceFactory()
dataSource = dataSourceFactory.create(dataSourceName=QVizGlobalValues.IMAS_NATIVE, shotNumber=52702, runNumber=0, userName='imas_public', imasDbName='west')

f = api.CreateDataTree(dataSource)
paths = []

for i in range(0,6):
    paths.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

api.SelectSignals(f, paths)

api.PlotSelectedSignals(f)

app.exec()
