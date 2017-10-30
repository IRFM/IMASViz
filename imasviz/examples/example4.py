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
userName = os.environ['USER']
dataSource = dataSourceFactory.create(shotNumber=10, runNumber=60,userName=userName,imasDbName='test')

f = api.CreateDataTree(dataSource)
paths = []

for i in range(0,6):
    paths.append('core_profiles/profiles_1d(' + str(i) + ')/pressure_ion_total')

api.SelectSignals(f, paths)

#configFileName = os.environ['HOME'] + "/.imasviz/config4.cfg"
configFileName = os.environ['VIZ_HOME'] + "/myconfig.cfg"
config = ET.parse(configFileName)
api.PlotSelectedSignalsInMultiFrame(f, config)

api.ShowDataTree(f)



#v = config.findall(".//*[@key='(1, 1)']/trace")

#print v
#print v[0]
#a=v[0]

#print 'title = ' + a.get('title')

#t = ApplyPlotConfiguration(f, paths, config)
#t.execute()

app.MainLoop()
