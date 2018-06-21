
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

    """Global frame, panels etc. IDs"""
    MENU_PREVIEW_PLOT_ID = 201
    MENU_MULTIPLOT_ID = 202
    MENU_SIGNALS_ID = 203
    MENU_SIGNALS_UNSELECT_ID = 204
    MENU_ITEM_PREVIEW_PLOT_ENABLE_DISABLE_ID = 2011
    MENU_ITEM_PREVIEW_PLOT_FIX_POSITION_ID =2012
    MENU_ITEM_SIGNALS_ALL_DTV_TO_MULTIPLOT_ID = 2013
    MENU_ITEM_SIGNALS_SINGLE_DTV_TO_MULTIPLOT_ID = 2014
    MENU_ITEM_SIGNALS_SAVE_ID = 2015
    MENU_ITEM_SIGNALS_UNSELECT_SINGLE_DTV_ID = 2016
    MENU_ITEM_SIGNALS_UNSELECT_ALL_DTV_ID = 2017


