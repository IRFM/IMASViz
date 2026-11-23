# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under this.
#
# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************
"""The prompt catalogue, as a window: choose, answer the holes, run.

The catalogue itself is disk and gestures (``VizAgent/prompts.py`` and
the ``*_prompt`` methods of the core); this module is only the shape it
wears in the application, exactly as ``QVizPluginManager`` is the shape
the plugin folders wear. Everything it shows and writes goes through the
core, so the panel, the page and the client read and write the same two
folders — a catalogue that only the Qt surface could edit is a second
catalogue.

Three rules the shape is built on:

* **Non-modal.** ``QDialog.exec()`` runs a nested event loop on the GUI
  thread, and a session with an agent running has work to do behind this
  window. ``show()`` keeps the transcript readable while a prompt is
  chosen, and the panel keeps the reference (``QVizAgentPanel.
  promptManager``) — a window no Python reference holds dies with the
  wrapper that made it.
* **Filling is not running.** *Mettre dans la boîte* puts the filled
  text in the panel's box; *Lancer* puts it there and asks it through the
  panel's own run. There is no ``run_prompt`` gesture to ask (the agent
  would be answering a turn from inside a turn), and the window does not
  pretend there is one.
* **A value the user did not type is a value they see.** Every hole
  arrives prefilled with what the four sources answer, and the line
  under it names which one answered. A hole nothing answers arrives
  empty, and the refusal ``fill_prompt`` earns names it — a prompt is
  never sent with ``{shot}`` in it, and never with a guess in its place.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# The panel is French and the source names come from the store's one
# table (``prompts.CALLED`` and its three neighbours), in English. They
# are data the user is entitled to read, not chrome to translate: a
# second table of French copies is how the two would drift apart.
SOURCE_PREFIX = 'venu de : '

NO_PROMPT = '(choisir un prompt du catalogue)'


class QVizPromptManager(QDialog):
    """The catalogue in a window: the list, the holes, the two buttons.

    ``core`` is the ``McpGuiCore`` the gestures live on — the one that
    knows which case is open, which is what answers ``{shot}`` without
    asking. ``onInsert(text)`` and ``onRun(text)`` are what the panel
    answers to a fill and to a launch: this window does not own the
    prompt box, and it does not own the agent's thread.
    """

    def __init__(self, core, parent=None, onInsert=None, onRun=None,
                 onChanged=None):
        super(QVizPromptManager, self).__init__(parent)
        self.core = core
        self.onInsert = onInsert
        self.onRun = onRun
        self.onChanged = onChanged
        self._open = None        # {'scope','id'} of the prompt on show
        self._holes = []         # the holes of that prompt, in order
        self._valueEdits = {}    # hole -> QLineEdit
        self._preview = {}       # hole -> the value the preview answered
        self._editing = None     # {'scope','id'} of the prompt being edited

        self.setWindowTitle('Prompts du catalogue')
        self.resize(720, 560)
        self.setModal(False)

        layout = QVBoxLayout(self)

        # --- the filters: a word, and the category it belongs to --------
        row = QHBoxLayout()
        self.filterEdit = QLineEdit()
        self.filterEdit.setPlaceholderText(
            'un mot du nom, de la description, de la catégorie')
        self.filterEdit.returnPressed.connect(self.refresh)
        row.addWidget(self.filterEdit)
        self.categoryBox = QComboBox()
        row.addWidget(self.categoryBox)
        refresh = QPushButton('Rafraîchir')
        refresh.clicked.connect(self.refresh)
        row.addWidget(refresh)
        layout.addLayout(row)

        # --- the catalogue itself --------------------------------------
        self.listBox = QListWidget()
        self.listBox.currentItemChanged.connect(self._onPick)
        layout.addWidget(self.listBox)

        self.bodyView = QPlainTextEdit()
        self.bodyView.setReadOnly(True)
        self.bodyView.setMaximumHeight(140)
        layout.addWidget(self.bodyView)

        # --- the holes --------------------------------------------------
        layout.addWidget(QLabel('<b>Les valeurs demandées par ce prompt</b>'))
        self.valuesGrid = QWidget()
        self.valuesLayout = QGridLayout(self.valuesGrid)
        self.valuesLayout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.valuesGrid)

        self.status = QLabel('')
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.status)

        actions = QHBoxLayout()
        self.putButton = QPushButton('Mettre dans la boîte')
        self.putButton.clicked.connect(lambda: self._fill(run=False))
        actions.addWidget(self.putButton)
        self.runButton = QPushButton('Lancer')
        actions.addWidget(self.runButton)
        self.runButton.clicked.connect(lambda: self._fill(run=True))
        self.editButton = QPushButton('Modifier')
        self.editButton.clicked.connect(self._openEdit)
        actions.addWidget(self.editButton)
        self.deleteButton = QPushButton('Supprimer')
        self.deleteButton.clicked.connect(self._delete)
        actions.addWidget(self.deleteButton)
        self.newButton = QPushButton('Nouveau')
        self.newButton.clicked.connect(self._newPrompt)
        actions.addWidget(self.newButton)
        actions.addStretch(1)
        layout.addLayout(actions)

        # --- the form of a prompt: new one, or the one on show ---------
        self.formTitle = QLabel('')
        self.nameEdit = QLineEdit()
        self.categoryEdit = QLineEdit()
        self.descriptionEdit = QLineEdit()
        self.bodyEdit = QPlainTextEdit()
        self.bodyEdit.setPlaceholderText(
            'le prompt, avec ses trous écrits {shot}, {figure}, {rho}…')
        self.variablesEdit = QLineEdit()
        self.variablesEdit.setPlaceholderText(
            'valeurs par défaut (facultatif) : shot=54924; rho=0.8')
        self.saveButton = QPushButton('Enregistrer')
        self.saveButton.clicked.connect(self._saveForm)
        self.cancelButton = QPushButton('Annuler')
        self.cancelButton.clicked.connect(self.hideForm)
        self.hideForm()
        layout.addWidget(self.formTitle)
        layout.addWidget(QLabel('nom'))
        layout.addWidget(self.nameEdit)
        layout.addWidget(QLabel('catégorie'))
        layout.addWidget(self.categoryEdit)
        layout.addWidget(QLabel('description'))
        layout.addWidget(self.descriptionEdit)
        layout.addWidget(QLabel('le prompt'))
        layout.addWidget(self.bodyEdit)
        layout.addWidget(QLabel('défauts'))
        layout.addWidget(self.variablesEdit)
        formRow = QHBoxLayout()
        formRow.addWidget(self.saveButton)
        formRow.addWidget(self.cancelButton)
        formRow.addStretch(1)
        layout.addLayout(formRow)

    # ------------------------------------------------------------------ list

    def _ask(self, gesture, **args):
        """One gesture of the core, with its refusal said here rather than
        raising out of a button. The gesture is named ``gesture``, never
        ``name``: every one of these gestures takes a ``name=`` of its own,
        and a parameter called the same thing is a call that cannot be
        made."""
        if self.core is None:
            raise ValueError(
                'aucun agent ne porte le catalogue: cette fenêtre n\'a ' +
                'personne à qui demander ses prompts.')
        return getattr(self.core, gesture)(**args)

    def _refused(self, e):
        self.status.setText('REFUSAL — %s' % e)

    def hideForm(self):
        for widget in (self.formTitle, self.nameEdit, self.categoryEdit,
                       self.descriptionEdit, self.bodyEdit,
                       self.variablesEdit, self.saveButton,
                       self.cancelButton):
            widget.setVisible(False)
        self._editing = None

    def showForm(self, title):
        self.formTitle.setText(title)
        for widget in (self.formTitle, self.nameEdit, self.categoryEdit,
                       self.descriptionEdit, self.bodyEdit,
                       self.variablesEdit, self.saveButton,
                       self.cancelButton):
            widget.setVisible(True)

    def refresh(self):
        """The list, from the two catalogues: name, category, one line of
        description — what a reader chooses on. The category box is the
        filter the catalogue answers, refilled from what it holds."""
        self.listBox.clear()
        args = {}
        word = self.filterEdit.text().strip()
        if word:
            args['query'] = word
        category = self.categoryBox.currentText()
        chosen = category not in ('', '(toutes)')
        if chosen:
            args['category'] = category
        try:
            answer = self._ask('list_prompts', **args)
        except ValueError as e:
            self._refused(e)
            return
        counts = answer.get('categories', {})
        self.categoryBox.blockSignals(True)
        keep = self.categoryBox.currentText() if chosen else ''
        self.categoryBox.clear()
        self.categoryBox.addItem('(toutes)')
        for name in sorted(counts):
            self.categoryBox.addItem(name or '(sans catégorie)')
        self.categoryBox.setCurrentIndex(
            max(0, self.categoryBox.findText(keep or '(toutes)')))
        self.categoryBox.blockSignals(False)

        last = None
        for entry in answer['prompts']:
            label = '%s — %s' % (entry['category'] or '(sans catégorie)',
                                 entry['name'])
            if entry['description']:
                label += '  ·  %s' % entry['description']
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, (entry['scope'], entry['id']))
            item.setToolTip(entry['path'])
            if last is not None and entry['category'] != last:
                self.listBox.insertSeparator(self.listBox.count())
            last = entry['category']
            self.listBox.addItem(item)
        line = '%d prompt(s)' % answer['total']
        for scope, why in sorted(
                (answer.get('catalogues_unavailable') or {}).items()):
            line += '  ·  %s : %s' % (scope, why)
        if answer.get('truncated'):
            line += '  ·  %s' % answer['truncated']
        self.status.setText(line)

    def _onPick(self, item, _previous=None):
        """One line chosen: the body, and the value each hole would take
        today — read through ``prompt_detail``, which remembers nothing:
        asking what a prompt would answer is not typing an answer in."""
        self._clearValues()
        if item is None:
            self._open = None
            self.bodyView.setPlainText('')
            return
        scope, prompt_id = item.data(Qt.UserRole)
        try:
            detail = self._ask('prompt_detail', name=prompt_id, scope=scope)
        except ValueError as e:
            self._refused(e)
            return
        self._open = {'scope': detail['scope'], 'id': detail['id']}
        self.bodyView.setPlainText(detail['text'])
        holes = detail.get('values') or {}
        self._holes = list(holes)
        for row, name in enumerate(self._holes):
            known = holes[name]
            edit = QLineEdit()
            edit.setText('' if known['value'] is None
                         else str(known['value']))
            self._valueEdits[name] = edit
            self._preview[name] = edit.text()
            self.valuesLayout.addWidget(QLabel('{%s}' % name), row, 0)
            self.valuesLayout.addWidget(edit, row, 1)
            self.valuesLayout.addWidget(
                QLabel(SOURCE_PREFIX + known['source'] if known['value']
                       else 'rien ne répond ce trou : écrivez la valeur'),
                row, 2)
        note = (detail.get('context') or {}).get('note')
        if note:
            self.status.setText(note)

    def _clearValues(self):
        while self.valuesLayout.count():
            item = self.valuesLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._valueEdits = {}
        self._preview = {}
        self._holes = []

    # ------------------------------------------------------------------ run

    def _valuesOfForm(self):
        """Only what the hand changed since the preview.

        The fields arrive filled — that is the point of the preview — and
        sending them back as they stand would call every one of them a
        value the user named: ``{shot}`` would read ``you named it`` under
        a number this session answered, and worse, it would be remembered.
        The next case open would then answer the shot of the old one,
        because a remembered value outranks the session. So a field left
        as the preview filled it answers nothing here, and the source that
        answered it keeps its name.
        """
        out = {}
        for name, edit in self._valueEdits.items():
            text = edit.text().strip()
            if text and text != (self._preview.get(name) or '').strip():
                out[name] = text
        return out

    def _fill(self, run=False):
        """The holes answered, and the text handed to the panel. The
        refusal is the store's: it names the holes nothing answered, and
        nothing here picks a value in their place."""
        if not self._open:
            self.status.setText('REFUSAL — choisissez un prompt de la '
                                'liste : ses trous sont ce qui se remplit.')
            return
        try:
            answer = self._ask('fill_prompt', name=self._open['id'],
                               scope=self._open['scope'],
                               values=self._valuesOfForm())
        except ValueError as e:
            self._refused(e)
            return
        filled = [name for name, one in answer['values'].items()
                  if one['value']]
        self.status.setText('%s — %s' % (
            answer['name'],
            ', '.join('{%s} (%s)' % (name, answer['values'][name]['source'])
                      for name in sorted(filled)) or 'aucun trou à remplir'))
        text = answer['text']
        if self.onInsert:
            self.onInsert(text)
        if run and self.onRun:
            self.onRun(text)

    # ---------------------------------------------------------------- write

    def _newPrompt(self):
        """A prompt written here. The name leads its id, so a second
        prompt under the same name is a refusal, not a file overwritten."""
        self._editing = None
        self.nameEdit.setText('')
        self.categoryEdit.setText(self.categoryBox.currentText()
                                  if self.categoryBox.currentIndex() > 0
                                  else '')
        self.descriptionEdit.setText('')
        self.bodyEdit.setPlainText('')
        self.variablesEdit.setText('')
        self.showForm('<b>Nouveau prompt</b> — son nom devient l\'identifiant '
                      'que le catalogue, les valeurs et les relances lisent')

    def _openEdit(self):
        """The prompt on show, in the form: read back through
        ``prompt_detail``, so the form holds what the file holds. The id
        is not a field an edit moves — a prompt under another name is a
        new prompt."""
        if not self._open:
            self.status.setText('REFUSAL — modifiez un prompt choisi de la '
                                'liste.')
            return
        try:
            detail = self._ask('prompt_detail', name=self._open['id'],
                               scope=self._open['scope'])
        except ValueError as e:
            self._refused(e)
            return
        self._editing = {'scope': detail['scope'], 'id': detail['id']}
        self.nameEdit.setText(detail['name'])
        self.nameEdit.setEnabled(False)
        self.categoryEdit.setText(detail['category'])
        self.descriptionEdit.setText(detail['description'])
        self.bodyEdit.setPlainText(detail['text'])
        self.variablesEdit.setText('; '.join(
            '%s=%s' % (name, value)
            for name, value in sorted(detail['variables'].items()) if value))
        self.showForm('<b>Modifier « %s »</b> — il garde l\'identifiant %s '
                      'sous lequel ses valeurs sont rappelées'
                      % (detail['name'], detail['id']))

    def _saveForm(self):
        text = self.bodyEdit.toPlainText().strip()
        name = self.nameEdit.text().strip()
        if not text:
            self.status.setText('REFUSAL — un prompt doit dire ce qu\'il '
                                'demande : le texte nommé est vide.')
            return
        if not name and not self._editing:
            self.status.setText('REFUSAL — un prompt a besoin d\'un nom : '
                                'c\'est ce que le catalogue affiche et ce '
                                'que ses valeurs retiennent.')
            return
        variables = self.variablesEdit.text().strip()
        args = {
            'text': text,
            'category': self.categoryEdit.text().strip(),
            'description': self.descriptionEdit.text().strip(),
        }
        if self._editing:
            # An edit always names its declaration, so an empty box
            # clears the defaults and leaves the holes the text opens on
            # their own.
            args['variables'] = variables
            args['name'] = self._editing['id']
            args['scope'] = self._editing['scope']
            tool = 'edit_prompt'
        else:
            if variables:
                args['variables'] = variables
            args['name'] = name
            tool = 'save_prompt'
        try:
            answer = self._ask(tool, **args)
        except ValueError as e:
            self._refused(e)
            return
        finally:
            self.nameEdit.setEnabled(True)
        self.hideForm()
        # The list first, the confirmation after: ``refresh`` answers how
        # many prompts the shelves hold, and a hand that just filed one
        # needs to read that its own file went in, not how many others
        # are on the shelf.
        self.refresh()
        self.status.setText('%s : %s  —  %s'
                            % (tool, answer['id'], answer['path']))
        if self.onChanged:
            self.onChanged()

    def _delete(self):
        if not self._open:
            self.status.setText('REFUSAL — supprimez un prompt choisi de la '
                                'liste.')
            return
        scope, prompt_id = self._open['scope'], self._open['id']
        try:
            answer = self._ask('delete_prompt', name=prompt_id, scope=scope)
        except ValueError as e:
            self._refused(e)
            return
        self._clearValues()
        self.bodyView.setPlainText('')
        self._open = None
        self.refresh()
        self.status.setText('supprimé : %s (%s) — %s'
                            % (answer.get('deleted', prompt_id), scope,
                               answer.get('path', '')))
        if self.onChanged:
            self.onChanged()
