from imasviz.VizUtils.QVizGlobalOperations import QVizGlobalOperations
from imasviz.VizUtils.QVizGlobalValues import QVizGlobalValues

class QVizTreeNodeExtraAttributes:

    def __init__(self, *args, **kwargs):
        self.aos = None
        self.itime_index = None  # string
        self.aos_parents_count = None  # sring
        self.aos_indices_values = {}  # key = index name ('i', 'j', ...)
        self.aos_indices_max_values = {}
        self.coordinate1 = None

    def add_aos_value(self, aos_indice_name, value):
        self.aos_indices_values[aos_indice_name] = value

    def add_aos_max_value(self, aos_indice_name, value):
        self.aos_indices_max_values[aos_indice_name] = value

    def isCoordinateTimeDependent(self, coordinate):
        if '/time' in coordinate or '.time' in coordinate or coordinate == 'time':
            return True
        return False

    def time_dependent(self, path):
        if 'itime' in path:
            return True
        return False

    def time_dependent_aos(self):
        return self.time_dependent(self.aos)
