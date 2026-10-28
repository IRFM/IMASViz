# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""What a configuration file is, and what it may say.

The manual keeps two kinds of file under :file:`$HOME/.imasviz`: a node
selection (``.lsp``), which names quantities, and a plot configuration
(``.pcfg``), which names quantities and the place each panel held in the table.
That is what this class writes, and nothing else -- because a file has to say
what the application can put back on the screen, and the panels a Table Plot
View draws are made of a quantity and a place.

The files the previous writer produced are still read: they hold a
``PlotConfiguration`` root with one ``PlotItem`` per panel and a ``sourceInfo``
under it, and a ``SignalSelection`` root with one ``IDSPath`` per quantity. That
shape is not produced any more, for the reason the writer gave: it serialised
the pen, the fonts and the axis ranges of pyqtgraph objects, reading 23 keys off
``PlotDataItem.opts`` by name and calling ``QPen`` methods on whatever the pen
had become. Measured, the button wrote no file at all -- ``KeyError: 'name'`` on
this pyqtgraph, and with that key supplied by hand ``AttributeError: 'tuple'
object has no attribute 'brush'`` -- for a window of two panels as for one
holding a curve of 1642 points. And of whatever it did write, the reader kept
two attributes per panel: the path and the occurrence.

So the new file records the two attributes per panel the reader already used,
the row and column the old file carried and never read back (measured: a file
naming (0, 0) and (1, 1) laid its panels at (0, 0) and (0, 1)), and the abscissa
the window was drawn with -- which is what a saved window was, and was not in
the file: measured, a window drawn along time came back along ``rho_tor`` and
``theta_poloidal``, first abscissa values [0, 1, 2, 3] rather than the time
base. Styling an old file holds is counted and named by the commands that apply
it, not dropped in silence.

