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
QVizSessionFigure = namedtuple('QVizSessionFigure',
                               'key kind quantities axis tensor')
QVizSessionCase = namedtuple('QVizSessionCase',
                             'uri dd_version label loads expanded selection')

ROOT = 'IMASVizSession'
VERSION = '1'

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
        if version != VERSION:
            raise ValueError('"%s" declares session version "%s", which this '
                             'application cannot read: it writes version %s.'
                             % (path, version, VERSION))
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
        _indent(root)
        ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
        self.path = path
        return path

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
    return QVizSessionFigure(
        key=_attribute(element, 'key', path, 'Figure'),
        kind=kind,
        quantities=[_quantityOf(child, path)
                    for child in element.findall('Quantity')],
        axis=element.get('axis'),
        tensor=element.get('tensor') == '1')


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
