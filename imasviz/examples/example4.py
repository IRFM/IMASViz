#!/usr/bin/python

import wx
import os
from imasviz.Browser_API import Browser_API
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.gui_commands.plots_configuration.ApplyPlotConfiguration import ApplyPlotConfiguration
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues
import xml.etree.ElementTree as ET

app = wx.App()

GlobalOperations.checkEnvSettings()

api = Browser_API()

dataSourceFactory = DataSourceFactory()
dataSource = dataSourceFactory.create(name=GlobalValues.IMAS_NATIVE, shotNumber=10, runNumber=60,userName='LF218007',imasDbName='test')

f = api.CreateDataTree(dataSource)
paths = []

for i in range(0,6):
    paths.append('core_profiles/profiles_1d(' + str(i) + ')/pressure_ion_total')

#api.SelectSignals(f, paths)

#api.PlotSelectedSignalsInMultiFrame(f)

#api.ShowDataTree(f)
configFileName = os.environ['HOME'] + "/viz/myconfig.cfg"
config = ET.parse(configFileName)

t = ApplyPlotConfiguration(f, paths, config)
t.execute()

app.MainLoop()
