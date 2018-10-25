# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
# If you need to restart vim tabs then :retab

import getpass
import os
import sys
from PyQt5.QtWidgets import QApplication

#if (__name__ == '__main__'):
sys.path.append(os.getcwd())
app = QApplication(sys.argv)
dictDataSource = {'time_i': 31.880, \
                  'time_e': 32.020, \
                  'delta_t': 0.02, \
                  'shot': 50642, \
                  'run': 0, \
                  'machine': 'west_equinox', \
                  'user': 'imas_private'}
mod = __import__('equilibriumcharts', fromlist=['equilibriumcharts'])
importedClass = getattr(mod, 'equilibriumcharts')
#importedClass = my_import('imas_viz_plugins.equilibriumcharts.equilibriumcharts')
pluginEquiPlot = importedClass()
pluginEquiPlot.execute(app, dictDataSource)
#app.frame = PlotFrame(dictDataSource)
#app.frame.Show()
#app.MainLoop()
