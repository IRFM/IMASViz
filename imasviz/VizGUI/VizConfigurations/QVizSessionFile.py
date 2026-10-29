# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a session file is, and what it may say.

A session is the set of windows the user had on screen: which case was open,
which occurrences of which IDS had been loaded -- and with which choice of time
slices --, which branches of the tree were unfolded, which quantities were
selected, and which figures were drawn with which quantities in them. This file
says all of that, and nothing about a widget.

It says nothing about a widget because that is what the previous attempt at
saving state did, and it is why nothing came back: the plot-configuration writer
read 23 keys off ``PlotDataItem.opts`` by name and called ``QPen`` methods on
whatever the pen had become. Measured on this pyqtgraph, its button wrote no
file at all (``KeyError: 'name'``, and with that key supplied by hand
``AttributeError: 'tuple' object has no attribute 'brush'``), and of what it did
write the reader kept two attributes per panel. So the session file records the
*questions* the application asked -- a case URI, an IDS name, an occurrence, a
slice choice, a node path, a figure key -- and whoever restores it replays the
gestures that answer them. A restored window is then a window the drawing code
built, not a screenshot of one: it responds to every gesture because it *is* one
of the frames, with its sliders, its abscissa and its legend.

The figure key is in the file on purpose. A key is the identity of a window:
the Show/Hide sub-menu, the Delete sub-menu and the "add this quantity to that
figure" entries all read ``Viz_API.figureframes`` by that key, and
``GetNextKeyForFigure`` answers max+1. Replaying the gestures without the keys
would renumber the windows -- measured on a session of two curve figures and one
image, ``SlicesPlot1`` came back as ``SlicesPlot2`` and ``SlicesImage1`` as
``SlicesImage2`` -- so a file naming the windows it had would no longer describe
the ones on screen. The restore therefore honours the keys it reads, and refuses
a key that is already in use by a live window rather than drawing under it.

Version 2, and what it adds
--------------------------

Version 1 says which windows were open and what they drew. It does not say what
the user had *set* on them, so a session came back with its windows and without
the reason they were drawn: a curve zoomed onto one bump came back zoomed out,
a tensor walked to element 12 came back on the element the tree stood on, the
error bars a click had put on a curve were gone. So version 2 adds four elements
per ``<Figure>``, each one a thing the frame already answers rather than a
picture of a widget:

* ``<Cursors folded="0|1">`` with one ``<Cursor key index/>`` per slider of the
  band -- the choice of element for every array of structures the figure fixes
  rather than draws. The key is ``QVizAxis.key()`` spelled out, because two
  quantities of one figure can sit at the same nesting level in different
  arrays, and a control keyed by the level moves one and is read back for the
  other;
* ``<View x0 x1 y0 y1 autoX autoY xInverted yInverted/>`` -- pyqtgraph's own
  view state, read off ``viewRange()`` and ``state['autoRange']``. Measured on
  the reference case: a range set by hand **survives a re-read of the curves**
  (``[[-0.0416, 1.0416], [-0.0526, 1.0526]]`` before a ``refresh`` and the same
  after), and putting it back costs **0,0007 s**;
* ``<Errors bars bands/>`` -- the three lines of the right-click menu, read as
  the frame keeps them: how many bars, how many bands, and the slicing step.
  Measured on ``magnetics/flux_loop(0)/flux/data``: putting the bars back costs
  **0,012 s** over 17 344 samples and the band **0,051 s**;
* ``<Window x y w h maximized hidden/>`` -- where the window sat in the MDI
  area, in its own geometry rather than a ``QMdiArea`` state: this PySide6
  answers no ``saveState`` on a ``QMdiArea`` (measured with ``hasattr`` at run
  time, and in ``QtWidgets.pyi``: 43 methods, none of them one), unlike
  ``QMainWindow``.

