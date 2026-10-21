# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The "Save Node Selection" entry of the tree browser menu.

The selection is the one record T8 left: ``selectedSignalsDict``, keyed by the
data source and holding the node itself. Writing a configuration reads that
record and names the quantities in the order they were picked -- the order the
manual warns decides the order of the plots. A node the tree dropped after it
was selected is written too: the user selected it, and whether the tree still
lists it is the tree's business, not the file's.
"""

import logging
import os
import time

from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
    QVizConfigurationFile, QVizQuantity, SELECTION
from imasviz.VizGUI.VizGUICommands.QVizAbstractCommand import QVizAbstractCommand
from imasviz.VizUtils import QVizGlobalOperations


class QVizSaveNodeSelection(QVizAbstractCommand):
    """Write the current selection out as an '.lsp' that can be applied again."""

    def __init__(self, dataTreeView, name=None):
        """
        Arguments:
            name (str) : the configuration name; when it is left out, the user
                         is asked, as the manual says.
        """
        QVizAbstractCommand.__init__(self, dataTreeView)
        self.name = name

    def execute(self):
        """Write the file. Returns its path, or None when the user backed out."""
        name = self.name if self.name is not None else self.askForName()
        if name is None:
            return None

        quantities = self.quantities()
        if not quantities:
            raise ValueError('Nothing to save: no node is selected.')

        configuration = QVizConfigurationFile(kind=SELECTION,
                                              quantities=quantities)
        path = QVizConfigurationFile.named(name, SELECTION)
        configuration.write(path)
        logging.getLogger(self.dataTreeView.uri).info(
            'Node selection "%s" written: %d node(s).'
            % (os.path.basename(path), len(quantities)))
        return path

    def askForName(self):
        """The dialog the manual shows; None when the user cancels."""
        default = 'signalSelection-' + time.strftime('%d-%m-%Y')
        message = 'Type the name of the configuration. \nNote. If left empty ' \
                  'the default name \n' + default + '\nwill be used.'
        name, ok = QVizGlobalOperations.askWithCancel(
            parent=self.dataTreeView, title='Save node selection',
            message=message, default_value=default)
        return None if not ok else name

    def quantities(self):
        """[QVizQuantity] for the selected nodes, in the order they came in."""
        entries = self.dataTreeView.selectedSignalsDict.values()
        ordered = sorted(entries, key=lambda entry: entry.get('index', 0))
        return [QVizQuantity(path=entry['QTreeWidgetItem'].getPath(),
                             occurrence=entry['QTreeWidgetItem'].getOccurrence(),
                             row=None, column=None,
                             uri=entry.get('uri', self.dataTreeView.dataSource.uri))
                for entry in ordered]
