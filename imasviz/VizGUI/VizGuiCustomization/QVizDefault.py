import os


class QVizDefaultGUIEntries:
    def __init__(self):
        pass

    def getDefaultEntries(self):
        default_user = os.getenv('USER')
        default_machine = ''
        default_run = '0'
        return default_user, default_machine, default_run

    def getDefaultEntriesForWEST(self):
        default_user = 'public'
        default_machine = 'west'
        default_run = '1'
        return default_user, default_machine, default_run


class QVizDefault:

    @staticmethod
    def getGUIEntries():
        machineName = os.getenv('DATABASE_NAME')
        if machineName is None:
            TESTING = not bool(int(os.environ["VIZ_PRODUCTION"]))
            if TESTING:
                machineName = ''
        if machineName == 'WEST':
            return QVizDefaultGUIEntries().getDefaultEntriesForWEST()
        else:
            return QVizDefaultGUIEntries().getDefaultEntries()
