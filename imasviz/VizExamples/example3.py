#!/usr/bin/python

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
dataSource = dataSourceFactory.create(dataSourceName=QVizGlobalValues.IMAS_NATIVE, shotNumber=52682, runNumber=0, userName='imas_public', imasDbName='west')

f = api.CreateDataTree(dataSource)
paths = []

for i in range(0,6):
    paths.append('magnetics/flux_loop(' + str(i) + ')/flux')

api.SelectSignals(f, paths)
#api.PlotSelectedSignalsInTablePlotViewFrame(f)
api.ShowDataTree(f)

app.exec()
