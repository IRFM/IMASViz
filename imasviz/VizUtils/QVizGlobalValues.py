
# Copyright holders : Commissariat à l’Energie Atomique et aux Energies Alternatives (CEA), France;
# and Laboratory for Engineering Design - LECAD, University of Ljubljana, Slovenia
# CEA and LECAD authorize the use of the METIS software under the CeCILL-C open source license https://cecill.info/licences/Licence_CeCILL-C_V1-en.html
# The terms and conditions of the CeCILL-C license are deemed to be accepted upon downloading the software and/or exercising any of the rights granted under the CeCILL-C license.

# ****************************************************
#     Authors L. Fleury, X. Li, D. Penko
# ****************************************************

import os
import sys
import logging
from PySide6 import QtGui


class FigureTypes:
    TABLEPLOTTYPE = "TablePlotView:"
    STACKEDPLOTTYPE = "StackedPlotView:"
    PROFILESPLOTTYPE = "PlotView:"
    # The frames drawn through the axes model keep their own prefixes: the
    # "add to this figure" entries build their curves through another path and
    # would be handed a frame they do not know how to fill. Separate namespace,
    # same registry. Two prefixes died with the frames that produced them: the
    # legacy image frame's "Image:", and the "Figure:" one the legacy widget
    # handed out. A second namespace for one kind of window is two *Windows* menu
    # entries and one window the "add to" entries cannot fill; a namespace with
    # no frame left behind it is a *Windows* menu group that can never be filled.
    CURVEPLOTTYPE = "SlicesPlot"
    IMAGEPLOTTYPE = "SlicesImage"
    # The window the Equilibrium plugin builds is a figure like the others: it is
    # registered in `figureframes`, so the *Windows* menu and its *Delete*
    # sub-menu reach it. It is not drawn through the axes model, so it keeps its own prefix and registers no
    # node in `figToNodes` -- the "add this quantity to that figure" entries walk
    # that record and could not fill a matplotlib window.
    EQUILIBRIUMPLOTTYPE = "EquiPlotView:"

    # Every kind of figure the commands can draw, in menu order: the label the
    # user reads (it is the prefix the window title shows), the icon named in
    # GlobalIcons, and the prefix its key carries. The *Windows* menu and its
    # *Delete* sub-menu iterate this, because a kind missing here is a window the user has
    # no way left to close -- and a kind listed here that no command draws any
    # more is a sub-menu that can never be filled.
    MENU_ORDER = (('TablePlotView', 'TPV', TABLEPLOTTYPE),
                  ('StackedPlotView', 'SPV', STACKEDPLOTTYPE),
                  ('Profiles', 'Profiles', PROFILESPLOTTYPE),
                  ('SlicesPlot', 'Figure', CURVEPLOTTYPE),
                  ('SlicesImage', 'Image', IMAGEPLOTTYPE),
                  ('Equilibrium', 'Figure', EQUILIBRIUMPLOTTYPE))

class UserInputs:
    inputs = None
    enable = False
    def setUserInputs(self, userInputs):
        UserInputs.inputs = userInputs

class Imas_Viz_Options:

    HIDE_EMPTY_SIGNALS = False
    HIDE_OBSOLESCENT_NODES = False


class PlotTypes:
    STACKED_PLOT = "STACKED_PLOT"
    TABLE_PLOT = "TABLE_PLOT"
    SIMPLE_PLOT = "SIMPLE_PLOT"
    PREVIEW_PLOT = "PREVIEW_PLOT"


class GlobalColors:
    """The colours the *interface* is painted with -- tree text, selection, the
    documentation panel -- through the preferences file.

    The eighteen `*_HEX` strings this class used to carry existed for one
    consumer: `getRGBColorList()`, which walked `GlobalColors.__dict__` to build
    the list a curve was drawn with, blue first because that walk happened to put
    `BLUE_HEX` first. Nothing draws a curve from this class any more -- a curve
    asks `QVizCurveColors`, which names its colours and picks them against the
    ground the window paints -- so the hex table and the walk are gone.
    """
    from PySide6.QtGui import QBrush, QColor

    BLUE = QBrush(QColor('#0000ff'))
    RED = QBrush(QColor('#ff0000'))
    BLACK = QBrush(QColor('#000000'))
    CYAN = QBrush(QColor('#00ffff'))
    LIGHT_CYAN = QBrush(QColor('#cce5ff'))
    LIGHT_GREY = QBrush(QColor('#d3d3d3'))

    def getAvailableColorForNodes(index):
        availableColors = []
        availableColors.append(GlobalColors.BLUE)
        availableColors.append(GlobalColors.RED)
        availableColors.append(GlobalColors.BLACK)
        availableColors.append(GlobalColors.CYAN)
        availableColors.append(GlobalColors.LIGHT_CYAN)
        availableColors.append(GlobalColors.LIGHT_GREY)
        return availableColors[index]


