# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""The source of one plugin, on screen -- and writable only if it is yours.

Two answers are said here, and both have to be said in the same place so they
cannot disagree: what the file holds, and whether this run will let you change
it. The second is not the text area's `readOnly` alone -- a greyed-out area is
what the user sees, but what makes it true is `QVizPluginSource.writeSource`
refusing a plugin IMASViz ships. A boundary that only exists in the widget is a
boundary a determined user walks through, and a careless one finds out about by
losing an edit.

Saving goes through `compileCheck` before a byte is written, for the reason the
watcher gives: a half-typed file saved out of habit should not replace the module
that answers the menu today. So the refusal lands on the box, naming the line the
interpreter stopped at, and the file on disk stays what it was.

The line numbers are not decoration. Every refusal IMASViz answers about a plugin
names a line -- the syntax check, the import guard in the catalog -- and a number
is only worth having if the user can find the line it points at.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontDatabase, QPainter, QPalette
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPlainTextEdit,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from imasviz.VizPlugins.QVizPluginSource import (readSource, userPluginsFolder,
                                                 writeSource)


class QVizLineNumberArea(QWidget):
    """The margin a `QVizCodeView` draws its line numbers in."""

    MARGIN = 52

    def __init__(self, view):
        super().__init__(view)
        self._view = view
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

    def paintEvent(self, event):
        self._view.paintLineNumbers(self, event)


class QVizCodeView(QPlainTextEdit):
    """A code view: fixed font, line numbers, and a margin that follows them."""

    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(4 * fontMetricsWidth(font))
        self._numbers = QVizLineNumberArea(self)
        self.blockCountChanged.connect(self._updateMargin)
        self.updateRequest.connect(self._updateNumbers)
        self._updateMargin(0)

    def _updateMargin(self, _blockCount=0):
        self.setViewportMargins(QVizLineNumberArea.MARGIN, 0, 0, 0)

    def _updateNumbers(self, rect, dy):
        if dy:
            self._numbers.scroll(0, dy)
        else:
            self._numbers.update(0, rect.y(), self._numbers.width(),
                                 rect.height())
        if rect.contains(self.viewport().rect()):
            self._updateMargin()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        margin = self.contentsMargins()
        self._numbers.setGeometry(margin.left(), margin.top(),
                                  QVizLineNumberArea.MARGIN,
                                  self.height() - margin.top()
                                  - margin.bottom())

    def paintLineNumbers(self, area, event):
        """Draw one number per visible block, in the colour the theme says.

        The painter is ended whatever happens inside. Measured: an exception
        raised partway through leaves the paint device open, Qt answers
        `QPaintDevice: Cannot destroy paint device that is being painted`, and the
        process dies in a later paint event with nothing naming this file -- which
        is how one wrong method name here came out as a segmentation fault while
        repainting a different window.

        `contentOffset`, and not the `viewportOffset` the snippets for this widget
        copy around: `QPlainTextEdit::viewportOffset` is protected in C++ and this
        binding does not expose it (measured with `hasattr`: True for
        `contentOffset`, False for `viewportOffset`), so asking for the second
        raised `AttributeError` on the first repaint of the editor.
        """
        painter = QPainter(area)
        try:
            palette = self.palette()
            painter.fillRect(event.rect(), palette.color(QPalette.Window))
            painter.setFont(self.font())
            # `PlaceholderText` is the role for "there, but not what you are reading
            # for" -- and it is a theme role, so the numbers follow a dark session the
            # way everything else does. Asked from the widget's own palette, because
            # the theme is on screen, not in this module.
            painter.setPen(palette.color(QPalette.PlaceholderText))

            block = self.firstVisibleBlock()
            number = block.blockNumber() + 1
            top = round(self.blockBoundingGeometry(block)
                        .translated(self.contentOffset()).top())
            bottom = top + round(self.blockBoundingRect(block).height())
            height = self.fontMetrics().height()
            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    painter.drawText(0, top, area.width() - 10, height,
                                     Qt.AlignRight, str(number))
                block = block.next()
                top = bottom
                bottom = top + round(self.blockBoundingRect(block).height())
                number += 1
        finally:
            painter.end()


