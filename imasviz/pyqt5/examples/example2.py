#!/usr/bin/python
"""This example demonstrates the procedure of plotting multiple data to one
plot.
"""
from imasviz.Browser_API import Browser_API
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)

GlobalOperations.checkEnvSettings()

api = Browser_API()

dataSourceFactory = DataSourceFactory()

f1 = api.CreateDataTree(dataSourceFactory.create(52344, runNumber = 0, userName = 'g2penkod', imasDbName = 'test'))

# f2 = api.CreateDataTree(dataSourceFactory.create(52682, 0, 'g2penkod', 'test'))

paths = []

for i in range(0,2):
    paths.append('magnetics/flux_loop(' + str(i) + ')/flux/data')

# TODO: fix SelectSignals
# api.SelectSignals(f2, paths)
api.SelectSignals(f1, paths)

# f = [f2,f1]
#api.PlotSelectedSignalsFrom(f)

# f2.show()

f1.show()

sys.exit(app.exec_())