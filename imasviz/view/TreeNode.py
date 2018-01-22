import numpy as np
from imasviz.util.GlobalValues import GlobalValues

class TreeNode:

    def __init__(self, aos, coordinate1, itime_index = -1, aos_parents_count = 0):
        self.aos = aos
        self.itime_index = itime_index #string
        self.aos_parents_count = aos_parents_count #sring
        self.aos_indices_values = {} #key = index name ('i', 'j', ...)
        self.aos_indices_max_values = {}
        self.coordinate1 = coordinate1

    def add_aos_value(self, aos_indice_name, value):
        self.aos_indices_values[aos_indice_name] = value

    def add_aos_max_value(self, aos_indice_name, value):
        self.aos_indices_max_values[aos_indice_name] = value

    def time_dependent(self, path):
        if '[itime]' in path:
            return True
        return False

    def time_dependent_aos(self):
        return self.time_dependent(self.aos)

    def isCoordinateTimeDependent(self, coordinate):
        if '/time' in coordinate or '.time' in coordinate or coordinate=='time' :
            return True
        return False

    def index_name_of_itime(self):
        i = 0
        #print "TreeNode : self.itime_index = " + self.itime_index
        for key in GlobalValues.indices:
            if i == int(self.itime_index):
                return GlobalValues.indices[key]
            i = i + 1

    def replaceBrackets(self, toReplace): #replace '[' by '(' and ']' by ')'
        c = toReplace.replace("[", "(")
        return c.replace("]", ")")

    def evaluateCoordinate1(self):
        coordinate1 = self.evaluateCoordinate1VsTime()
        if self.time_dependent(self.coordinate1):
            coordinate1 = coordinate1.replace("[itime]", "[" + self.timeValue() + "]")
        return coordinate1
    
    def evaluateCoordinate1At(self, itimeValue):
        coordinate1 = self.evaluateCoordinate1VsTime()
        if self.time_dependent(self.coordinate1):
            coordinate1 = coordinate1.replace("[itime]", "[" + str(itimeValue) + "]")
        if coordinate1 == None:
            coordinate1 = self.coordinate1
        return coordinate1

    def coordinate1Label(self, idsName, index, ids):
        if self.coordinate1 == "1..N" or self.coordinate1 == "1...N":
            return "[" + str(index) + "]"
        to_eval = "ids." + idsName + \
                  "." + self.evaluateCoordinate1() + "[" + str(index) + "]"
        coordinate1_value = eval(to_eval)
        tokens_list = to_eval.split(".")
        coord1 = tokens_list[-1]
        label = coord1 + "=" + str(coordinate1_value)
        return label

    def evaluateCoordinate1VsTime(self):#the result can eventually depend on [itime]
        return self.evaluatePath(self.coordinate1)

    def coordinate1Length(self, selectedNodeData, ids):

        if self.coordinate1 == "1..N" or self.coordinate1 == "1...N":
            r = np.array([eval(selectedNodeData['dataName'])])
            return len(r[0])

        to_evaluate = "ids." + selectedNodeData['IDSName'] + "." + self.evaluateCoordinate1()
        #print to_evaluate
        return len(eval(to_evaluate))

    def timeMaxValue(self):
        if self.time_dependent(self.aos):
            return self.aos_indices_max_values[self.index_name_of_itime()]
        #print "timeMaxValue : Node is not time dependent !"

    def timeValue(self):
        if self.time_dependent(self.aos):
            return self.aos_indices_values[self.index_name_of_itime()]
        #print "timeValue : Node is not time dependent !"


    def getDataPathVsTime(self, path):
        return self.evaluatePath(path)

    def evaluatePath(self, path):
        aos_valued = None
        path = self.patchIndices(path)
        for i in xrange(0, self.aos_parents_count):
            index_name = GlobalValues.indices[str(i + 1)]
            index_value =  self.aos_indices_values[index_name]
            s = "[" + index_name + "]"
            aos_valued = path.replace(s, "[" + index_value + "]")
            path= aos_valued
        return aos_valued
    
    def patchIndices(self, value):
        value = value.replace("[i1]", "[i]")
        value = value.replace("[i2]", "[j]")
        value = value.replace("(i3]", "[k]")
        value = value.replace("[i4]", "[l]")
        value = value.replace("[i5]", "[q]")
        value = value.replace("[i6]", "[r]")
        value = value.replace("(i7]", "[t]")
        #print "patched value : " + value
        return value

    def getDataPath(self, data_path_vs_time, itime_value):
        s = "[itime]"
        replacement = "[" + str(itime_value) + "]"
        return data_path_vs_time.replace(s, replacement)


    def getDataVsTime(self):
        data_list = []
        aos_vs_itime = self.getDataPathVsTime(self.aos)
        #print "TreeNode : time max value = " + self.timeMaxValue()
        for itime in xrange(0, int(self.timeMaxValue())):
            data_path = self.getDataPath(aos_vs_itime, itime)
            data_list.append(data_path)
        return data_list
