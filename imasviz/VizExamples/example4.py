#!/usr/bin/python
import os
import sys

from PyQt5.QtWidgets import QApplication
from imasviz.util.GlobalOperations import GlobalOperations

from imasviz.Browser_API import Browser_API
from imasviz.VizDataSource import DataSourceFactory
from imasviz.VizUtils.GlobalValues import GlobalValues

app = QApplication(sys.argv)
GlobalOperations.checkEnvSettings()

api = Browser_API()

dataSourceFactory = DataSourceFactory()
userName = os.environ['USER']
dataSource = dataSourceFactory.create(dataSourceName=GlobalValues.IMAS_NATIVE, shotNumber=52344, runNumber=0,userName='imas_public',imasDbName='west')

f = api.CreateDataTree(dataSource)
configFileName = os.environ['HOME'] + "/.imasviz/magnetics1.pcfg"
figurekey =api.GetNextKeyForMultiplePlots()

#api.ApplyMultiPlotConfiguration(f, figureKey=figurekey, update=0, configFileName=configFileName)

app.exec()
