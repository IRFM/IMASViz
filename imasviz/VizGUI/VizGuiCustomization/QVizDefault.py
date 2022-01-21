import os


class QVizDefaultGUIEntries:
    def __init__(self):
        pass

    def getDefaultEntries(self):
        default_user = os.getenv('USER')
        default_machine = ''
        default_run = '0'
        return default_user, default_machine, default_run


class QVizDefault:

    @staticmethod
    def getGUIEntries():
        return QVizDefaultGUIEntries().getDefaultEntries()