class QVizPreferences:

    userPreferencesInitialized = False
    SelectionColor = None
    ColorOfNodesContainingData = None
    Allow_data_to_be_plotted_with_different_units = 0
    Ignore_GGD = 1
    # Whether IMASViz writes the session it is closed with -- and offers it back
    # at the next start. Off: a run that ends leaves nothing behind on the disk,
    # and the next run asks nothing. The *File* menu saves whenever asked.
    Auto_save_session = 0
    Show_only_tensors_rank_ge_1 = 0
    # Which of the two themes the application is dressed with -- see
    # ``VizGUI/VizGuiCustomization/QVizStyle.py``, which holds both palettes and
    # is what refuses a name it does not wear. Light is the default: the tool is
    # used on a desktop in a lit room, and it is what the manual's screenshots
    # were taken on.
    Theme = 'light'
    # What the box in the corner of a window title bar is worth. Off (the
    # default): it takes the window off the screen and keeps it -- the *Windows*
    # menu still names it, unchecked, and clicking the line puts it back. On: it
    # closes the window for good, out of the bookkeeping and out of the session.
    # Hiding is the default because a figure costs a read of the case to redraw,
    # and the box is where a user reaches for "get this out of my way" far more
    # often than for "throw it away".
    Close_button_deletes = 0
    # How the MDI area lays its windows out -- windows, tabs, a tile grid, or a
    # cascade -- answered by the *Disposition* sub-menu of the *Windows* menu,
    # and read back at start-up to lay the area the first case is opened on.
    # Windowed is the default, and the only state the area opens in when no
    # choice is read: a pile of titled windows is the state a case is opened
    # into, and a line nobody wrote keeps the case where it was.
    Mdi_view_mode = 'windowed'
    LAYOUT_MODES = ('windowed', 'tabbed', 'tiled', 'cascaded')
    # The start window's list of local cases: which field it is laid out by,
    # in which sense, and which of the two protocols it shows. The field is one
    # of SORT_KEYS -- the user picks it with the *Trier par* box, and the arrow
    # beside it its sense -- and, whatever key is chosen, the cases are already
    # read in the order database, backend, shot, run, so an unchosen key answers
    # that order rather than nothing. The defaults are ``database`` and
    # ``asc`` -- the field the list used to be laid out by and the sense the
    # scanner spells it in -- so a run that has never chosen a sort sees the
    # list as it always was, with only shot and run read as numbers where they
    # used to read as words (12 before 999, not 999 before 54924... the point is
    # the number, in the number's order).
    Uri_list_sort_key = 'database'
    SORT_KEYS = ('uri', 'database', 'backend', 'shot', 'run')
    Uri_list_sort_direction = 'asc'
    SORT_DIRECTIONS = ('asc', 'desc')
    # Both on by default: a case a user holds locally is a case they expect to
    # see, and hiding half of them is a choice the user makes at the two boxes,
    # not a state the list starts in. They cannot both be read as off -- the
    # list is *which kind of case to open*, and an empty one is a place to look
    # at that shows nothing, so the selector refuses to uncheck the last one.
    # ``Uri_list_filter_MDSplus`` carries ``MDS+`` by a name Python allows in an
    # identifier, and the file line spells that same name -- ``MDSplus``, like
    # the identifiers the rest of this file keys on -- never the ``+``.
    Uri_list_filter_HDF5 = 1
    Uri_list_filter_MDSplus = 1

    def persist(**options):
        """Write `options` (``key`` -> ``value``) into the user preferences file.

        The file is ``$HOME/.imasviz/preferences`` -- the same one `build` reads --
        and a line that is not in `options` is left exactly where it was, in the
        order it was in. The file is created, with its folder, when neither
        exists yet: a fresh installation holds no preferences, and the first
        choice a user makes at the selector's sort box or protocol checkboxes
        has to land in one without the user creating it by hand. Each value is
        written as text; the reader (`build`) is what turns it back into the
        type it asks for, so a line this writer spells is a line that reader
        reads -- and the round trip is what the tests check.
        """
        home = os.environ.get('HOME', os.getcwd())
        folder = os.path.join(home, '.imasviz')
        path = os.path.join(folder, 'preferences')
        old = []
        if os.path.exists(path):
            with open(path) as f:
                old = list(f)
        new = []
        for line in old:
            if '=' in line and line.split('=', 1)[0].strip() in options:
                continue          # replaced below, where the option was asked
            new.append(line)
        for key, value in options.items():
            new.append('%s=%s\n' % (key, value))
        os.makedirs(folder, exist_ok=True)
        with open(path, 'w') as f:
            f.writelines(new)

    def sortKey(text):
        """Which field the list is laid out by, refusing a word it does not sort on.

        What the *Trier par* box offers is ``SORT_KEYS``; a file that names a
        field it does not offer is refused by the name it wrote, and the list
        keeps the field it was holding -- the same "the line answers for itself"
        rule `build` has always applied, so one bad line costs its own option
        and nothing else changes.
        """
        asked = text.strip().lower()
        if asked not in QVizPreferences.SORT_KEYS:
            raise ValueError(
                '%r is not a field the case list sorts by: write %s'
                % (text.strip(),
                   ' or '.join(repr(one) for one in QVizPreferences.SORT_KEYS)))
        return asked

    def sortDirection(text):
        """Which sense the list is laid out in, refusing a sense it does not turn.

        ``asc`` puts the first before the last, ``desc`` the reverse; anything
        else is a word the arrow does not spell, refused by it, and the list
        keeps the sense it was holding.
        """
        asked = text.strip().lower()
        if asked not in QVizPreferences.SORT_DIRECTIONS:
            raise ValueError(
                '%r is not a sort sense: write %s'
                % (text.strip(),
                   ' or '.join(repr(one) for one in QVizPreferences.SORT_DIRECTIONS)))
        return asked

    def colour(text):
        """One of the two colour options, read as the manual writes it.

        The manual says ``Nodes_selection_colour=#ff0000``; the reader took an
        index into the six ``GlobalColors`` brushes with ``int(text) - 1``, so
        the file the manual tells the user to write answered ``ValueError`` --
        and ``build()`` is called by ``QtVIZ_GUI.main()`` with nothing around
        it, which stopped the application before a window appeared. Both
        spellings are read here, and a third one (a Qt colour name) comes along
        for free; what neither spelling can mean is named, not raised.
        """
        from PySide6.QtGui import QBrush, QColor

        asked = text.strip()
        if asked.isdigit():
            if not 1 <= int(asked) <= 6:
                raise ValueError('%r is not one of the six colours: number one '
                                 'from 1 to 6, or write it as #rrggbb' % asked)
            return GlobalColors.getAvailableColorForNodes(int(asked) - 1)
        hexed = asked if asked.startswith('#') else '#' + asked
        colour = QColor(hexed) if len(hexed) in (4, 5, 7, 9) else QColor(asked)
        if not colour.isValid():
            raise ValueError('%r is not a colour: write it as #rrggbb, or number '
                             'one of the six from 1 to 6' % asked)
        return QBrush(colour)

    def build(self):
        if not QVizPreferences.userPreferencesInitialized:
            QVizPreferences.ColorOfNodesContainingData = GlobalColors.BLUE
            QVizPreferences.SelectionColor = GlobalColors.RED
            option1 = "Colour_of_data_nodes_containing_data="
            option2 = "Nodes_selection_colour="
            option3 = "Allow_data_to_be_plotted_with_different_units="
            option4 = "Ignore_GGD="
            option5 = "Auto_save_session="
            option6 = "Theme="
            option7 = "Show_only_tensors_rank_ge_1="
            option8 = "Close_button_deletes="
            option9 = "Mdi_view_mode="
            option10 = "Uri_list_sort_key="
            option11 = "Uri_list_sort_direction="
            option12 = "Uri_list_filter_HDF5="
            option13 = "Uri_list_filter_MDSplus="
            userPreferencesFile = os.environ['HOME'] + '/.imasviz/preferences'
            if os.path.exists(userPreferencesFile):
                with open(userPreferencesFile) as f:
                    for line in f:
                        # One bad line used to cost the whole start-up. Each
                        # option now answers for itself: what it cannot read is
                        # named in the log and costs its own option, so a typo
                        # in the colour leaves the theme, the tree and the
                        # windows of the run exactly where they were.
                        try:
                            if line.startswith(option1):
                                QVizPreferences.ColorOfNodesContainingData = \
                                    QVizPreferences.colour(line[len(option1):])
                            elif line.startswith(option2):
                                QVizPreferences.SelectionColor = \
                                    QVizPreferences.colour(line[len(option2):])
                            elif line.startswith(option3):
                                QVizPreferences.Allow_data_to_be_plotted_with_different_units = \
                                    int(line[len(option3):])
                            elif line.startswith(option4):
                                QVizPreferences.Ignore_GGD = int(line[len(option4):])
                            elif line.startswith(option5):
                                QVizPreferences.Auto_save_session = \
                                    int(line[len(option5):])
                            elif line.startswith(option6):
                                QVizPreferences.Theme = QVizPreferences.theme(
                                    line[len(option6):])
                            elif line.startswith(option7):
                                QVizPreferences.Show_only_tensors_rank_ge_1 = \
                                    int(line[len(option7):])
                            elif line.startswith(option8):
                                QVizPreferences.Close_button_deletes = \
                                    QVizPreferences.yesNo(line[len(option8):])
                            elif line.startswith(option9):
                                QVizPreferences.Mdi_view_mode = \
                                    QVizPreferences.layoutMode(
                                        line[len(option9):])
                            elif line.startswith(option10):
                                QVizPreferences.Uri_list_sort_key = \
                                    QVizPreferences.sortKey(line[len(option10):])
                            elif line.startswith(option11):
                                QVizPreferences.Uri_list_sort_direction = \
                                    QVizPreferences.sortDirection(
                                        line[len(option11):])
                            elif line.startswith(option12):
                                QVizPreferences.Uri_list_filter_HDF5 = \
                                    QVizPreferences.yesNo(line[len(option12):])
                            elif line.startswith(option13):
                                QVizPreferences.Uri_list_filter_MDSplus = \
                                    QVizPreferences.yesNo(line[len(option13):])
                        except ValueError as bad:
                            logging.warning('Ignoring %s in %s: %s',
                                            line.split('=', 1)[0],
                                            userPreferencesFile, bad)

                QVizPreferences.userPreferencesInitialized = True
            else:
                logging.info("No user preferences file found.")

    def theme(text):
        """Which theme to wear, refusing a name IMASViz does not dress in.

        What exists is asked of ``QVizStyle`` -- it holds the two palettes -- so
        the answer to ``Theme=`` cannot drift from the colours on screen. What
        the refusal *names* is what the file says, as it was typed: the name is
        matched case-insensitively, and a line reading ``Theme=Night`` answered
        ``unknown theme 'night'``, which is a word nobody wrote.
        """
        from imasviz.VizGUI.VizGuiCustomization import QVizStyle

        asked = text.strip().lower()
        try:
            QVizStyle.forName(asked)
        except ValueError:
            raise ValueError('%r is not a theme: IMASViz wears %s'
                             % (text.strip(),
                                ' or '.join(repr(one)
                                            for one in QVizStyle.NAMES)))
        return asked

    def yesNo(text):
        """One of the two switches that mean something else when they are on.

        ``int(text)`` would read ``Close_button_deletes=purple`` as a
        ``ValueError`` and say nothing about what the line was asked to hold,
        and would read ``2`` as a third state nothing answers. Both are refused
        by what the file says, and the switch stays at its default: the line
        answers for itself, the rest of the file is read (T48).
        """
        asked = text.strip()
        if asked not in ('0', '1'):
            raise ValueError('%r is not a yes/no switch: write 0 to keep the '
                             'default or 1 to change it' % asked)
        return int(asked)

    def layoutMode(text):
        """Which view the MDI area wears, refusing a name it cannot lay out in.

        ``QVizPreferences.LAYOUT_MODES`` is what the *Disposition* sub-menu
        answers, so a file that writes a name nobody wrote on a menu is a name
        the application does not wear, and the line that spelled it is the one
        that refuses it. The default the line reads to is what the MDI area
        already answers, so nothing else changes.
        """
        asked = text.strip().lower()
        if asked not in QVizPreferences.LAYOUT_MODES:
            raise ValueError(
                '%r is not a view for the MDI area: write %s'
                % (text.strip(),
                   ' or '.join(repr(one) for one in
                               QVizPreferences.LAYOUT_MODES)))
        return asked


