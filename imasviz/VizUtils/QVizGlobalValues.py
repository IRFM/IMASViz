
import os
import sys
import logging
from PySide2 import QtGui


class FigureTypes:
    FIGURETYPE = "Figure:"
    IMAGETYPE = "Image:"
    TABLEPLOTTYPE = "TablePlotView:"
    STACKEDPLOTTYPE = "StackedPlotView:"
    PROFILESPLOTTYPE = "PlotView:"

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
    """Global colors
    """
    from PySide2.QtGui import QBrush, QColor

    BLUE = QBrush(QColor('#0000ff'))
    RED = QBrush(QColor('#ff0000'))
    BLACK = QBrush(QColor('#000000'))
    CYAN = QBrush(QColor('#00ffff'))
    LIGHT_CYAN = QBrush(QColor('#cce5ff'))
    LIGHT_GREY = QBrush(QColor('#d3d3d3'))

    BLUE_HEX = '#0000ff'
    RED_HEX = '#ff0000'
    GREEN_HEX = '#008000'
    YELLOW_HEX = '#FFFF00'
    ORANGE_HEX = '#FFA500'
    PURPLE_HEX = '#800080'
    BLACK_HEX = '#000000'
    CYAN_HEX = '#00ffff'
    LIGHT_CYAN_HEX = '#cce5ff'
    LIGHT_GREY_HEX = '#d3d3d3'
    LIME_HEX = '#00FF00'
    MAGENTA_HEX = '#FF00FF'
    SILVER_HEX = '#C0C0C0'
    GRAY_HEX = '#808080'
    MAROON_HEX = '#800000'
    OLIVE_HEX = '#808000'
    TEAL_HEX = '#008080'
    NAVY_HEX = '#000080'

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

    def build(self):
        if not QVizPreferences.userPreferencesInitialized:
            from PySide2.QtGui import QBrush, QColor
            QVizPreferences.ColorOfNodesContainingData = GlobalColors.BLUE
            QVizPreferences.SelectionColor = GlobalColors.RED
            option1 = "Colour_of_data_nodes_containing_data="
            option2 = "Nodes_selection_colour="
            option3 = "Allow_data_to_be_plotted_with_different_units="
            option4 = "Ignore_GGD="
            userPreferencesFile = os.environ['HOME'] + '/.imasviz/preferences'
            if os.path.exists(userPreferencesFile):
                logging.info("No user preferences file found.")
                with open(userPreferencesFile) as f:
                    for line in f:
                        if line.startswith(option1):
                            color_str = line[len(option1):]
                            QVizPreferences.ColorOfNodesContainingData = GlobalColors.getAvailableColorForNodes(int(color_str) - 1)
                        elif line.startswith(option2):
                            color_str = line[len(option2):]
                            QVizPreferences.SelectionColor = GlobalColors.getAvailableColorForNodes(int(color_str) - 1)
                        elif line.startswith(option3):
                            value = line[len(option3):]
                            QVizPreferences.Allow_data_to_be_plotted_with_different_units = int(value)
                        elif line.startswith(option4):
                            value = line[len(option4):]
                            QVizPreferences.Ignore_GGD = int(value)

                userPreferencesInitialized = True


class QVizGlobalValues:

    IMAS_VIZ_VERSION = ''
    if "IMAS_VIZ_VERSION" in os.environ:
        IMAS_VIZ_VERSION = os.environ["IMAS_VIZ_VERSION"]

    # Default maximum number of IDS occurences
    MAX_NUMBER_OF_IDS_OCCURRENCES = 5

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
            os.environ["VIZ_HOME"] = os.environ["HOME"] + "viz"

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
        TESTING_IMAS_DATA_DICTIONARIES_DIR = TESTING_VIZ_HOME + '/imas_data_dictionaries'
        TESTING_IMAS_VERSION = os.environ["IMAS_VERSION"]
        TESTING_IMAS_MAJOR_VERSION = "3"

        print("TESTING_VIZ_HOME:" + TESTING_VIZ_HOME)
        print("TESTING_IMAS_VERSION:" + TESTING_IMAS_VERSION)

    else:
        print ("VIZ_HOME:" + os.environ["VIZ_HOME"])
        if IMAS_VIZ_VERSION == '':
            print("IMAS_VIZ_VERSION not defined in environment. Please report to admin!")
            IMAS_VIZ_VERSION = 'Undefined (please report to admin)'
        os.environ["TS_MAPPINGS_DIR"] = os.environ["VIZ_HOME"] + '/ts_mapping_files'
        os.environ["IMAS_DATA_DICTIONARIES_DIR"] = os.environ["VIZ_HOME"] + '/imas_data_dictionaries'
        if "IMAS_VERSION" in os.environ:
            os.environ["IMAS_MAJOR_VERSION"] = os.environ["IMAS_VERSION"][:1]
        else:
            os.environ["IMAS_MAJOR_VERSION"] = ""

