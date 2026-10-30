
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
    # handed out. A second namespace for one kind of window is two Show/Hide
    # entries and one window the "add to" entries cannot fill; a namespace with
    # no frame left behind it is a Show/Hide entry that can never be filled.
    CURVEPLOTTYPE = "SlicesPlot"
    IMAGEPLOTTYPE = "SlicesImage"
    # The window the Equilibrium plugin builds is a figure like the others: it is
    # registered in `figureframes`, so Show/Hide and Delete reach it. It is not
    # drawn through the axes model, so it keeps its own prefix and registers no
    # node in `figToNodes` -- the "add this quantity to that figure" entries walk
    # that record and could not fill a matplotlib window.
    EQUILIBRIUMPLOTTYPE = "EquiPlotView:"

    # Every kind of figure the commands can draw, in menu order: the label the
    # user reads (it is the prefix the window title shows), the icon named in
    # GlobalIcons, and the prefix its key carries. The Show/Hide and Delete
    # menus iterate this, because a kind missing here is a window the user has
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
    # Which of the two themes the application is dressed with -- see
    # ``VizGUI/VizGuiCustomization/QVizStyle.py``, which holds both palettes and
    # is what refuses a name it does not wear. Light is the default: the tool is
    # used on a desktop in a lit room, and it is what the manual's screenshots
    # were taken on.
    Theme = 'light'

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