The numbers are small because the restore replays them, it does not replay the
drawing: one ``refresh`` for all the sliders of a band costs **0,001 s** where
one per slider costs **0,003 s**, and the whole of version 2 adds about **400
bytes** to the 944-byte file of a two-figure session.

Versions 1 and 2 are both read, and writing produces 2. A version 1 file simply
has no such elements, which is the same as the user having set nothing.

One version, and a refusal rather than a guess: ``version`` is checked, and an
element this module does not know is named in a ``ValueError``. Ignoring what it
does not read is how a file silently stops describing the session it was written
for -- the configuration reader did exactly that for a file whose extension it
did not recognise, answering "no quantities" without a word.
"""

import os
import xml.etree.ElementTree as ET
from collections import namedtuple

from imasviz.VizGUI.VizConfigurations.QVizConfigurationFile import (
    QVizConfigurationFile, SESSION)

QVizSessionLoad = namedtuple('QVizSessionLoad', 'ids occurrence slices')
QVizSessionExpanded = namedtuple('QVizSessionExpanded', 'ids occurrence')
QVizSessionSelection = namedtuple('QVizSessionSelection', 'path occurrence')
QVizSessionQuantity = namedtuple('QVizSessionQuantity',
                                 'path occurrence uri row column')
QVizSessionCursor = namedtuple('QVizSessionCursor', 'key index')
QVizSessionCursors = namedtuple('QVizSessionCursors', 'folded cursors')
QVizSessionView = namedtuple('QVizSessionView',
                             'x0 x1 y0 y1 autoX autoY xInverted yInverted')
QVizSessionErrors = namedtuple('QVizSessionErrors', 'bars bands')
QVizSessionWindow = namedtuple('QVizSessionWindow',
                               'x y w h maximized hidden')
QVizSessionFigure = namedtuple(
    'QVizSessionFigure',
    'key kind quantities axis tensor cursors view errors window',
    # A figure written before version 2 has no state to carry, and the four
    # fields being absent is exactly that: nothing was set.
    defaults=(None, None, None, None))

QVizSessionCase = namedtuple('QVizSessionCase',
                             'uri dd_version label loads expanded selection')

ROOT = 'IMASVizSession'
VERSION = '2'
# Both are read. A version 1 file holds no `<Cursors>`, `<View>`, `<Errors>` or
# `<Window>`, which is the same answer as a user who set nothing on those
# windows: the windows come back as the drawing leaves them.
READABLE_VERSIONS = ('1', '2')

# The name of the session the application writes when it closes and offers when
# it starts. A name, not a path: where it lives is the folder's business, and the
# guard that keeps a name inside that folder is the one the typed names go
# through. `last_session` rather than something the user would type over, because
# it is the one session that is never asked for by hand.
LAST_SESSION = 'last_session'

# The four windows this application draws from a selection. A plugin window is
# not one of them: it is built by the plugin, from a question the plugin asks
# (the Profiles plugin asks which occurrence to plot through a modal dialog), so
# a session file cannot say what it held. The Equilibrium chart is not in an MDI
# window either, and holds no node of the tree.
CURVE = 'curve'
IMAGE = 'image'
TABLE = 'table'
STACKED = 'stacked'
KINDS = (CURVE, IMAGE, TABLE, STACKED)

# How many elements of a dynamic array of structures a view keeps. Spelled as a
# word here because an integer would be a promise about the case: the reference
# `equilibrium` occurrence 0 holds 49 slices, and an index is only valid inside
# the array of the shot the file was written for. `index=N` is the exception the
# manual documents as the fourth choice; it is restored for the case the file
# names, and refused by name if that case does not hold that many. The words are
# named short because the commands that write them import the four *objects* they
# stand for, and two similar names for one choice in one file is how a word and
# an object get mixed up.
ALL = 'all'
ONE_IN_TEN = 'one_in_ten'
FIRST = 'first'
INDEX_PREFIX = 'index='
SLICE_WORDS = (ALL, ONE_IN_TEN, FIRST)

# The error bars, spelled the way the menu asks for them. *Show/Hide error bars*
# draws one per sample and *Show error bars (with slicing)* asks a step, so the
# file says which of the two the user clicked and what step was answered; an
# integer alone would not tell them apart, and re-asking a question the user
# already answered is what a restore must not do.
BARS_ALL = 'all'
BARS_STEP = 'step='

# A cursor key is the tuple `QVizAxis.key()` answers -- (origin, IDS, name) --
# spelled with a slash between the parts. No part carries one: the coordinate is
# normalised to dots by `key()` itself, an IDS name has none, and an origin is
# `AOS` or `LEAF`. The third part is the array name, the coordinate, or -- when
# neither is known -- the nesting level, which comes back as a number.
CURSOR_KEY_SEPARATOR = '/'


def cursorKeyText(key):
    """The file's spelling of one slider's axis."""
    return CURSOR_KEY_SEPARATOR.join(str(part) for part in key)


def cursorKeyOf(text, path):
    """The tuple a spelled key stands for, refused by naming what it said."""
    parts = text.split(CURSOR_KEY_SEPARATOR)
    if len(parts) != 3:
        raise ValueError('"%s" spells a cursor key "%s": a key names the origin, '
                         'the IDS and the array or coordinate, separated by "%s".'
                         % (path, text, CURSOR_KEY_SEPARATOR))
    origin, idsName, third = parts
    if origin == 'AOS' and third.isdigit():
        # The level spelling, which is what `key()` falls back on when the array
        # has neither a name nor a loop letter. Left as text it would never match
        # the axis it names, and the restore would report a slider that does not
        # exist for a key that does.
        third = int(third)
    return (origin, idsName, third)


class QVizSessionFile:
    """A session: the cases it names, the windows it drew, and its file."""

    def __init__(self, cases=(), figures=(), path=None):
        """
        Arguments:
            cases   (list) : [QVizSessionCase], in the order the user opened them.
            figures (list) : [QVizSessionFigure], in the order the api handed out
                             their keys. They are beside the cases, not inside
                             one: one curve figure can hold quantities read from
                             two shot views -- that is what *Plot the selection
                             in a figure* with *all databases* does -- so a
                             figure belongs to the session, and each of its
                             quantities names the case it came from.
            path    (str)  : the file it was read from, or the one it is written
                             to.
        """
        self.cases = list(cases)
        self.figures = list(figures)
        self.path = path

    # ---------------------------------------------------------------- names
    @staticmethod
    def named(name):
        """The path of the session a user just named.

        The name comes from a text field, so the same guard that protects a
        configuration name applies: a session lives in the configuration folder,
        and a name naming a directory is refused there for the same reason.
        """
        return QVizConfigurationFile.named(name, SESSION)

    @staticmethod
    def listing():
        """The sessions the folder holds, as the dialog lists them."""
        return QVizConfigurationFile.listing(SESSION)

    # ------------------------------------------------------------ last session
    @staticmethod
    def lastSession():
        """The file the application writes when it closes, and offers at start-up.

        One name nobody chose, in the folder the manual already tells the user
        about, and written through the same guard as a named session -- so the
        file the close writes is a session the *Load session* menu lists like any
        other. `listing()` will show it under this name, which is the point: a
        session that cannot be found by hand is a file, not a feature.
        """
        return QVizConfigurationFile.named(LAST_SESSION, SESSION)

    @staticmethod
    def hasLastSession():
        """Whether such a file is there -- answered without ever raising.

        Asked before a dialog is opened: a session that is not there must not ask
        a question, and a `HOME` this application cannot read is not a reason to
        lose the window the user is opening.
        """
        try:
            path = QVizSessionFile.lastSession()
        except ValueError:
            return False
        return os.path.isfile(path)

    # --------------------------------------------------------------- reading
    @staticmethod
    def read(path):
        """The session a ``.vsess`` file holds."""
        try:
            root = ET.parse(path).getroot()
        except OSError as e:
            raise ValueError('Cannot read the session "%s": %s' % (path, e))
        except ET.ParseError as e:
            raise ValueError('"%s" is not a session file: it is not well-formed '
                             'XML (%s).' % (path, e))
        if root.tag != ROOT:
            raise ValueError('"%s" holds a <%s>: a session written by this '
                             'application has a <%s> root.'
                             % (path, root.tag, ROOT))
        version = root.get('version')
        if version not in READABLE_VERSIONS:
            raise ValueError('"%s" declares session version "%s", which this '
                             'application cannot read: it reads %s and writes '
                             'version %s.'
                             % (path, version, ' and '.join(READABLE_VERSIONS),
                                VERSION))
        _knownChildren(root, ('Case', 'Figure'), path)
        return QVizSessionFile(
            cases=[_caseOf(element, path) for element in root.findall('Case')],
            figures=[_figureOf(element, path)
                     for element in root.findall('Figure')],
            path=path)

    # -------------------------------------------------------------- writing
    def write(self, path=None):
        """Write the file: one element per thing the session held."""
        path = path if path is not None else self.path
        if path is None:
            raise ValueError('No file was named to write the session to.')
        root = ET.Element(ROOT)
        root.set('version', VERSION)
        for case in self.cases:
            element = ET.SubElement(root, 'Case')
            element.set('uri', case.uri)
            if case.dd_version:
                element.set('dd_version', case.dd_version)
            if case.label:
                element.set('label', case.label)
            for load in case.loads:
                child = ET.SubElement(element, 'Load')
                child.set('ids', load.ids)
                child.set('occurrence', str(load.occurrence))
                child.set('slices', load.slices)
            for expanded in case.expanded:
                child = ET.SubElement(element, 'Expanded')
                child.set('ids', expanded.ids)
                if expanded.occurrence is not None:
                    child.set('occurrence', str(expanded.occurrence))
            for selection in case.selection:
                child = ET.SubElement(element, 'Selection')
                child.set('path', selection.path)
                child.set('occurrence', str(selection.occurrence))
        for figure in self.figures:
            element = ET.SubElement(root, 'Figure')
            element.set('key', figure.key)
            element.set('kind', figure.kind)
            if figure.axis:
                element.set('axis', figure.axis)
            if figure.tensor:
                element.set('tensor', '1')
            for quantity in figure.quantities:
                leaf = ET.SubElement(element, 'Quantity')
                leaf.set('path', quantity.path)
                leaf.set('occurrence', str(quantity.occurrence))
                if quantity.uri:
                    leaf.set('uri', quantity.uri)
                # A place in a table grid is written only when there is one:
                # `str(None)` is what an absent place used to become, and the
                # reader of that file answered `invalid literal for int()
                # with base 10: 'None'`, which cost the entry its panel.
                if quantity.row is not None and quantity.column is not None:
                    leaf.set('row', str(quantity.row))
                    leaf.set('column', str(quantity.column))
            self._writeCursors(element, figure.cursors)
            self._writeView(element, figure.view)
            self._writeErrors(element, figure.errors)
            self._writeWindow(element, figure.window)
        _indent(root)
        ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
        self.path = path
        return path

    # ------------------------------------------------- what was set on a window
    # Each of the four elements below is written only when there is something to
    # say, and an attribute inside one only when it is not what a freshly drawn
    # window answers. A file that repeats the default of every window pins what
    # the drawing would have chosen anyway -- and a stale range is worse than no
    # range at all.

    @staticmethod
    def _writeCursors(element, cursors):
        """One `<Cursor>` per slider of the band, and how the band stands."""
        if cursors is None or not cursors.cursors:
            return
        child = ET.SubElement(element, 'Cursors')
        if cursors.folded is not None:
            child.set('folded', '1' if cursors.folded else '0')
        for cursor in cursors.cursors:
            leaf = ET.SubElement(child, 'Cursor')
            leaf.set('key', cursorKeyText(cursor.key))
            leaf.set('index', str(cursor.index))

    @staticmethod
    def _writeView(element, view):
        """The range the window was looking at, and which axes fit themselves."""
        if view is None:
            return
        child = ET.SubElement(element, 'View')
        for name, value in [('x0', view.x0), ('x1', view.x1),
                            ('y0', view.y0), ('y1', view.y1)]:
            child.set(name, repr(float(value)))
        # Both axes fitting their curves is what the restore's own drawing does,
        # so there is nothing to put back. What is written is the axes the user
        # took off that rule: `autoX="0"` says this range was set by hand.
        if not view.autoX:
            child.set('autoX', '0')
        if not view.autoY:
            child.set('autoY', '0')
        if view.xInverted:
            child.set('xInverted', '1')
        if view.yInverted:
            child.set('yInverted', '1')

    @staticmethod
    def _writeErrors(element, errors):
        """Which of the three right-click lines were on."""
        if errors is None:
            return
        child = ET.SubElement(element, 'Errors')
        if errors.bars is not None:
            child.set('bars', BARS_ALL if int(errors.bars) == 1
                      else '%s%d' % (BARS_STEP, int(errors.bars)))
        if errors.bands:
            child.set('bands', '1')

    @staticmethod
    def _writeWindow(element, window):
        """Where the window sat in the MDI area.

        A geometry of its own rather than a `QMdiArea` state, because this
        PySide6 has no `saveState` on a `QMdiArea`. The four numbers are what
        `QMdiSubWindow.geometry()` answers and what `setGeometry` takes back:
        measured off screen, (120, 90, 640, 420) round-trips unchanged.
        """
        if window is None:
            return
        child = ET.SubElement(element, 'Window')
        for name, value in [('x', window.x), ('y', window.y),
                            ('w', window.w), ('h', window.h)]:
            child.set(name, str(int(value)))
        if window.maximized:
            child.set('maximized', '1')
        if window.hidden:
            child.set('hidden', '1')

    # ------------------------------------------------------------ questions
    def quantities(self):
        """Every quantity every figure of the session names."""
        return [quantity for figure in self.figures
                for quantity in figure.quantities]

    def __str__(self):
        return '<QVizSessionFile %s: %d case(s), %d figure(s)>' % (
            self.path, len(self.cases), len(self.figures))


def _caseOf(element, path):
    _knownChildren(element, ('Load', 'Expanded', 'Selection'), path)
    uri = _attribute(element, 'uri', path, 'Case')
    return QVizSessionCase(
        uri=uri,
        dd_version=element.get('dd_version'),
        label=element.get('label'),
        loads=[_loadOf(child, path) for child in element.findall('Load')],
        expanded=[_expandedOf(child, path)
                  for child in element.findall('Expanded')],
        selection=[_selectionOf(child, path)
                   for child in element.findall('Selection')])


def _loadOf(element, path):
    return QVizSessionLoad(
        ids=_attribute(element, 'ids', path, 'Load'),
        occurrence=_integer(element, 'occurrence', 0, path),
        slices=_slices(element, path))


def _expandedOf(element, path):
    # No occurrence means the branch of the IDS itself is open, occurrence 0
    # means the node under it is: an absent attribute cannot default to 0, or
    # the two stop being distinguishable and every IDS branch would come back
    # with its first occurrence unfolded.
    return QVizSessionExpanded(
        ids=_attribute(element, 'ids', path, 'Expanded'),
        occurrence=_integer(element, 'occurrence', None, path))


def _selectionOf(element, path):
    return QVizSessionSelection(
        path=_attribute(element, 'path', path, 'Selection'),
        occurrence=_integer(element, 'occurrence', 0, path))


def _figureOf(element, path):
    kind = _attribute(element, 'kind', path, 'Figure')
    if kind not in KINDS:
        raise ValueError('"%s" holds a <Figure kind="%s">: this application '
                         'draws %s.' % (path, kind, ' / '.join(KINDS)))
    _knownChildren(element,
                   ('Quantity', 'Cursors', 'View', 'Errors', 'Window'), path)
    return QVizSessionFigure(
        key=_attribute(element, 'key', path, 'Figure'),
        kind=kind,
        quantities=[_quantityOf(child, path)
                    for child in element.findall('Quantity')],
        axis=element.get('axis'),
        tensor=element.get('tensor') == '1',
        cursors=_cursorsOf(element.find('Cursors'), path),
        view=_viewOf(element.find('View'), path),
        errors=_errorsOf(element.find('Errors'), path),
        window=_windowOf(element.find('Window'), path))


def _quantityOf(element, path):
    row = _integer(element, 'row', None, path)
    column = _integer(element, 'column', None, path)
    if (row is None) != (column is None):
        raise ValueError('"%s" gives a <Quantity> half a place in the table: it '
                         'names %s without %s.'
                         % (path, 'row' if row is not None else 'column',
                            'column' if row is not None else 'row'))
    return QVizSessionQuantity(
        path=_attribute(element, 'path', path, 'Quantity'),
        occurrence=_integer(element, 'occurrence', 0, path),
        uri=element.get('uri'), row=row, column=column)


def _cursorsOf(element, path):
    """The band of sliders a figure had, and where each stood.

    An absent `<Cursor index>` is refused rather than defaulted: a slider whose
    index nobody set is the silent assumption this element exists to remove, and
    the index the tree stands on is not what the user left on screen.
    """
    if element is None:
        return None
    _knownChildren(element, ('Cursor',), path)
    cursors = []
    for child in element.findall('Cursor'):
        key = cursorKeyOf(_attribute(child, 'key', path, 'Cursor'), path)
        index = _integer(child, 'index', None, path)
        if index is None:
            raise ValueError('"%s" holds a <Cursor key="%s"> with no index: the '
                             'file says which axis to move and not where.'
                             % (path, cursorKeyText(key)))
        cursors.append(QVizSessionCursor(key=key, index=index))
    return QVizSessionCursors(folded=_flag(element, 'folded', path, 'Cursors'),
                              cursors=cursors)


def _viewOf(element, path):
    """The range a window was looking at.

    The four numbers go together or the element is refused: half a range is a
    range along one axis only, and pyqtgraph would then answer for the other one
    whatever the drawing chose -- which is the guess this file does not make.
    """
    if element is None:
        return None
    _knownChildren(element, (), path)
    numbers = {}
    for name in ('x0', 'x1', 'y0', 'y1'):
        if element.get(name) is None:
            raise ValueError('"%s" gives a <View> with no %s: a range names the '
                             'two ends of both axes.' % (path, name))
        numbers[name] = _number(element, name, path)
    return QVizSessionView(
        autoX=_flag(element, 'autoX', path, 'View', default=True),
        autoY=_flag(element, 'autoY', path, 'View', default=True),
        xInverted=_flag(element, 'xInverted', path, 'View'),
        yInverted=_flag(element, 'yInverted', path, 'View'), **numbers)


def _errorsOf(element, path):
    """Which of the three right-click lines the user had switched on."""
    if element is None:
        return None
    _knownChildren(element, (), path)
    word = element.get('bars')
    bars = None
    if word is not None:
        if word == BARS_ALL:
            bars = 1
        elif word.startswith(BARS_STEP):
            bars = _integer(element, 'bars', path=path, prefix=BARS_STEP)
            if bars < 1:
                raise ValueError('"%s" asks for %s%d: a slicing step of less '
                                 'than one sample is the whole curve, which '
                                 '%s already says.'
                                 % (path, BARS_STEP, bars, BARS_ALL))
        else:
            raise ValueError('"%s" asks for bars="%s": a session names %s, or '
                             '%sN with N the step between two bars.'
                             % (path, word, BARS_ALL, BARS_STEP))
    return QVizSessionErrors(bars=bars,
                             bands=_flag(element, 'bands', path, 'Errors'))


def _windowOf(element, path):
    """Where the window sat, maximized, hidden.

    The four numbers go together: three of them and `setGeometry` is asked for a
    size of none, which is what a `<Window>` missing its height would become --
    and that refusal would land in the restore, far from the line of the file
    that caused it.
    """
    if element is None:
        return None
    _knownChildren(element, (), path)
    place = {}
    for name in ('x', 'y', 'w', 'h'):
        if element.get(name) is None:
            raise ValueError('"%s" gives a <Window> with no %s: a place names '
                             'where the window sits and how big it is.'
                             % (path, name))
        place[name] = _integer(element, name, path=path)
    return QVizSessionWindow(
        maximized=_flag(element, 'maximized', path, 'Window'),
        hidden=_flag(element, 'hidden', path, 'Window'), **place)


def _slices(element, path):
    word = element.get('slices', FIRST)
    if word in SLICE_WORDS:
        return word
    if word.startswith(INDEX_PREFIX):
        _integer(element, 'slices', path=path, prefix=INDEX_PREFIX)
        return word
    raise ValueError('"%s" asks for slices "%s": a session names %s, or %sN with '
                     'N the index of the slice to keep.'
                     % (path, word, ' / '.join(SLICE_WORDS), INDEX_PREFIX))


def _knownChildren(element, allowed, path):
    """Refuse an element this format does not know, by name.

    A misspelled `<Selections>` used to be read as "no selection at all", which
    is how a session file comes back describing less than it says.
    """
    for child in element:
        if child.tag not in allowed:
            raise ValueError('"%s" holds a <%s> where this application expects '
                             '%s.' % (path, child.tag,
                                      ' / '.join('<%s>' % name
                                                 for name in allowed)))


def _attribute(element, name, path, tag):
    value = element.get(name)
    if value is None:
        raise ValueError('"%s" holds a <%s> with no %s: the session cannot be '
                         'restored without it.' % (path, tag, name))
    return value


def _integer(element, name, default=0, path=None, prefix=''):
    """An integer attribute, refused by naming the file and what it said."""
    text = element.get(name)
    if text is None:
        return default
    try:
        return int(text[len(prefix):] if prefix else text)
    except ValueError:
        raise ValueError('"%s" gives %s="%s", which is not a number.'
                         % (path, name, text))


def _number(element, name, path):
    """A float attribute -- an end of a range -- refused the same way."""
    text = element.get(name)
    try:
        return float(text)
    except (TypeError, ValueError):
        raise ValueError('"%s" gives %s="%s", which is not a number.'
                         % (path, name, text))


def _flag(element, name, path, tag, default=False):
    """A `0`/`1` attribute.

    A word is refused rather than read as truthy: `autoX="no"` answered True for
    any non-empty string, which is how a file that means "leave this axis alone"
    ends up pinning a range nobody asked for.
    """
    text = element.get(name)
    if text is None:
        return default
    if text == '1':
        return True
    if text == '0':
        return False
    raise ValueError('"%s" gives %s="%s" on a <%s>: this file writes 0 or 1 for '
                     'a yes or a no.' % (path, name, text, tag))


def _indent(element, level=0):
    """Line breaks and indentation, so a session stays readable by hand."""
    padding = '\n' + level * '  '
    if len(element):
        if not element.text or not element.text.strip():
            element.text = padding + '  '
        if not element.tail or not element.tail.strip():
            element.tail = padding
        for child in element:
            _indent(child, level + 1)
        if not element.tail or not element.tail.strip():
            element.tail = padding
    elif level and (not element.tail or not element.tail.strip()):
        element.tail = padding