class QVizGlobalValues:

    IMAS_VIZ_VERSION = ''
    if "IMAS_VIZ_VERSION" in os.environ:
        IMAS_VIZ_VERSION = os.environ["IMAS_VIZ_VERSION"]

    indices = {'1': 'i', '2': 'j', '3': 'k', '4': 'l', '5': 'q', '6': 'r', '7': 't'}
    max_indices = {'1': 'N', '2': 'M', '3': 'K', '4': 'L', '5': 'Q', '6': 'R', '7': 'T'}

    TORE_SUPRA = 'TS'
    IMAS_NATIVE = 'NATIVE'
    IMAS_UDA = "UDA"
    WEST = "WEST"
    TCV = "TCV"
    JET = "JET"
    AUG = "AUG"
    MAST = "MAST"

    ExternalSources = (MAST, WEST, TCV, JET, AUG)

    if "VIZ_PRODUCTION" not in os.environ:
        print ("VIZ_PRODUCTION environment variable not defined")
        os.environ["VIZ_PRODUCTION"] = "0"

    TESTING = not bool(int(os.environ["VIZ_PRODUCTION"]))
    if TESTING:
        IMAS_VIZ_VERSION = 'DEVEL'
        TESTING_VIZ_HOME = None
        os.environ["WEST"] = '1'
        if "VIZ_HOME" in os.environ:
            TESTING_VIZ_HOME = os.environ["VIZ_HOME"]
        else:
            os.environ["VIZ_HOME"] = os.environ["HOME"] + "/viz"

        if os.getenv("DATABASE_NAME") is None:
            os.environ["DATABASE_NAME"] = os.uname()[1]

        if TESTING_VIZ_HOME is None:
            if os.environ["HOSTNAME"] == 'r000u11l06':
                TESTING_VIZ_HOME = os.environ["HOME"] + '/workspace_python/viz'
            elif os.environ['HOSTNAME'] == 'spica.intra.cea.fr' or \
                        os.environ['HOSTNAME'] == 'sirrah' \
                    or os.environ['HOSTNAME'] == 'gemma.intra.cea.fr':
                TESTING_VIZ_HOME = os.environ["HOME"] + '/viz'
            else:
                print ("Environment variable TESTING_VIZ_HOME not defined. Check the QVizGlobalValues.py file. Exiting.")
                sys.exit(-1)

        os.environ["UDA_DISABLED"] = "1"
        TESTING_USER = os.environ["USER"]
        TESTING_TS_MAPPINGS_DIR = TESTING_VIZ_HOME + '/ts_mapping_files'
        # IMAS_VERSION is the version of the *data dictionary*, and IMAS-Python
        # reads it itself (imas.dd_zip). It used to be filled here from
        # AL_VERSION when unset, which is what made opening a pulse die: AL_VERSION
        # is 5.7.1 on this stack, an Access Layer number that is not a data
        # dictionary at all -- the distribution bundles 35 of them, 3.22.0 to
        # 4.1.1. Nothing invents that number any more.
        TESTING_IMAS_VERSION = os.environ.get("IMAS_VERSION", '')
        if TESTING_IMAS_VERSION == '':
            print ("IMAS_VERSION environment variable not defined. Load the IMAS module or export IMAS_VERSION. Exiting.")
            sys.exit(-1)

        print("TESTING_VIZ_HOME:" + TESTING_VIZ_HOME)
        print("TESTING_IMAS_VERSION:" + TESTING_IMAS_VERSION)

    else:
        print ("VIZ_HOME:" + os.environ["VIZ_HOME"])
        if IMAS_VIZ_VERSION == '':
            print("IMAS_VIZ_VERSION not defined in environment. Please report to admin!")
            IMAS_VIZ_VERSION = 'Undefined (please report to admin)'
        if "TS_MAPPINGS_DIR" not in os.environ:
            os.environ["TS_MAPPINGS_DIR"] = os.environ["VIZ_HOME"] + '/ts_mapping_files'

