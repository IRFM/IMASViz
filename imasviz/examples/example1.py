#!/usr/bin/python

from imasviz.Browser_API import Browser_API
from imasviz.data_source.DataSourceFactory import DataSourceFactory
import wx
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations

app = wx.App()

GlobalOperations.checkEnvSettings()

api = Browser_API()

dataSourceFactory = DataSourceFactory()
dataSource = dataSourceFactory.create(name=GlobalValues.IMAS_NATIVE, shotNumber=10, runNumber=60,userName='LF218007',imasDbName='test')

f = api.CreateDataTree(dataSource)
paths = []

for i in range(0,6):
    paths.append('core_profiles/profiles_1d(' + str(i) + ')/pressure_ion_total')

api.SelectSignals(f, paths)

api.PlotSelectedSignals(f)

#api.ShowDataTree(f)

app.MainLoop()
