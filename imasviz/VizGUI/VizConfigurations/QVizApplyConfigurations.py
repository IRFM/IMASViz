# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The "Apply Configuration" window of a shot view.

Two tabs, as the manual describes them: the plot configurations and the node
selections this application has written, each listed from the folder, each
applied to the shot view the window was opened from -- and the window says which
one, because a configuration names paths and the same path means a different
quantity in a different database.

The list is read from the folder every time the window is shown, so a
configuration saved from any window -- a Table Plot View's button, another shot
view, or the user's own editor -- is there without the application having to
tell this window about it. The command that used to save a selection refreshed
it by reaching through ``dataTreeView.parent.configurationListsWindow``, a chain
of three attributes with no guard on it; a save from anywhere else left the list
stale, and two clicks on the menu entry built two windows.

Nothing here parses a file: the list comes from the folder, and what a file
names is the format's business.
"""

import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QLabel, QListWidget, QPushButton,
                               QSizePolicy, QTabWidget, QVBoxLayout, QWidget)

from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import \
    QVizConfigurationFile, PLOT, SELECTION
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectFromConfiguration \
    import QVizSelectFromConfiguration
from imasviz.VizGUI.VizGUICommands.VizDataSelection.QVizSelectNodes \
    import QVizSelectNodes
from imasviz.VizGUI.VizGUICommands.VizPlotting.QVizPlotAsTable import \
    QVizPlotAsTable
from imasviz.VizUtils import GlobalFonts, QVizGlobalOperations


class QVizApplyConfigurations(QDialog):
    """The configurations this application can apply, listed by kind."""

    def __init__(self, dataTreeView):
        super().__init__(dataTreeView.parent)
        self.dataTreeView = dataTreeView
        self.setWindowTitle('Apply Configurations')

        self.tabs = QTabWidget()
        self.tabs.addTab(QVizConfigurationsTab(self, PLOT),
                         'Available Plot Configurations')
        self.tabs.addTab(QVizConfigurationsTab(self, SELECTION),
                         'Available Node Selection Configurations')

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def showEvent(self, event):
        """Read the folder again: a configuration may have been saved since."""
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        for index in range(self.tabs.count()):
            self.tabs.widget(index).refresh()

    def selectedFile(self, kind):
        """The configuration the user picked in the tab of that kind."""
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            if tab.kind == kind:
                return tab.selectedFile()
        return None

    def apply(self, kind, andPlot=False):
        """Apply the configuration of that kind to this shot view.

        Returns the frame a plot configuration opened, or None. The reason a
        configuration cannot be applied is said in the log panel of the shot
        view, which is where the manual tells the user to look.
        """
        path = self.selectedFile(kind)
        if path is None:
            logging.getLogger(self.dataTreeView.uri).warning(
                'No configuration is selected in the %s tab.'
                % ('plot configuration' if kind == PLOT else 'node selection'))
            return None

        QVizSelectNodes(self.dataTreeView).unselectAll()
        try:
            QVizSelectFromConfiguration(self.dataTreeView, path).execute()
            if not andPlot:
                return None
            frame = QVizPlotAsTable(self.dataTreeView,
                                    configFile=path).execute()
        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))
            return None
        if frame is not None:
            self.dataTreeView.imas_viz_api.addPlotWidgetToMDI(frame)
        return frame

    def remove(self, kind):
        """Delete the configuration of that kind, once the user confirmed."""
        path = self.selectedFile(kind)
        if path is None:
            return None
        if not QVizGlobalOperations.YesNo(
                parent=self,
                question='The configuration %s will be deleted. Are you sure?'
                         % path,
                caption='Please confirm'):
            return None
        try:
            QVizConfigurationFile(kind=kind, path=path).remove()
        except ValueError as e:
            logging.getLogger(self.dataTreeView.uri).error(str(e))
            return None
        logging.getLogger(self.dataTreeView.uri).info('Configuration "%s" '
                                                      'removed.' % path)
        self.refresh()
        return path


class QVizConfigurationsTab(QWidget):
    """One kind of configuration: the list, what may be done to it, and the
    note naming the shot view it would be applied to."""

    def __init__(self, window, kind):
        super().__init__(window)
        self.window = window
        self.kind = kind
        self.dataTreeView = window.dataTreeView

        self.listWidget = QListWidget(self)
        self.listWidget.setSizePolicy(QSizePolicy(QSizePolicy.Expanding,
                                                 QSizePolicy.Expanding))

        buttons = QVBoxLayout()
        buttons.setSpacing(5)
        buttons.setContentsMargins(15, 0, 15, 0)
        if kind == PLOT:
            self.addButton(buttons, 'Apply selection and plot selected data',
                           lambda: self.window.apply(PLOT, andPlot=True))
        else:
            self.addButton(buttons, 'Apply Node Selection Configuration to '
                                    'current IMAS database',
                           lambda: self.window.apply(SELECTION))
        self.addButton(buttons, 'Apply selection only',
                       lambda: self.window.apply(kind))
        self.addButton(buttons, 'Remove configuration',
                       lambda: self.window.remove(kind))

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.addWidget(self.listWidget, 1)
        layout.addLayout(buttons)
        layout.addLayout(self.note())
        self.setLayout(layout)

        self.refresh()

    @staticmethod
    def addButton(layout, text, action):
        button = QPushButton(text)
        button.clicked.connect(action)
        layout.addWidget(button)

    def note(self):
        """The manual's note: which shot view a configuration applies to."""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(10, 0, 10, 0)
        for text, font in (('Note:', GlobalFonts.TITLE_MEDIUM),
                           ('The configuration will be applied ONLY to the '
                            'single currently opened IMAS database source:',
                            GlobalFonts.TEXT_MEDIUM),
                           (self.dataTreeView.parent.windowTitle(),
                            GlobalFonts.TITLE_MEDIUM)):
            label = QLabel()
            label.setText(text)
            label.setAlignment(Qt.AlignLeft)
            label.setWordWrap(True)
            label.setFont(font)
            layout.addWidget(label)
        return layout

    def refresh(self):
        """The configurations of this kind the folder holds, in order."""
        self.listWidget.clear()
        for name in QVizConfigurationFile.listing(self.kind):
            self.listWidget.addItem(name)

    def selectedFile(self):
        """The path of the picked configuration, or None."""
        items = self.listWidget.selectedItems()
        if not items:
            return None
        return os.path.join(QVizConfigurationFile.directory(), items[0].text())