class GlobalIDs:
    """Global frame, panels etc. IDs.
    """
    # IDs used in wxDataTreeView.py
    ID_MENU_PREVIEW_PLOT = 201
    ID_MENU_MULTIPLOT = 202
    ID_MENU_SIGNALS = 203
    ID_MENU_SIGNALS_UNSELECT = 204
    ID_POPUP_MENU_SIGNALS_UNSELECT_SINGLE_DTV = 205
    ID_POPUP_MENU_SIGNALS_UNSELECT_ALL_DTV = 206
    ID_MENU_ITEM_PREVIEW_PLOT_ENABLE_DISABLE = 2011
    ID_MENU_ITEM_PREVIEW_PLOT_FIX_POSITION = 2012
    ID_MENU_ITEM_SIGNALS_ALL_DTV_TO_MULTIPLOT = 2013
    ID_MENU_ITEM_SIGNALS_SINGLE_DTV_TO_MULTIPLOT = 2014
    ID_MENU_ITEM_SIGNALS_SAVE = 2015
    ID_MENU_ITEM_SIGNALS_UNSELECT_SINGLE_DTV = 2016
    ID_MENU_ITEM_SIGNALS_UNSELECT_ALL_DTV = 2017
    ID_MENU_ITEM_APPLY_CONFIGURATION = 2018
    ID_MENU_ITEM_CLOSE_AND_REOPEN_DATABASE = 2019

    # IDs used in SignalHandling.py
    ID_ADD_PLOT_TO_FIGURE = 1000
    ID_ADD_PLOT_TO_EXISTING_FIGURE = 1500
    ID_SELECT_OR_UNSELECT_SIGNAL = 2000
    ID_SHOW_HIDE_FIGURES  = 3000
    ID_SHOW_HIDE_MULTIPLOTS = 3500
    ID_SHOW_HIDE_SUBPLOTS = 4000
    ID_PLOT_ALL_SELECTED_SIGNALS_TO_FIGURE = 5000
    ID_PLOT_AS_ITIME = 6000
    ID_PLOT_SELECTED_SIGNALS_TO_NEW_FIGURE = 7000
    ID_PLOT_SELECTED_SIGNALS_TO_NEW_FIGURE_SINGLE_DTV = 7001
    ID_PLOT_SELECTED_SIGNALS_TO_NEW_FIGURE_ALL_DTV = 7002
    ID_PLOT_SELECTED_SIGNALS_TO_MULTIPLOTFRAME = 7100
    ID_PLOT_SELECTED_SIGNALS_TO_MULTIPLOTFRAME_ALL_DTV = 7101
    ID_PLOT_SELECTED_SIGNALS_TO_MULTIPLOTFRAME_SINGLE_DTV = 7202
    ID_ADD_SELECTION_TO_MULTIPLOT = 7300
    ID_SELECT_ALL_SIGNALS_FROM_SAME_AOS = 7400
    ID_OPEN_SUBPLOTS_MANAGER = 8000
    ID_DELETE_FIGURES = 10000
    ID_DELETE_MULTIPLOTS = 11000
    ID_DELETE_SUBPLOTS = 12000

    # IDs used in LoadDataHandling.py
    ID_GET_IDS_DATA = 13000
    ID_REFRESH_IDS_DATA = 13001
    ID_GET_IDS_OCC_DATA = 13002

    # Other IDs
    # ID_CHANGE_COORD1 = 14001
    # ID_CHANGE_TIME1 = 14002

    # PyQt5
    RESULT_EVENT = 9999


def getRGBColorList():
    """Get RGB color list for plot lines using hex colors defined in
    GlobalColors.
    """

    # Set empty list ob RGB colors
    RGBlist = []

    # The predefined global colors (hex) will be used
    gc = GlobalColors()
    gck = GlobalColors.__dict__.keys()
    # - Get all members, specifying hex color, available
    #   (e.g. 'BLACK_HEX' etc)
    members = [attr for attr in gck if not attr.startswith("__") and attr.endswith("HEX")]

    # Move attribute for blue color to front (first and default plot color)
    members.insert(0, members.pop(members.index('BLUE_HEX')))

    for member in members:
        # Get string attribute and remove '#'
        c = getattr(gc, member).lstrip('#')
        # Convert hex to RGB and add it to the list of RGB colors
        RGBlist.append(tuple(int(c[i:i+2], 16) for i in (0, 2 ,4)))

    return RGBlist


class GlobalFonts:
    """Global fonts.
    """
    from PySide2.QtGui import QFont

    TITLE_MEDIUM = QFont('Open Sans', 11)
    # TITLE.setStyleHint(QFont.TypeWriter)
    TITLE_MEDIUM.setBold(True)

    TITLE_BIG = QFont('Open Sans', 15)
    # TITLE.setStyleHint(QFont.TypeWriter)
    TITLE_BIG.setBold(True)

    TEXT_MEDIUM = QFont('Open Sans', 10)
    TEXT_BIG = QFont('Open Sans', 11)
    # TEXT.setStyleHint(QFont.TypeWriter)


class GlobalQtStyles:
    """Global Qt styles dictionary.
    """
    from PySide2.QtCore import Qt

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
