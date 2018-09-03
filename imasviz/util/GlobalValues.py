
import os
import sys

class FigureTypes:
    FIGURETYPE = "Figure:"
    MULTIPLOTTYPE = "Multiplot:"
    SUBPLOTTYPE = "Subplot:"

class GlobalValues:

    IMAS_VIZ_VERSION = 1.1

    indices = {'1': 'i', '2': 'j', '3': 'k', '4': 'l', '5': 'q', '6': 'r', '7': 't'}
    max_indices = {'1': 'N', '2': 'M', '3': 'K', '4': 'L', '5': 'Q', '6': 'R', '7': 'T'}

    TORE_SUPRA = 'TS'
    IMAS_NATIVE = 'NATIVE'
    IMAS_UDA = "UDA"
    WEST = "WEST"
    TCV = "TCV"
    JET = "JET"
    AUG = "AUG"

    if "VIZ_PRODUCTION" not in os.environ:
        print ("VIZ_PRODUCTION environment variable not defined")
        os.environ["VIZ_PRODUCTION"] = "0"

    TESTING = not bool(int(os.environ["VIZ_PRODUCTION"]))

    if TESTING:
        TESTING_VIZ_HOME = None
        if "VIZ_HOME" in os.environ:
            TESTING_VIZ_HOME = os.environ["VIZ_HOME"]

        if TESTING_VIZ_HOME is None:
            if os.environ["HOSTNAME"] == 'r000u11l06':
                TESTING_VIZ_HOME = os.environ["HOME"] + '/workspace_python/viz'
            elif os.environ['HOSTNAME'] == 'spica.intra.cea.fr' or \
                            os.environ['HOSTNAME'] == 'sirrah' \
                    or os.environ['HOSTNAME'] == 'gemma.intra.cea.fr':
                TESTING_VIZ_HOME = os.environ["HOME"] + '/viz'
            else:
                print ("Environment variable TESTING_VIZ_HOME not defined. Check the GlobalValues.py file. Exiting.")
                sys.exit(-1)


        TESTING_USER = os.environ["USER"]
        TESTING_TS_MAPPINGS_DIR = TESTING_VIZ_HOME + '/ts_mapping_files'
        TESTING_IMAS_DATA_DICTIONARIES_DIR = TESTING_VIZ_HOME + '/imas_data_dictionaries'
        TESTING_IMAS_VERSION = "3.15.1"
        TESTING_IMAS_MAJOR_VERSION = "3"

        print("TESTING_VIZ_HOME:" + TESTING_VIZ_HOME)
        print("TESTING_IMAS_VERSION:" + TESTING_IMAS_VERSION)

    else:
        print ("VIZ_HOME:" + os.environ["VIZ_HOME"])
        os.environ["TS_MAPPINGS_DIR"] = os.environ["VIZ_HOME"] + '/ts_mapping_files'
        os.environ["IMAS_DATA_DICTIONARIES_DIR"] = os.environ["VIZ_HOME"] + '/imas_data_dictionaries'
        os.environ["IMAS_MAJOR_VERSION"] = os.environ["IMAS_VERSION"][:1]

class GlobalIDs:
    """Global frame, panels etc. IDs.
    """
    # IDs used in wxDataTreeView.py
    ID_MENU_PREVIEW_PLOT = 201
    ID_MENU_MULTIPLOT = 202
    ID_MENU_SIGNALS = 203
    ID_MENU_SIGNALS_UNSELECT = 204
    ID_MENU_ITEM_PREVIEW_PLOT_ENABLE_DISABLE = 2011
    ID_MENU_ITEM_PREVIEW_PLOT_FIX_POSITION =2012
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
    ID_PLOT_SELECTED_SIGNALS_ALL_DTV_TO_MULTIPLOTFRAME = 7100
    ID_PLOT_SELECTED_SIGNALS_SINGLE_DTV_TO_MULTIPLOTFRAME = 7200
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

class GlobalColors:
    """Global colors
    """
    from PyQt5.QtGui import QBrush, QColor

    BLUE = QBrush(QColor('#0000ff'))
    RED = QBrush(QColor('#ff0000'))
    BLACK = QBrush(QColor('#000000'))

    BLUE_HEX = '#0000ff'
    RED_HEX = '#ff0000'
    BLACK_HEX = '#000000'




