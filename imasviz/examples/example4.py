#!/usr/bin/python

import wx
import os
from imasviz.Browser_API import Browser_API
from imasviz.data_source.QVizDataSourceFactory import DataSourceFactory
#from imasviz.gui_commands.configurations.ApplyPlotConfiguration import ApplyPlotConfiguration
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues

app = wx.App()

GlobalOperations.checkEnvSettings()

api = Browser_API()

dataSourceFactory = DataSourceFactory()
userName = os.environ['USER']
dataSource = dataSourceFactory.create(dataSourceName=GlobalValues.IMAS_NATIVE, shotNumber=52344, runNumber=0,userName='imas_public',imasDbName='west')

f = api.CreateDataTree(dataSource)
configFileName = os.environ['HOME'] + "/.imasviz/magnetics1.pcfg"
figurekey =api.GetNextKeyForMultiplePlots()

api.ApplyMultiPlotConfiguration(f, figureKey=figurekey, update=0, configFileName=configFileName)

app.MainLoop()
