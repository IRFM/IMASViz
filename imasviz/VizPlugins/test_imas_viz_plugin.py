# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import getpass
import sys
from PySide6.QtWidgets import QApplication

if (__name__ == '__main__'):
    app = QApplication(sys.argv)
    dictDataSource = {'time_i': 31.880,
                      'time_e': 32.020,
                      'delta_t': 0.02,
                      'shot': 50642,
                      'run': 0,
                      'machine': 'west_equinox',
                      'user': getpass.getuser()}
    mod = __import__('imas_viz_plugins.equilibriumcharts', fromlist=['equilibriumcharts'])
    importedClass = getattr(mod, 'equilibriumcharts')
    #importedClass = my_import('imas_viz_plugins.equilibriumcharts.equilibriumcharts')
    pluginEquiPlot = importedClass()
    pluginEquiPlot.execute(app, dictDataSource)
    #app.frame = PlotFrame(dictDataSource)
    #app.frame.Show()
    #app.MainLoop()
