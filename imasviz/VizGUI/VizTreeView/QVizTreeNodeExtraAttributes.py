from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues

class QVizTreeNodeExtraAttributes:

    def __init__(self, *args, **kwargs):
        self.parametrizedPath = None
        self.itime_index = None  # string
        self.aos_parents_count = None  # sring
        self.parameters_values = {}  # key = index name ('i', 'j', ...)
        self.parameters_max_values = {}
        self.coordinate1 = None

    def addParameterValue(self, aos_indice_name, value):
        self.parameters_values[aos_indice_name] = value

    def addMaxParameterValue(self, aos_indice_name, value):
        self.parameters_max_values[aos_indice_name] = value

    def isCoordinateTimeDependent(self, coordinate):
        if '/time' in coordinate or '.time' in coordinate or coordinate == 'time':
            return True
        return False

    def time_dependent(self, path):
        if 'itime' in path:
            return True
        return False

    def embedded_in_time_dependent_aos(self):
        return self.time_dependent(self.parametrizedPath)
