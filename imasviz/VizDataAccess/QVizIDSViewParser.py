# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

"""Builds the data tree shadow structure from Access Layer dictionary reflection.

This class replaces the per-data-dictionary parsers that used to be generated as
Python source from IDSDef_<version>.xml. The data dictionary is walked once at
run time through imas IDSMetadata, and the runtime IDS object supplies the array
of structures lengths and the 0D values. The element attributes produced here
are the contract consumed by QVizDataTreeViewBuilder and QVizTreeNode.
"""

import logging
import re
import xml.etree.ElementTree as ET

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from imasviz.VizDataAccess.QVizAccessLayerHLI import IDSDataType
from imasviz.VizDataAccess.QVizAxesSpec import isUnboundedCoordinate
from imasviz.VizDataAccess.VizTimeSlices import FIRST_SLICE
from imasviz.VizGUI.VizTreeView.QVizResultEvent import QVizResultEvent
from imasviz.VizUtils import QVizGlobalOperations, QVizGlobalValues, QVizPreferences


def itimeIndexFromPathDoc(pathDoc):
    """Index of the AOS level the time index belongs to, -1 when there is none.

    Kept as the code generator derived it, including its early return on the
    first missing (iN): the tree structure downstream depends on it.
    """
    if not pathDoc:
        return -1
    position = pathDoc.find('(itime)')
    if position == -1:
        return -1

    prefix = pathDoc[0:position]
    itimePosition = 0
    for level in range(1, 10):
        if ('(i' + str(level) + ')') in prefix:
            itimePosition += 1
        else:
            return itimePosition
    return itimePosition


def dataTypeName(metaData):
    """Restores the data dictionary spelling of a node type.

    IDSMetadata normalizes the type into an enum plus a rank, while the view
    builder selects on the original spelling (data_type.startswith('FLT_')).
    """
    name = metaData.data_type.value
    if name in ('structure', 'struct_array'):
        return name
    return name + '_' + str(metaData.ndim) + 'D'


def cleanDocumentation(documentation):
    """One-line rendering of the data dictionary documentation.

    The generated parsers embedded the text in a single-quoted literal and
    doubled every single quote to do so; the view then displayed those doubled
    quotes. Assigning the attribute directly drops the artefact.
    """
    return documentation.replace('&#34;', '"').replace('\n', '')


def metadataForPath(rootMetaData, segments):
    """Descends the dictionary by child name.

    IDSMetadata item lookup rejects the relative spelling the coordinates use,
    while child iteration always works, which is what the walk relies on.
    """
    metaData = rootMetaData
    for segment in segments:
        for child in metaData:
            if child.name == segment:
                metaData = child
                break
        else:
            return None
    return metaData


def structureCoordinates(metaData):
    """The coordinates a structure declares for the arrays it holds.

    IDSMetadata leaves .coordinates empty on a structure and answers the
    declaration on coordinate1 / coordinate2 attributes instead, so a walk that
    reads only .coordinates never sees it. hard_x_rays.channel[i1].radiance
    declares (channel(i1)/energy_band, channel(i1)/radiance/time) and its array
    spells (1..N, channel(i1)/radiance/time): the leaf keeps the axis it shares
    and leaves the other one anonymous, and the name of the anonymous one is
    here and nowhere else on the leaf.

    Trailing blanks end the declaration: what a structure spells is how many
    dimensions it describes arrays for, which is what makes the declaration
    usable or not for a given leaf -- see inheritCoordinates.
    """
    declared = []
    for number in range(1, 7):
        spelling = getattr(metaData, 'coordinate%d' % number, None)
        if spelling is None or not str(spelling):
            break
        declared.append(str(spelling))
    return declared


def inheritCoordinates(own, donors):
    """Fills the anonymous dimensions of a leaf from the structures around it.

    A declaration only describes the leaf if it counts as many dimensions as the
    leaf has: radiance declares two coordinates and holds both a 2D 'data' and a
    1D 'time', so handing 'time' the first of the two calls a time axis an energy
    band. On the 3.35.0 dictionary the two counts agree for 1 570 dimensions and
    disagree for 7 556, and only the first set is carried over.

    The closest declaration wins each dimension, and a further structure may
    still name one the closest one left blank. A declaration naming no node
    ('1..N', '1..9') is carried over as well: it names nothing, but it is what
    the dictionary says about that axis.
    """
    filled = list(own)
    for donor in donors:
        if len(donor) != len(own):
            continue
        for position, spelling in enumerate(donor):
            if not spelling:
                continue
            if filled[position] and not isUnboundedCoordinate(filled[position]):
                continue
            filled[position] = spelling
    return filled


