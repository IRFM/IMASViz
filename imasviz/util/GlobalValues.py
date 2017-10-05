
import os
import sys

class GlobalValues:
    
    indices = {'1': 'i', '2': 'j', '3': 'k', '4': 'l', '5': 'q', '6': 'r', '7': 't'}
    max_indices = {'1': 'N', '2': 'M', '3': 'K', '4': 'L', '5': 'Q', '6': 'R', '7': 'T'}

    TORE_SUPRA = 'TS'
    IMAS_NATIVE = 'NATIVE'
    IMAS_UDA = "UDA"
    WEST = "WEST"
    TESTING = True
    TESTING_VIZ_HOME = None
    if "VIZ_HOME" in os.environ:
        TESTING_VIZ_HOME = os.environ["VIZ_HOME"]

    if TESTING_VIZ_HOME is None:
        if os.environ["HOSTNAME"] == 'r000u11l06':
            TESTING_VIZ_HOME = os.environ["HOME"] + '/workspace_python/viz'
        elif os.environ['HOSTNAME'] == 'spica.intra.cea.fr' or os.environ['HOSTNAME'] == 'sirrah':
            TESTING_VIZ_HOME = os.environ["HOME"] + '/viz'
        else:
            print "Environment variable TESTING_VIZ_HOME not defined. Check the GlobalValues.py file. Exiting."
            sys.exit(-1)

    print "TESTING_VIZ_HOME:" + TESTING_VIZ_HOME

    TESTING_USER = os.environ["USER"]
    TESTING_TS_MAPPINGS_DIR = TESTING_VIZ_HOME + '/ts_mapping_files'
    TESTING_IMAS_DATA_DICTIONARIES_DIR = TESTING_VIZ_HOME + '/imas_data_dictionaries'

    TESTING_IMAS_DATA_DICTIONARY_VERSION = "3.11.0"
    TESTING_IMAS_MAJOR_VERSION = "3"