def fontMetricsWidth(font):
    """How wide one character of this font is -- what a tab stop is measured in."""
    from PySide6.QtGui import QFontMetrics

    return QFontMetrics(font).horizontalAdvance(' ') or 8


class QVizPluginEditor(QDialog):
    """One plugin's source, with the write boundary stated out loud."""

    # Said when a write landed on disk, with the file it landed on. The plugin
    # manager connects it to the reload, so saving a file and having the running
    # session read it are one gesture instead of two. A Qt connection and not a
    # stored callback on purpose: a plain helper kept on a widget that holds a
    # bound method back is how the manager ends up freed by the cyclic collector
    # while Qt still owes it a paint event.
    saved = Signal(str)

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source
        self.setWindowTitle('%s — %s' % (source.name,
                                         'editing' if source.writable
                                         else 'read-only'))
        self.resize(900, 620)
        self._dirty = False
        self._buildUI()
        self._load()

    def _buildUI(self):
        layout = QVBoxLayout(self)

        self.whereLabel = QLabel()
        self.whereLabel.setTextFormat(Qt.RichText)
        self.whereLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.whereLabel)

        self.view = QVizCodeView(self)
        self.view.setReadOnly(not self.source.writable)
        self.view.textChanged.connect(self._changed)
        layout.addWidget(self.view, 1)

        self.stateLabel = QLabel('')
        self.stateLabel.setTextFormat(Qt.RichText)
        self.stateLabel.setWordWrap(True)
        layout.addWidget(self.stateLabel)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.closeButton = QPushButton('Close')
        self.closeButton.clicked.connect(self.close)
        buttons.addWidget(self.closeButton)
        self.saveButton = QPushButton('Save')
        self.saveButton.clicked.connect(self._save)
        self.saveButton.setEnabled(self.source.writable)
        buttons.addWidget(self.saveButton)
        layout.addLayout(buttons)

    def _load(self):
        try:
            text = readSource(self.source)
        except ValueError as refusal:
            self.stateLabel.setText('<b>%s</b>' % refusal)
            text = ''
        self.view.setPlainText(text or '')
        self._dirty = False
        origin = ('one of yours' if self.source.writable
                  else 'shipped with IMASViz, so it is read here and not changed')
        self.whereLabel.setText('<b>%s</b> &mdash; %s<br><code>%s</code>'
                                % (self.source.name, origin,
                                   self.source.fileName or 'no file'))
        if not self.source.writable:
            self.stateLabel.setText('To change this one, copy it into '
                                    '<code>%s</code> from the Plugins window: it '
                                    'comes back under a name of your own, and '
                                    'that copy is editable.'
                                    % userPluginsFolder())

    def _changed(self):
        self._dirty = True

    def _save(self):
        try:
            writeSource(self.source, self.view.toPlainText())
        except ValueError as refusal:
            # Nothing was written, and the box says where it stopped. The module
            # that answers the menu right now is still the one that ran before.
            self.stateLabel.setText('<b>Not written:</b> %s' % refusal)
            return False
        self._dirty = False
        self.stateLabel.setText('Written in <code>%s</code>. The Plugins menu of '
                                'every opened case answers with it from now on.'
                                % self.source.fileName)
        self.saved.emit(self.source.fileName)
        return True

    def closeEvent(self, event):
        """Ask before throwing away an edit nobody wrote."""
        if not self._dirty:
            event.accept()
            return
        from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations

        answer = QVizGlobalOperations.YesNo(
            parent=self, question='%s holds changes that were not written.\n'
                                  'Throw them away?' % self.source.fileName,
            caption='Please confirm')
        if answer:
            event.accept()
        else:
            event.ignore()