def coordinateSegments(coordinate):
    """Splits a data dictionary coordinate into the names to descend through.

    A coordinate is a path whose steps may each carry a parenthesised name:
    'time_slice(itime)/profiles_1d/psi' descends through time_slice,
    profiles_1d and psi. A parenthesised index placeholder (itime, i1, ...)
    names no node, and the unbounded '1..N' spelling names nothing at all.

    The same coordinate reaches this helper spelled two ways. The shadow tree
    keeps the dictionary's slashes; the tree node carries the form
    buildNamedDataElement wrote after replacing every '/' with a '.', where the
    steps after a closing parenthesis are no longer separated -- cutting
    'time_slice(itime).grid.dim1' on slashes alone yields an 'itime)' step and
    drops the rest of the path.
    """
    segments = []
    for step in str(coordinate).split('/'):
        name, _, rest = step.partition('(')
        segments.extend(part for part in name.split('.') if part)
        if not rest:
            continue
        inside, _, tail = rest.partition(')')
        if inside and not re.fullmatch(r'i(time|[0-9]+)', inside):
            segments.extend(part for part in inside.split('.') if part)
        segments.extend(part for part in tail.lstrip('.').split('.') if part)
    return segments


class QVizIDSViewParser(QThread):
    """Walks one IDS occurrence and returns the shadow tree the view builds on.

    The constructor signature, setProgressBar() and run() are the contract the
    data sources rely on: they build the parser, assign .dataSource, then call
    .start() (or .run() when synchronous).
    """

    def __init__(self, uri, view, IDSName, occurrence=0,
                 sliceSelection=None, asynch=True):
        super(QVizIDSViewParser, self).__init__()
        self.occurrence = occurrence
        self.view = view
        self.dataSource = None
        self.idsName = IDSName
        self.view.IDSNameSelected[occurrence] = IDSName
        self.sliceSelection = sliceSelection
        self.asynch = asynch
        self.progressBar = None
        self.ggd_warning_done = 0
        # Whether the walk met a dynamic array of structures, which is what
        # makes an occurrence worth viewing more than once. The view asks the
        # shadow tree, not the slice choice: measured, the flag the old menu
        # gate read was set only in the branch of the fourth choice, so three
        # of the four slice choices left the "Add a new view" entry unreachable.
        self.sawDynamicArrays = False
        # Index currently visited, and length, for each enclosing array of
        # structures: position 0 is the outermost one (loop variable 'i').
        self.indexStack = []
        self.maxStack = []
        # Coordinate spelling -> dictionary node, for the IDS being walked.
        # Set up in loadIDS, where the root metadata is known.
        self._coordinateMetaData = {}
        # How many times the dictionary was actually descended, for the test
        # that keeps the walk from growing with the node count.
        self.metadataDescents = 0
        # Coordinates declared by the structures currently being walked,
        # outermost first. A leaf spells the axes it shares with its siblings
        # and leaves the others anonymous; the name of an anonymous one lives on
        # the structure, so the walk has to remember it on the way down.
        self._structureCoordinates = []

    def setProgressBar(self, progressBar):
        self.progressBar = progressBar

    def run(self):
        try:
            idsData, ids_instance = self.loadIDS(self.idsName, self.occurrence)
            if self.asynch:
                QApplication.postEvent(self.view.parent,
                                       QVizResultEvent((self.idsName, ids_instance,
                                                        self.occurrence, idsData,
                                                        self.progressBar,
                                                        self.sliceSelection, self),
                                                       self.view.parent.eventResultId), 1)
            else:
                self.view.updateView(self.idsName, ids_instance, self.occurrence,
                                     idsData, self.sliceSelection)
                self.closeProgressBar()
        except AttributeError as attributeError:
            # What the walk met, with the frames that show where. The sentence
            # that used to follow it -- 'the data dictionary of the data entry
            # does not match the fields IMASViz expects' -- was a diagnosis this
            # code cannot make: measured, the branch was reached because a read
            # had been refused for a data-dictionary major version, and the
            # answer named something else entirely.
            logging.getLogger(self.dataSource.uri).error(attributeError, exc_info=True)
        except ValueError as valueError:
            # A slice index the IDS does not hold, or a selection left without
            # an index: said as the sentence the object raises, without the
            # traceback the generic branch below adds to everything else.
            logging.getLogger(self.dataSource.uri).error(valueError)
        except Exception as exception:
            logging.getLogger(self.dataSource.uri).error(exception, exc_info=True)
        # Every failure path used to take the bar down right here. Asynchronously
        # that is the walk's own thread asking for a window to be closed, and it
        # never comes back: measured, with no case and no IMAS in it, the thread
        # stayed inside `QWindow::close()` past a 20 s watchdog while the GUI
        # thread pumped events -- the walk thread is lost, `finished` is never
        # emitted, the parser is never dropped, the occurrence stays in
        # `loadsInProgress` for the rest of the session, and every later request
        # for it is refused as already being loaded. So the walk says what it met
        # and leaves the window to the thread that made it.
        if not self.asynch:
            self.closeProgressBar()

    def closeProgressBar(self):
        """Take the bar of this load down.

        `hide()` left it alive: the source built a new one for every load, so a
        session that loaded a dozen IDSs kept a dozen closed-but-live windows.

        Only a thread that owns the widget may call this. Synchronously that is
        the caller, which is the thread that made the bar; asynchronously it is
        the source when the walk ends, or the frame once it has drawn the tree.
        """
        if self.progressBar is not None:
            self.progressBar.close()

    def loadIDS(self, IDSName, occurrence):
        """Walks one IDS occurrence, holding a reference on the case for the
        duration of the walk.

        The reference goes back whatever the walk does: run() only logs what is
        raised in here, and a reference left behind would keep the case open,
        and the IDSs loaded from it, for the rest of the session.
        """
        self.dataSource.open()
        try:
            idsInstance = self.dataSource.get(IDSName, occurrence)

            # Coordinates are named relative to the IDS root, so resolving their
            # units needs the root metadata, not the metadata of the current branch.
            self.rootMetaData = idsInstance.metadata
            # Resolutions belong to this IDS: a new root invalidates them.
            self._coordinateMetaData = {}
            self._structureCoordinates = []
            self.metadataDescents = 0
            self.sawDynamicArrays = False

            root = ET.Element(IDSName)
            parents = [root]
            self.walkIDS(idsInstance.metadata, idsInstance, root, parents, IDSName, 1)
            # What the walk met, carried on the shadow tree the view builds on:
            # an occurrence of an IDS with a dynamic array can be looked at more
            # than once, and the view says so on the strength of this rather
            # than of the slice choice that happened to be asked for.
            root.set('dynamic_arrays', '1' if self.sawDynamicArrays else '0')
            return (root, idsInstance)
        finally:
            self.dataSource.close()

    def coordinateMetaData(self, coordinate):
        """The dictionary node a coordinate names, resolved once per spelling.

        The same spelling repeats for every element of an array of structures:
        walking equilibrium occurrence 0 with the GGD structures kept descended
        the dictionary 84 708 times for 16 distinct coordinate spellings. A
        spelling that resolves to nothing is cached as well, so the unbounded
        '1..N' ones stop costing after the first.
        """
        key = str(coordinate)
        if key not in self._coordinateMetaData:
            self.metadataDescents += 1
            self._coordinateMetaData[key] = metadataForPath(
                self.rootMetaData, coordinateSegments(key))
        return self._coordinateMetaData[key]

    def walkIDS(self, metaData, idsObject, parent, parents, pathText, level):
        """Walks one dictionary level, mirroring the shadow tree of the parsers.

        pathText keeps the parametrized path with the literal loop placeholders
        ([i], [j], ...) the view evaluates later; counters and maxes carry the
        array-of-structures indexes actually visited.
        """
        for childMeta in metaData:
            name = childMeta.name
            dataType = childMeta.data_type

            if dataType is IDSDataType.STRUCTURE:
                element = ET.SubElement(parent, name)
                element.text = pathText + '.' + name
                parents.append(element)
                self.setCommonAttributes(element, childMeta, 'structure')
                self._structureCoordinates.append(structureCoordinates(childMeta))
                self.walkIDS(childMeta, self.childOf(idsObject, name), element,
                             parents, pathText + '.' + name, level)
                self._structureCoordinates.pop()
                parents.pop()
                parent = parents[-1]

            elif dataType is IDSDataType.STRUCT_ARRAY:
                if self.ignoreGGD(name):
                    continue
                runtime = self.childOf(idsObject, name)
                length = len(runtime) if runtime is not None else 0
                minLimit, maxLimit, step = self.slicing(childMeta, length)
                indexVar = QVizGlobalValues.indices[str(level)]
                while len(self.indexStack) < level:
                    self.indexStack.append(0)
                    self.maxStack.append(0)
                self.maxStack[level - 1] = length
                for index in range(minLimit, maxLimit, step):
                    self.indexStack[level - 1] = index
                    element = ET.SubElement(parent, name)
                    element.text = pathText + '.' + name + '[' + indexVar + ']'
                    parents.append(element)
                    element.set('index', str(index))
                    element.set('dim', str(length))
                    self.setCommonAttributes(element, childMeta, 'struct_array')
                    self.walkIDS(childMeta, self.elementOf(runtime, index), element,
                                 parents, pathText + '.' + name + '[' + indexVar + ']',
                                 level + 1)
                    parents.pop()
                    parent = parents[-1]

            else:
                self.buildLeaf(parent, childMeta, idsObject, pathText, level, dataType)

    def buildLeaf(self, parent, childMeta, idsObject, pathText, level, dataType):
        name = childMeta.name
        spelling = dataTypeName(childMeta)

        if childMeta.ndim == 0:
            content = self.scalarContent(self.childOf(idsObject, name))
            element = ET.SubElement(parent, name + '=' + content)
            element.set('content', content)
        else:
            element = ET.SubElement(parent, name)

        # The element text carries the accumulated data path. QVizDataTreeViewBuilder
        # builds every tree item name from it (tag + '=' + text), so leaving it out
        # strips the path suffix from the whole shot view. The loop placeholders
        # ([i], [j], ...) stay unsubstituted here, as the generated parsers left them.
        element.text = pathText + '.' + name

        self.setCommonAttributes(element, childMeta, spelling)

        pathDoc = childMeta.path_doc
        itimeIndex = itimeIndexFromPathDoc(pathDoc)
        element.set('itime_index', str(itimeIndex))
        element.set('type', getattr(childMeta.type, 'value', str(childMeta.type)))

        element.set('path_doc', pathDoc if pathDoc is not None else '')

        # A leaf spells the axes it shares with its siblings and writes 1..N for
        # the ones it does not; the name of those lives on the structure that
        # holds it. The closest declaration wins each dimension.
        ownCoordinates = [str(coordinate) for coordinate in childMeta.coordinates]
        coordinates = inheritCoordinates(ownCoordinates,
                                         reversed(self._structureCoordinates))

        for dimension in range(childMeta.ndim):
            number = str(dimension + 1)
            coordinate = coordinates[dimension] if dimension < len(coordinates) else ''
            if not coordinate:
                continue
            element.set('coordinate' + number,
                        QVizGlobalOperations.makeIMASPath(coordinate))

            # The view builds axis labels from the coordinate; its unit comes
            # from the dictionary node it names, which was never carried over
            # before, leaving every non-time axis without an unit.
            coordinateMetaData = self.coordinateMetaData(coordinate)
            if coordinateMetaData is not None and coordinateMetaData.units:
                element.set('coordinate' + number + '_units',
                            coordinateMetaData.units)

            sameAs = getattr(childMeta, 'coordinates_same_as', None)
            if sameAs and str(sameAs[dimension]):
                element.set('coordinate' + number + '_same_as',
                            QVizGlobalOperations.makeIMASPath(str(sameAs[dimension])))

        nameNode = ET.SubElement(element, 'name')
        nameNode.set('data_type', 'STR_0D')
        nameNode.text = self.renderPath(pathText + '.' + name)

        parametrizedPath = pathText
        if itimeIndex != -1:
            parametrizedPath = parametrizedPath.replace(
                '[' + QVizGlobalValues.indices[str(itimeIndex + 1)] + ']', '[itime]')
        element.set('parametrizedPath', parametrizedPath)

        for enclosing in range(0, level - 1):
            element.set(QVizGlobalValues.indices[str(enclosing + 1)],
                        str(self.indexStack[enclosing]))
            element.set(QVizGlobalValues.max_indices[str(enclosing + 1)],
                        str(self.maxStack[enclosing]))

        element.set('aos_parents_count', str(level - 1))

    def setCommonAttributes(self, element, childMeta, spelling):
        if childMeta.units:
            element.set('units', childMeta.units)
        documentation = childMeta.documentation
        if documentation is not None:
            element.set('documentation', cleanDocumentation(documentation))
        element.set('name', childMeta.name)
        element.set('data_type', spelling)
        lifecycleStatus = getattr(childMeta, 'lifecycle_status', None)
        if lifecycleStatus is not None:
            element.set('lifecycle_status', lifecycleStatus)

    def slicing(self, childMeta, length):
        """Which elements of a dynamic array of structures this view keeps.

        The choice is an object that knows the window it wants out of an array of
        `length` elements; nothing here compares a name to a number. Measured on
        the reference case, the old code compared the identifier of the choice to
        the literals 1, 2 and 4, turned any name it did not recognise into 1 in
        silence, and refused an index past the end four seconds into the walk.
        Meeting a dynamic array is recorded on the walk, which is what tells the
        view that this occurrence can be looked at more than once.
        """
        if not childMeta.type.is_dynamic:
            return 0, length, 1
        self.sawDynamicArrays = True
        selection = FIRST_SLICE if self.sliceSelection is None else self.sliceSelection
        try:
            return selection.window(length)
        except ValueError as error:
            # Named for the array it is about: one IDS can hold several dynamic
            # arrays and the choice is a single index for all of them, so the
            # refusal says which one cannot take it -- measured, equilibrium
            # occurrence 0 holds 49 time_slice and 1 grids_ggd.
            raise ValueError('%s: %s' % (childMeta.name, error))

    def ignoreGGD(self, name):
        if QVizPreferences.Ignore_GGD == 0:
            return False
        if name == 'ggd' or name.startswith('ggd_') or name.endswith('_ggd'):
            if self.ggd_warning_done == 0:
                self.ggd_warning_done = 1
                logging.getLogger(self.dataSource.uri).warning(
                    'GGD structures have been ignored')
                logging.getLogger(self.dataSource.uri).warning(
                    'Enable GGD structures parsing using a user preferences file. '
                    'See Viz documentation for details, 2.9. Setting user preferences.')
            return True
        return False

    @staticmethod
    def childOf(idsObject, name):
        if idsObject is None:
            return None
        try:
            return getattr(idsObject, name)
        except (AttributeError, KeyError):
            return None

    @staticmethod
    def scalarContent(value):
        """A 0D value as the text the tree can carry.

        The Access Layer wraps every scalar in an object of its own. Keeping that
        object in the element makes the shadow tree impossible to serialise --
        ElementTree refuses an attribute that is not text, and on the reference
        case that is every scalar of the IDSs walked, 3 620 of them across tf,
        equilibrium and core_profiles -- and it is also what the documentation
        panel ends up showing for a scalar, where the wrapper says nothing about
        the value. The plain Python value sits under .value; a string arrives as
        bytes on some back ends.
        """
        if value is None:
            return ''
        plain = getattr(value, 'value', value)
        if isinstance(plain, bytes):
            return plain.decode('utf-8', 'replace')
        return str(plain)

    @staticmethod
    def elementOf(array, index):
        if array is None:
            return None
        try:
            return array[index]
        except (IndexError, TypeError):
            return None

    def renderPath(self, pathText):
        """Replaces the loop placeholders by the indexes actually visited.

        The brackets stay: this text is the `dataName` the shot view evaluates
        against the IDS instance it holds -- `QVizTreeNode.updateStyle` reads the
        value this way -- and an index written without them asks the runtime for
        an attribute named `time_slice0`. Measured on the reference case, loading
        `equilibrium` occurrence 0 into a shot view raised `AttributeError: IDS
        structure '' has no attribute 'time_slice0'` from that evaluation, so no
        occurrence of a dynamic IDS could be displayed at all. With the brackets
        the same string is also the IMAS path spelling the rest of the app uses:
        `makeIMASPath` turns it into `equilibrium/time_slice(0)/...`.
        """
        rendered = pathText
        for level, index in enumerate(self.indexStack):
            rendered = rendered.replace(
                '[' + QVizGlobalValues.indices[str(level + 1)] + ']',
                '[' + str(index) + ']')
        return rendered
