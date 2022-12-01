#! /usr/bin/env python3

#  Name   :GGDDialog
#
#          Container to create PyQt5 dialog for setting the GGD related
#          variables
#
#  Author :
#         Dejan Penko
#  E-mail :
#         dejan.penko@lecad.fs.uni-lj.si
#

from PySide2.QtWidgets import QLineEdit, QDialog, QFormLayout, QDialogButtonBox, \
                            QComboBox
from PySide2.QtGui import QIntValidator
import logging

from src.getEPGGD import getEPGGD, GetGGDVars

class GetGGDDialog(QDialog):
    """Dialog Demanding the grid_ggd and ggd slice together with grid
    subset and quantity (for edge_profiles IDS).
    """

    def __init__(self, parent=None):
        super(GetGGDDialog, self).__init__(parent)

        # Set IDS object (from parent)
        self.ids = parent.ids

        if self.ids == None:
            return
        # Set empty dictionaries
        self.gridSubsetDict = {}
        self.quantityDict = {}
        # Set edge_profiles object
        self.ep = self.ids.edge_profiles
        self.getGGD = getEPGGD(self.ep)

        # Get GGD properties
        # - Number of GGD slices
        self.nGGDSlices = len(self.ep.ggd)
        # - Number of GGD grid slices
        self.nGridGGDSlices = len(self.ep.grid_ggd)

    def prepareWidgets(self, parameters, title='Specify data to plot'):
        """Set dialog widgets (line edit etc.).

        Arguments:
            title (str) : Dialog title.

        """
        self.setModal(True)
        # Set window title
        self.setWindowTitle(title)
        # Set layout
        formLayout = QFormLayout(self)

        # Set line edit for grid_ggd slice
        self.g1_LineEdit = QLineEdit()
        self.g1_LineEdit.setText(GetGGDVars.names[0])
        self.g1_LineEdit.setText(str(GetGGDVars.defaultValues['gridGGDSlice']))
        self.g1_LineEdit.setValidator(QIntValidator())
        formLayout.addRow(GetGGDVars.names[0], self.g1_LineEdit)

        # Set line edit for ggd slice
        self.g2_LineEdit = QLineEdit()
        self.g2_LineEdit.setText(GetGGDVars.names[1])
        self.g2_LineEdit.setText(str(GetGGDVars.defaultValues['GGDSlice']))
        self.g2_LineEdit.setValidator(QIntValidator())
        formLayout.addRow(GetGGDVars.names[1], self.g2_LineEdit)

        # Set combo boxes
        self.combobox_gridSubset = QComboBox()
        self.combobox_quantity = QComboBox()

        self.populateComboBoxGS()
        self.populateComboBoxQ()

        self.g1_LineEdit.textChanged.connect(self.populateComboBoxGS)

        self.combobox_gridSubset.currentTextChanged.connect(
            self.populateComboBoxQ)

        formLayout.addRow('Grid Subset', self.combobox_gridSubset)
        formLayout.addRow('Grid Subset Quantity', self.combobox_quantity)

        # Adding the Ok and Cancel button.
        dialog_button_box = QDialogButtonBox()
        dialog_button_box.setStandardButtons(QDialogButtonBox.Ok |
                                             QDialogButtonBox.Cancel)
        dialog_button_box.accepted.connect(self.accept)
        dialog_button_box.rejected.connect(self.reject)
        formLayout.addRow(dialog_button_box)

    def populateComboBoxGS(self):
        """Populate grid subset combobox with choices
        corresponding to set grid_ggd and ggd indices.
        """

        self.combobox_gridSubset.clear()

        if self.g1_LineEdit.text().isdigit() != True:
            return

        gg = int(self.g1_LineEdit.text())

        # Get number of GGD grid subsets
        try:
            self.nGridSubsets = self.getGGD.getNGridSubset(gg)
        except:
            logging.error('The specified IDS does not contain any grid '
                          'subsets! Aborting.')
            return

        if self.getGGD.getNGridSubset(gg) < 1:
            logging.error('The specified IDS does not contain any grid '
                          'subsets! Aborting.')
            return



        for i in range(self.nGridSubsets):
            # Only 2D grid subsets supported for now (first object dimension
            # parameter = 3 (fortan notation, 2D -> 2+1 = 3)
            if self.getGGD.getGridSubsetDim(gridId=gg, gsId=i) == 3:
                gs_name = self.getGGD.getGridSubsetName(gridId=gg, gsId=i)
                self.combobox_gridSubset.addItem(gs_name)
                self.gridSubsetDict[gs_name] = i + 1 # Fortran notation in IDS

    def populateComboBoxQ(self):
        """Populate grid subset combobox with choices
        corresponding to set grid_ggd and ggd indices and grid subset.
        """

        self.combobox_quantity.clear()

        if self.g1_LineEdit.text().isdigit() != True:
            return

        if self.g2_LineEdit.text().isdigit() != True:
            return

        gg = int(self.g1_LineEdit.text())
        g = int(self.g2_LineEdit.text())
        gs_name = self.combobox_gridSubset.currentText()
        
        # Return if the combo box is empty
        if gs_name == '':
            return
        gs_id = self.gridSubsetDict[gs_name]

        ggd = self.ep.ggd[g]

        self.quantityDict = \
            self.getGGD.getQuantityDict(ggd=ggd, gridSubsetId=gs_id)

        for qLabel in self.quantityDict:
            self.combobox_quantity.addItem(qLabel)

    def on_close(self):
        # Returning a dictionary of values. The values are defined in
        # enumerator class GetGGDVars.

        variables = {}

        variables['gridGGDSlice'] = self.g1_LineEdit.text()
        variables['GGDSlice'] = self.g2_LineEdit.text()
        variables['gridSubsetId'] = self.gridSubsetDict[self.combobox_gridSubset.currentText()]
        variables['quantityLabel'] = self.combobox_quantity.currentText()
        variables['quantityValues'] = self.quantityDict[variables[
            'quantityLabel']]['values']

        # Checking if validating Integers.
        try:
            variables['gridGGDSlice'] = int(variables['gridGGDSlice'])
            variables['GGDSlice'] = int(variables['GGDSlice'])
            variables['gridSubsetId'] = int(variables['gridSubsetId'])
        except ValueError as e:

            variables['gridGGDSlice'] = -1
            variables['GGDSlice'] = -1
            variables['gridSubsetId'] = -1

        return variables
