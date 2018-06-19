#!/usr/bin/python

from imasviz.Browser_API import Browser_API
from imasviz.data_source.DataSourceFactory import DataSourceFactory
import wx
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.gui_commands.select_commands.SelectSignalsGroup import SelectSignalsGroup

app = wx.App()
GlobalOperations.checkEnvSettings()
api = Browser_API()
dataSource = DataSourceFactory().create(dataSourceName=GlobalValues.IMAS_NATIVE, shotNumber=52702, runNumber=0,userName='imas_public',imasDbName='west')

f = api.CreateDataTree(dataSource)
#api.SelectSignals(f, paths)
#nodeData = f.wxTreeView.GetItemData(f.wxTreeView.selectedItem)
#selectCommand = SelectSignalsGroup(f.wxTreeView, nodeData)
#selectCommand.execute()
occurrence = 0
api.SelectSignalsGroup(f, occurrence, 'magnetics/flux_loop(0)/flux/data')
api.ShowDataTree(f)

app.MainLoop()