Reading is done by root element rather than by extension. The old reader asked
the file name: measured, the same XML named ``.xyz`` answered "no quantities"
without a word, and ``endswith('lsp')`` -- no dot -- took ``probe.notlsp`` for a
node selection. A file whose root is neither shape is refused by name, as is one
that is not well-formed XML: measured, a truncated file raised ``ParseError: no
element found: line 1, column 35`` out of the slot that was asked to apply it.
"""

import os
import xml.etree.ElementTree as ET
from collections import namedtuple

QVizQuantity = namedtuple('QVizQuantity', 'path occurrence row column uri')

PLOT = 'plot'
SELECTION = 'selection'
# The session file is a third kind of file kept in the same folder, with its own
# module for its own root element (`QVizSessionFile`). It is listed here because
# what this class owns is the folder, the extension and the guard on a name typed
# by hand -- not the shape of the XML.
SESSION = 'session'
EXTENSIONS = {PLOT: 'pcfg', SELECTION: 'lsp', SESSION: 'vsess'}

# The roots the previous writer produced, and still produces on users' disks.
LEGACY_ROOTS = {'PlotConfiguration': PLOT, 'SignalSelection': SELECTION}


class QVizConfigurationFile:
    """One configuration: its kind, the quantities it names, and its file."""

    VERSION = '1'

    def __init__(self, kind=PLOT, quantities=(), abscissa=None, path=None,
                 styledPanels=0, spellPathsAsDocumented=False):
        """
        Arguments:
            kind        (str) : PLOT or SELECTION.
            quantities  (list) : [QVizQuantity], in the order the window holds
                                 them -- which is the order they come back in.
            abscissa    (str) : the strategy the saved window drew with, for a
                                plot configuration; None leaves the choice to
                                whoever applies it.
            path        (str) : the file it was read from, or the one it is
                                written to.
            styledPanels (int) : how many panels of an old file hold styling
                                 that will not be put back.
            spellPathsAsDocumented (bool) : set when the file came from the old
                                 writer, whose paths were spelled with dots and
                                 brackets and turned into tree paths on the way
                                 in.
        """
        self.kind = kind
        self.quantities = list(quantities)
        self.abscissa = abscissa
        self.path = path
        self.styledPanels = styledPanels
        self.spellPathsAsDocumented = spellPathsAsDocumented

    # ---------------------------------------------------------------- names
    @staticmethod
    def directory():
        """The folder the manual tells the user about, made when first needed."""
        home = os.environ.get('HOME')
        if not home:
            raise ValueError('HOME is not set: there is no folder to keep '
                             'configurations in.')
        folder = os.path.join(home, '.imasviz')
        if not os.path.isdir(folder):
            os.makedirs(folder)
        return folder

    @staticmethod
    def extension(kind):
        if kind not in EXTENSIONS:
            raise ValueError('"%s" is not a configuration this application '
                             'knows: it writes %s.'
                             % (kind, ' and '.join(sorted('.' + extension
                                                          for extension
                                                          in EXTENSIONS.values()))))
        return '.' + EXTENSIONS[kind]

    @staticmethod
    def named(name, kind):
        """The path of the configuration a user just named.

        The name comes from a text field, so it is checked here rather than
        trusted: a name typed with the extension on it loses exactly that
        extension (measured on the old command, typing "probe.lsp" wrote
        ``probe..lsp`` because three characters were removed from a four
        character extension), and a name naming a directory is refused --
        measured, typing "../outside" wrote outside the configuration folder.
        """
        typed = (name or '').strip()
        suffix = QVizConfigurationFile.extension(kind)
        if typed.endswith(suffix):
            typed = typed[:-len(suffix)]
        if not typed:
            raise ValueError('A configuration needs a name.')
        if os.path.sep in typed or (os.path.altsep and os.path.altsep in typed) \
                or typed in ('.', '..'):
            raise ValueError('"%s" is not a configuration name: it names a '
                             'place, not a configuration. Use a plain name '
                             'inside %s.' % (name, QVizConfigurationFile.directory()))
        folder = QVizConfigurationFile.directory()
        path = os.path.join(folder, typed + suffix)
        if os.path.dirname(os.path.realpath(path)) != \
                os.path.realpath(folder):
            raise ValueError('"%s" would be written outside %s.'
                             % (name, folder))
        return path

    @staticmethod
    def listing(kind):
        """The names of that kind the folder holds, as the dialog lists them."""
        suffix = QVizConfigurationFile.extension(kind)
        return sorted(name for name in os.listdir(QVizConfigurationFile.directory())
                      if name.endswith(suffix))

    # --------------------------------------------------------------- reading
    @staticmethod
    def read(path):
        """The configuration a file holds, whatever shape it was written in."""
        try:
            root = ET.parse(path).getroot()
        except OSError as e:
            raise ValueError('Cannot read "%s": %s' % (path, e))
        except ET.ParseError as e:
            raise ValueError('"%s" is not a configuration file: it is not '
                             'well-formed XML (%s).' % (path, e))

        if root.tag == 'IMASVizConfiguration':
            return QVizConfigurationFile._readCurrent(root, path)
        if root.tag in LEGACY_ROOTS:
            return QVizConfigurationFile._readLegacy(root, path)
        raise ValueError('"%s" holds a <%s>: this application reads '
                         '<IMASVizConfiguration> files, and the '
                         '<PlotConfiguration>/<SignalSelection> files it wrote '
                         'before.' % (path, root.tag))

    @staticmethod
    def _readCurrent(root, path):
        kind = root.get('kind', PLOT)
        if kind not in EXTENSIONS:
            raise ValueError('"%s" declares kind "%s", which this application '
                             'does not write.' % (path, kind))
        quantities = []
        for element in root.findall('Quantity'):
            quantities.append(QVizQuantity(
                path=element.get('path'),
                occurrence=int(element.get('occurrence', 0)),
                row=_integer(element.get('row')),
                column=_integer(element.get('column')),
                uri=element.get('uri')))
        return QVizConfigurationFile(kind=kind, quantities=quantities,
                                     abscissa=root.get('abscissa'), path=path)

    @staticmethod
    def _readLegacy(root, path):
        """A file written before this format existed.

        The old writer spelled paths the way the data dictionary does -- dots
        and brackets -- and every caller turned them into tree paths on the way
        in; that conversion is kept here so those files keep working, and it is
        not applied to the new shape, which spells a path the way the tree does.
        """
        kind = LEGACY_ROOTS[root.tag]
        panels = root.findall('.//PlotItem') if kind == PLOT \
            else root.findall('.//IDSPath')
        quantities = []
        for panel in panels:
            source = panel.find('.//sourceInfo')
            where = panel if source is None else source
            row, column = _placeOf(panel)
            quantities.append(QVizQuantity(
                path=where.get('path'),
                occurrence=int(where.get('occurrence', 0)),
                row=row,
                column=column,
                uri=where.get('uri')))
        styled = len(root.findall('.//PlotDataItem/opts')) if kind == PLOT else 0
        return QVizConfigurationFile(kind=kind, quantities=quantities,
                                     path=path, styledPanels=styled,
                                     spellPathsAsDocumented=True)

    # -------------------------------------------------------------- writing
    def write(self, path=None):
        """Write the file: one element per quantity, and nothing else."""
        path = path if path is not None else self.path
        if path is None:
            raise ValueError('No file was named to write the configuration to.')
        root = ET.Element('IMASVizConfiguration')
        root.set('kind', self.kind)
        root.set('version', QVizConfigurationFile.VERSION)
        if self.abscissa is not None:
            root.set('abscissa', self.abscissa)
        for quantity in self.quantities:
            element = ET.SubElement(root, 'Quantity')
            element.set('path', quantity.path)
            element.set('occurrence', str(quantity.occurrence))
            if self.kind == PLOT:
                # A quantity with no place in the table is written without the
                # attributes, which is how the reader takes an absent place: the
                # string "None" is what `str(None)` gives, and reading this file
                # back answered `invalid literal for int() with base 10: 'None'`
                # -- and the entry then drew no panel at all, naming the file.
                if quantity.row is not None and quantity.column is not None:
                    element.set('row', str(quantity.row))
                    element.set('column', str(quantity.column))
            if quantity.uri:
                element.set('uri', quantity.uri)
        _indent(root)
        ET.ElementTree(root).write(path, encoding='utf-8',
                                   xml_declaration=True)
        self.path = path
        return path

    def remove(self):
        """Delete the file this configuration was read from or written to."""
        if self.path is None:
            raise ValueError('No file was named to remove.')
        try:
            os.remove(self.path)
        except OSError as e:
            raise ValueError('Cannot remove "%s": %s' % (self.path, e))
        return self.path

    # ------------------------------------------------------------ resolving
    def treePaths(self):
        """The paths as the tree spells them, whatever the file spelled."""
        if not self.spellPathsAsDocumented:
            return [quantity.path for quantity in self.quantities]
        from imasviz.VizUtils import QVizGlobalOperations
        return QVizGlobalOperations.makeIMASPaths(
            [quantity.path for quantity in self.quantities])


def _integer(text):
    return None if text is None else int(text)


def _placeOf(panel):
    """Where an old file said a panel sat: attributes, or the key it wrote."""
    row, column = _integer(panel.get('row')), _integer(panel.get('column'))
    if row is None or column is None:
        key = (panel.get('key') or '').strip('() ')
        if ',' in key:
            first, second = key.split(',', 1)
            row, column = _integer(first.strip()), _integer(second.strip())
    return row, column


def _indent(element, level=0):
    """Line breaks and indentation, so a configuration stays readable by hand."""
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
