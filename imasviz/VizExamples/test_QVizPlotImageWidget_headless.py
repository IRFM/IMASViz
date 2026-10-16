# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

#!/usr/bin/python
"""Headless regression test of QvizPlotImageWidget, drivable without an IMAS case.

Unlike the other files of this directory it asks nothing from the GUI (no
QVizGlobalOperations.askForShot, which is a QInputDialog) and it never calls
app.exec_(), so it terminates by itself and reports its outcome through its
exit code: 0 when the image plot is built as expected, non-zero otherwise.

Run it from the repository root after loading the modules:

    export VIZ_PRODUCTION=1 VIZ_HOME=$PWD IMAS_VIZ_VERSION=2.3.7 UDA_DISABLED=1
    python3 imasviz/VizExamples/test_QVizPlotImageWidget_headless.py
"""

import os
import sys

# The package lives under $VIZ_HOME, which the interpreter does not know about
# unless it is exported through PYTHONPATH.
vizHome = os.environ.get('VIZ_HOME', '')
if vizHome and vizHome not in sys.path:
    sys.path.insert(0, vizHome)

import numpy as np
from PySide6.QtWidgets import QApplication

from imasviz.VizEntities.QVizDataArrayHandle import QVizDataArrayHandle, ArrayCoordinates
from imasviz.VizGUI.VizPlot.VizPlotFrames.QvizPlotImageWidget import QvizPlotImageWidget
from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues

# QApplication parses '-platform offscreen' from argv, which lets the test run
# where there is no X display. It must be set before QApplication is built.
sys.argv = ['test_QVizPlotImageWidget_headless.py', '-platform', 'offscreen']

mandatoryVariables = ['HOME', 'USER', 'VIZ_HOME', 'TS_MAPPINGS_DIR',
                      'IMAS_VERSION', 'IMAS_DATA_DICTIONARIES_DIR',
                      'IMAS_MAJOR_VERSION']

failures = []


def check(condition, message):
    if not condition:
        failures.append(message)
        return False
    return True


def main():
    # A broken configuration must not pass silently: QVizGlobalOperations.check
    # exits with code 0 when a mandatory variable is missing.
    missing = [name for name in mandatoryVariables if name not in os.environ]
    if missing:
        print("FAIL: mandatory environment variables not set: " + ", ".join(missing))
        return 1

    QVizGlobalOperations.checkEnvSettings()

    # Synthetic 2D array: no IMAS case, no data dictionary needed.
    coordinatesPath = ['path.x', 'path.y']
    coordinatesValues = [np.linspace(0, 100., num=100), np.linspace(10., 33., num=200)]
    coordinatesLabels = ['x_label', 'y_label']
    timeCoordinateDim = 2
    arrayCoordinates = ArrayCoordinates(coordinatesPath, coordinatesValues,
                                        timeCoordinateDim, coordinatesLabels)

    sinX = np.sin(coordinatesValues[0] / 50)
    cosY = np.cos(coordinatesValues[1] / 20)
    arrayValues = np.zeros((100, 200))
    for i in range(0, 100):
        arrayValues[i, :] = sinX[i] * cosY

    dataArrayHandle = QVizDataArrayHandle(arrayCoordinates, arrayValues,
                                          'test', 'label of the test')

    # vizTreeNode may be None: QvizPlotImageWidget.plot only calls
    # viewBox.addVizTreeNode when it is not.
    plotWidget = QvizPlotImageWidget(vizTreeNode=None, plotSliceFromROI=True,
                                     showImageTitle=False)

    plotWidget.plot(dataArrayHandle)

    check(plotWidget.dataArrayHandle is not None, 'plot() did not keep the data array handle')
    check(plotWidget.plotImageItem is not None, 'plot() did not create plotImageItem')
    check(plotWidget.slicesXPlotItem is not None,
          'plotSliceFromROI=True did not create slicesXPlotItem')
    check(plotWidget.slicesYPlotItem is not None,
          'plotSliceFromROI=True did not create slicesYPlotItem')

    plottedItems = plotWidget.plotImageItem.listDataItems()
    check(len(plottedItems) == 1, 'expected exactly one plotted item, got '
          + str(len(plottedItems)))

    check(plotWidget.dataArrayHandle is dataArrayHandle,
          'plot() did not keep the array handle it was given')
    check(plotWidget.dataArrayHandle.getTimeCoordinateDim() == timeCoordinateDim,
          'time coordinate dimension not preserved')
    check(np.shape(plotWidget.dataArrayHandle.arrayValues) == np.shape(arrayValues),
          'array values shape not preserved: '
          + str(np.shape(plotWidget.dataArrayHandle.arrayValues)) + ' vs '
          + str(np.shape(arrayValues)))

    return 0 if not failures else 1


if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)
    status = main()
    if failures:
        print("FAIL:")
        for message in failures:
            print("  " + message)
    else:
        print("OK: QvizPlotImageWidget built an image plot from a synthetic array")
    sys.exit(status)
