#!/usr/bin/python
from imasviz.Browser_API import Browser_API
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
import wx

app = wx.App()

GlobalOperations.checkEnvSettings()

api = Browser_API()

dataSourceFactory = DataSourceFactory()

f1 = api.CreateDataTree(dataSourceFactory.create(name=GlobalValues.TORE_SUPRA, shotNumber=47977))
f2 = api.CreateDataTree(dataSourceFactory.create(name=GlobalValues.TORE_SUPRA, shotNumber=47978))
f3 = api.CreateDataTree(dataSourceFactory.create(name=GlobalValues.TORE_SUPRA, shotNumber=47979))

paths = []

for i in range(1,2):
    paths.append('magnetics/flux_loop(' + str(i) + ')/flux')

api.SelectSignals(f1, paths)
api.SelectSignals(f2, paths)
api.SelectSignals(f3, paths)

f = [f1,f2,f3]
api.PlotSelectedSignalsFrom(f)

f1.Show()
f2.Show()
f3.Show()

app.MainLoop()