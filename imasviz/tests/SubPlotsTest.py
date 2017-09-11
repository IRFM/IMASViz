#!/usr/bin/python

from imasviz.Browser_API import Browser_API
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.tests.SubPlotsManagerView import SubPlotsManagerFrame
import os
from imasviz.util.GlobalValues import GlobalValues

api = Browser_API()

dataSourceFactory = DataSourceFactory()
dataSource = dataSourceFactory.create(GlobalValues.TORE_SUPRA, shotNumber=47979)

f = api.CreateDataTree(dataSource)
paths = []

for i in range(1,3):
    paths.append('magnetics/flux_loop(' + str(i) + ')/flux/data')
paths.append('magnetics/bpol_probe(1)/field/data')
paths.append('magnetics/method/ip/data')

api.SelectSignals(f, paths)
# api.PlotSelectedSignals(f)
spm = SubPlotsManagerFrame("Sbm", f)
spm.Show()
# spm.showSubPlots()
# f.Show()