class GlobalIDs:
    """The one Qt event type the application posts to itself.

    This class used to carry 38 integer ids for menu items and actions, numbered
    for a Qt where a menu entry was addressed by a number (the comments named
    their consumers: `wxDataTreeView.py`, `SignalHandling.py`,
    `LoadDataHandling.py`). All three are gone, and a PySide6 menu entry is a
    QAction holding a callable, so nothing reads those numbers any more: counted,
    38 declared, 0 read, outside the declaration itself. They are gone with this
    pass. What stays is the event the tree view listens for.
    """
    RESULT_EVENT = 9999


class GlobalFonts:
    """The four fonts the chrome of the application is drawn with.

    A family name is a wish, not a font. ``QFont('Open Sans')``, which every one
    of these four used to name, is not installed on this node -- ``QFontInfo``
    answers ``DejaVu Sans`` for it -- so the tree, the menus and the labels were
    drawn with a substitute nobody had asked for, at a size the theme had no say
    in either. The family is decided once, by ``QVizStyle``, and put here with
    ``useFamily``, so the application font and these four cannot be two faces.
    """
    from PySide6.QtGui import QFont

    #: The family the four currently stand on.
    FAMILY = 'Sans Serif'

    TITLE_MEDIUM = QFont(FAMILY, 11)
    TITLE_MEDIUM.setBold(True)

    TITLE_BIG = QFont(FAMILY, 15)
    TITLE_BIG.setBold(True)

    TEXT_MEDIUM = QFont(FAMILY, 10)
    TEXT_BIG = QFont(FAMILY, 11)

    @staticmethod
    def useFamily(family):
        """Rebuild the four on one installed family, and answer that family.

        Called once, from ``QVizStyle.applyToApplication``, with the family
        ``QFontInfo`` resolved. The sizes stay -- they are what the tree and the
        labels were laid out for; only the face follows the theme.
        """
        from PySide6.QtGui import QFont
        GlobalFonts.FAMILY = family
        GlobalFonts.TITLE_MEDIUM = QFont(family, 11)
        GlobalFonts.TITLE_MEDIUM.setBold(True)
        GlobalFonts.TITLE_BIG = QFont(family, 15)
        GlobalFonts.TITLE_BIG.setBold(True)
        GlobalFonts.TEXT_MEDIUM = QFont(family, 10)
        GlobalFonts.TEXT_BIG = QFont(family, 11)
        return family


