# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Integrated GUI Dialog for creating and scaffolding a new IMASViz plugin."""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QComboBox, QPushButton, QMessageBox
)
from imasviz.VizPlugins.create_plugin import createPlugin
from imasviz.VizPlugins.VizPlugin import registerPlugin


class QVizPluginCreatorDialog(QDialog):
    """Dialog window allowing users to create a new plugin from the UI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Create New IMASViz Plugin')
        self.resize(480, 420)
        self._buildUI()

    def _buildUI(self):
        layout = QVBoxLayout(self)

        # Title / Info
        infoLabel = QLabel('<b>Scaffold a new IMASViz plugin</b><br>'
                           'This will create a new plugin package under VizPlugins/ and register it.')
        layout.addWidget(infoLabel)

        # Plugin Name
        layout.addWidget(QLabel('Plugin Name (e.g. <code>my_analysis</code>):'))
        self.nameInput = QLineEdit()
        self.nameInput.setPlaceholderText('my_analysis')
        layout.addWidget(self.nameInput)

        # Target IDS
        layout.addWidget(QLabel('Target IDS (e.g. <code>equilibrium</code>, <code>core_profiles</code>):'))
        self.idsInput = QComboBox()
        self.idsInput.setEditable(True)
        self.idsInput.addItems(['equilibrium', 'core_profiles', 'magnetics', 'summary', 'wall'])
        layout.addWidget(self.idsInput)

        # Menu Title
        layout.addWidget(QLabel('Menu Title:'))
        self.titleInput = QLineEdit()
        self.titleInput.setPlaceholderText('My Custom Plugin Analysis...')
        layout.addWidget(self.titleInput)

        # Description
        layout.addWidget(QLabel('Description:'))
        self.descInput = QTextEdit()
        self.descInput.setPlaceholderText('Describe what your plugin does...')
        self.descInput.setMaximumHeight(80)
        layout.addWidget(self.descInput)

        # Buttons
        btnLayout = QHBoxLayout()
        self.createBtn = QPushButton('Create Plugin')
        self.createBtn.clicked.connect(self._onAccept)
        self.cancelBtn = QPushButton('Cancel')
        self.cancelBtn.clicked.connect(self.reject)

        btnLayout.addStretch()
        btnLayout.addWidget(self.cancelBtn)
        btnLayout.addWidget(self.createBtn)
        layout.addLayout(btnLayout)

    def _onAccept(self):
        name = self.nameInput.text().strip()
        if not name:
            QMessageBox.warning(self, 'Validation Error', 'Plugin name cannot be empty.')
            return

        targetIds = self.idsInput.currentText().strip() or 'equilibrium'
        menuTitle = self.titleInput.text().strip() or f'{name} action'
        description = self.descInput.toPlainText().strip() or f'Custom plugin {name}'

        try:
            className, dirName = createPlugin(
                name, targetIds=targetIds, description=description, menuTitle=menuTitle
            )
            # Register in memory
            modulePath = f'{dirName}.{className}'
            registerPlugin(className, modulePath)

            QMessageBox.information(
                self, 'Success',
                f'Plugin <b>{className}</b> successfully created and registered!\n'
                f'Files saved under <code>VizPlugins/{dirName}/</code>'
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to create plugin:\n{e}')
