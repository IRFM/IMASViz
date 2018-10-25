#!/usr/bin/python

import sys

from PyQt5.QtWidgets import QApplication
from imasviz.VizUtils.GlobalOperations import GlobalOperations

from imasviz.Browser_API import Browser_API
from imasviz.VizDataSource.QVizDataSourceFactory import DataSourceFactory
from imasviz.VizUtils.GlobalValues import GlobalValues

app = QApplication(sys.argv)

GlobalOperations.checkEnvSettings()

api = Browser_API()

dataSourceFactory = DataSourceFactory()
dataSource = dataSourceFactory.create(dataSourceName=GlobalValues.IMAS_NATIVE, shotNumber=52702, runNumber=0,userName='imas_public',imasDbName='west')

f = api.CreateDataTree(dataSource)
paths = []

for i in range(0,6):
    paths.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

api.SelectSignals(f, paths)

api.PlotSelectedSignals(f)

app.exec()