class GlobalQtStyles:
    """Global Qt styles dictionary.
    """
    from PySide6.QtCore import Qt

    # Set dictionary of line styles (keys) with their Qt style
    # counterpart (values)
    stylesDict = {'Solid Line' : Qt.SolidLine,
                  'Dash Line' : Qt.DashLine,
                  'Dot Line' : Qt.DotLine,
                  'Dash Dot Line' : Qt.DashDotLine,
                  'Dash Dot Dot Line' : Qt.DashDotDotLine,
                  'Hide Line': Qt.NoPen}


class GlobalPgSymbols:
    """Global pyqtgraph list of symbols.
    """

    # Set dictionary of plot symbols types description (keys) with their
    # pyqtgraph recognized label (variable).
    symbolsDict = { 'None'           : None,
                    'O'              : 'o',
                    '+'              : '+',
                    'Triangle Down'  : 't',
                    'Triangle Up'    : 't1',
                    'Triangle Right' : 't2',
                    'Triangle Left'  : 't3',
                    'Square'         : 's',
                    'Rhomb'          : 'd',
                    'Pentagon'       : 'p',
                    'Hexagon'        : 'h',
                    'Star'           : 'star'}


class GlobalIcons:
    """Global IMASViz icons.
    """

    def getCustomQIcon(application, label):
        """Get custom QIcon.
        TODO: Make it more efficient (maybe load everything at the start of
        the application etc.).

        Arguments:
            application (QApplication) : Running application object.
            label       (str)          : IMASViz QIcon label.
        """

        if label == 'unselect':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/minus.ico')
        if label == 'unselectMultiple':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/minus3x.ico')
        elif label == 'select':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/plus.ico')
        elif label == 'selectAOS':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/plus3x.ico')
        elif label == 'Figure' or label == 'Image':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/Figure.ico')
        elif label == 'TPV':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/TablePlotView.ico')
        elif label == 'SPV':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/StackedPlotView.ico')
        elif label == 'plotSingle':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/plotSingle.ico')
        elif label == 'plotMultiple':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/plotMultiple.ico')
        elif label == 'showHide':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/showHide.ico')
        elif label == 'publicdbs':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/publicdbs.ico')
        elif label == 'thisDTV':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/thisDTV.ico')
        elif label == 'allDTV':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/allDTV.ico')
        elif label == 'new':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/new.ico')
        elif label == 'bold':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/textIcons/bold.ico')
        elif label == 'italic':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/textIcons/italic.ico')
        elif label == 'underlined':
            return QtGui.QIcon(os.environ['VIZ_HOME'] +
                               '/resources/VizIcons/textIcons/underlined.ico')

    def getStandardQIcon(application, QStyleID):
        """Get standard QIcon by QStyle ID. Application must already run if the
        list is to be accessed.

        Arguments:
            application (QApplication) : Running application object.
            QStyleID    (int)          : QStyle icon ID.
        """
        return QtGui.QIcon(application.style().standardIcon(QStyleID))
