# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The "Save Plot Configuration" button of a Table Plot View.

The window says what it holds -- which quantity each panel answers for, where
that panel sits in the table, and along which abscissa the window was drawn --
and the file gets those three things. Nothing is taken from the pyqtgraph
objects inside the panels: the command that used to write this file read 23 keys
out of ``PlotDataItem.opts`` by name, and this pyqtgraph does not have them all.
Measured on the window this command replaces: the button raised ``KeyError:
'name'`` and left no file on disk, and with that key supplied by hand it raised
``AttributeError: 'tuple' object has no attribute 'brush'`` a few lines later --
on a window of two panels, and on one holding a curve of 1642 points. A window
whose first panel carried no signal data was worse: the loop stopped there and
the file was written with 0 quantities in it, 363 bytes naming nothing.

The name comes from the dialog the manual shows, and a caller may pass one
instead -- the dialog is modal, and what matters here is the file it leads to.
"""

import logging
import os
import time

from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
    QVizConfigurationFile, QVizQuantity, PLOT
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizUtils import QVizGlobalOperations


class QVizSavePlotConfiguration(QVizAbstractCommand):
    """Write this window out as a '.pcfg' that can be applied again."""

    def __init__(self, dataTreeView, figure, name=None):
        """
        Arguments:
            figure (QVizTablePlot) : the window to save.
            name      (str)        : the configuration name; when it is left
                                     out, the user is asked, as the manual says.
        """
        QVizAbstractCommand.__init__(self, dataTreeView)
        self.figure = figure
        self.name = name

    def execute(self):
        """Write the file. Returns its path, or None when the user backed out."""
        name = self.name if self.name is not None else self.askForName()
        if name is None:
            return None

        configuration = QVizConfigurationFile(kind=PLOT,
                                              quantities=self.quantities(),
                                              abscissa=self.figure.getPlotAxis())
        path = QVizConfigurationFile.named(name, PLOT)
        configuration.write(path)
        logging.getLogger(self.dataTreeView.uri).info(
            'Plot configuration "%s" written: %d panel(s). '
            'Applying it selects those quantities and lays the panels where '
            'they were; how the panels looked is not in the file, because the '
            'panels are drawn from the data.'
            % (os.path.basename(path), len(configuration.quantities)))
        return path

    def askForName(self):
        """The dialog the manual shows; None when the user cancels."""
        default = 'plotConfig-' + time.strftime('%d-%m-%Y')
        message = 'Type the name of the plot configuration. \nNote. If left ' \
                  'empty the default name \n' + default + '\nwill be used.'
        name, ok = QVizGlobalOperations.askWithCancel(
            parent=self.figure, title='Save plot configuration',
            message=message, default_value=default)
        return None if not ok else name

    def quantities(self):
        """[QVizQuantity] -- one per panel, with the place that panel holds."""
        uri = self.dataTreeView.dataSource.uri
        return [QVizQuantity(path=panel.treeNode.getPath(),
                             occurrence=panel.treeNode.getOccurrence(),
                             row=row, column=column, uri=uri)
                for row, column, panel in self.figure.panelsInTable()]
