# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The dialog that names the case an export writes.

The manual lists four fields -- user name, IMAS database name, shot number, run
number -- and this shows those four, plus the backend the previous dialog asked
for as a number the user had to know (``13`` written in the box, the manual
never mentioning it). A choice is asked here as a choice, not as a number.

The fields are checked where they are typed: a shot number that can only hold
digits cannot answer ``ValueError: invalid literal for int() with base 10:
'abc'`` out of the OK button, which is what the old dialog did because it read
its text boxes with ``int()`` inside the handler. The two notes the manual
attaches to this dialog are shown in it, and the fields start from the case that
is open rather than from ``/`` for a user and ``/`` for a database -- a URI
naming a user called ``/`` is never what the user meant.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QGridLayout,
                               QLabel, QLineEdit, QVBoxLayout, QWidget)

from imasviz.VizGUI.VizGUICommands.VizDataExport.QVizExportTarget import \
    QVizExportTarget, HDF5, MDSPLUS
from imasviz.VizUtils import GlobalFonts

BACKEND_LABELS = (('HDF5', HDF5), ('MDSplus', MDSPLUS))


class QVizExportDialog(QDialog):
    """Ask for the case to export to, and answer what it spells."""

    def __init__(self, parent, prefill=None):
        super().__init__(parent)
        self.prefill = prefill or QVizExportTarget()
        self.setWindowTitle('Export browsed tree view contents to local ID')

        layout = QVBoxLayout()
        layout.addWidget(self._note(
            'Note 1: Only IDSs that are CURRENTLY OPENED in the tree view will '
            'be exported!'))
        layout.addWidget(self._note(
            'Note 2: Make sure the database/machine (created using the imasdb '
            'command) exists!'))
        layout.addWidget(self._fields())
        self.setLayout(layout)

    def _note(self, text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(GlobalFonts.TEXT_MEDIUM)
        return label

    def _fields(self):
        grid = QGridLayout()
        grid.setVerticalSpacing(6)
        values = [('User name', 'user', QLineEdit(self.prefill.user), None),
                  ('IMAS database name', 'database',
                   QLineEdit(self.prefill.database), None),
                  ('Shot number', 'shot', QLineEdit(),
                   QIntValidator(1, 999999999, self)),
                  ('Run number', 'run', QLineEdit(),
                   QIntValidator(0, 999999, self))]
        for row, (label, name, box, validator) in enumerate(values):
            if name == 'shot' and self.prefill.shot is not None:
                box.setText(str(self.prefill.shot))
            elif name == 'run' and self.prefill.run is not None:
                box.setText(str(self.prefill.run))
            if validator is not None:
                box.setValidator(validator)
            grid.addWidget(QLabel(label + ':'), row, 0)
            grid.addWidget(box, row, 1)
            setattr(self, name + 'Box', box)

        self.backendCombo = QComboBox(self)
        for label, _ in BACKEND_LABELS:
            self.backendCombo.addItem(label)
        self.backendCombo.setCurrentIndex(
            1 if self.prefill.backend == MDSPLUS else 0)
        grid.addWidget(QLabel('Backend:'), len(values), 0)
        grid.addWidget(self.backendCombo, len(values), 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                   Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        grid.addWidget(buttons, len(values) + 1, 0, 1, 2)

        host = QWidget()
        host.setLayout(grid)
        return host

    def target(self):
        """What was typed, as a target -- raising with what is missing.

        Called only once the dialog was accepted, so a cancelled dialog writes
        nothing: the old dialog kept its OK handler's failure inside a bare
        ``except:`` and left the user with a half-made case directory.
        """
        return QVizExportTarget(
            user=self.userBox.text(),
            database=self.databaseBox.text(),
            shot=self._number(self.shotBox),
            run=self._number(self.runBox),
            backend=BACKEND_LABELS[self.backendCombo.currentIndex()][1],
            dataVersion=self.prefill.dataVersion)

    @staticmethod
    def _number(box):
        """The number a validated box holds, None when it holds nothing.

        The validator keeps letters out; an empty box is a missing run number,
        and 0 is a run number -- so an empty box has to stay distinguishable from
        a zero, which ``int('')`` does not do.
        """
        text = box.text().strip()
        return int(text) if text else None
