import xml.etree.ElementTree as ET
import os
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues
from threading import *
import wx

class IMAS_DataAccessCodeGenerator():

    def __init__(self, imas_dd_version):
        self.time_step = 10
        className = "ETNativeDataTree_Generated_" + GlobalOperations.replaceDotsByUnderScores(imas_dd_version)
        IDSDefFile = GlobalOperations.getIDSDefFile(imas_dd_version)
        XMLtreeIDSDef = ET.parse(IDSDefFile)
        fileName = className + ".py"
        self.f = open(fileName, 'w')
        self.generateCode(XMLtreeIDSDef, className)
        self.f.close()


    def generateCode(self, XMLtreeIDSDef, className):

        root = XMLtreeIDSDef.getroot()
        i = 0
        for ids in root:
            name_att = ids.get('name')
            if name_att == None:
                continue
            # if name_att != 'equilibrium':
            #     continue
            ids.text = name_att
            if i == 0:
                self.printCode('#This class has been generated -- DO NOT MODIFY MANUALLY !!! --', -1)
                self.printCode('import xml.etree.ElementTree as ET', -1)
                self.printCode('import os', -1)
                self.printCode('import wx', -1)
                self.printCode('import imas', -1)
                self.printCode('import threading', -1)
                self.printCode('import time', -1)
                self.printCode('from imasviz.view.ResultEvent import ResultEvent', -1)
                self.printCode('from threading import Thread', -1)
                self.printCode('\n', -1)

                self.printCode("class " + className + "(Thread):", -1)
                self.printCode("def __init__(self, userName, imasDbName, shotNumber, runNumber, view, occurrence=0, pathsList = None, async=True):", 0)
                self.printCode("Thread.__init__(self)", 1)
                self.printCode("self.occurrence = occurrence", 1)
                self.printCode("self.view = view", 1)
                self.printCode("self.ids = None", 1)
                self.printCode("self.idsName = self.view.IDSNameSelected", 1)
                self.printCode("self.pathsList = pathsList", 1)
                self.printCode("self.async = async", 1)
                self.printCode('', -1)


                self.printCode('def run(self):', 0)
                self.printCode('self.execute()', 1)
                self.printCode('', -1)

                self.printCode('def execute(self):', 0)
                self.printCode("idsData = None", 1)
                #print('-------->name_att')
                #print (name_att)
                for ids2 in root:
                    name_att2 = ids2.get('name')
                    if name_att2 == None:
                        continue
                    #print('name_att2')
                    self.printCode("if self.idsName == '" + name_att2 + "':", 1)
                    self.printCode("self.view.log.info('Loading occurrence ' + str(self.occurrence) + ' of IDS ' + self.idsName + '...')", 2)
                    self.printCode("t1 = time.time()", 2)
                    self.printCode("self.ids." + name_att2 + ".get(self.occurrence)", 2)  # get the data from the database for the ids"
                    self.printCode("t2 = time.time()", 2)
                    self.printCode("print('imas get took ' + str(t2 - t1) + ' seconds')",2)
                    #self.printCode("print ('Get operation ended')", 2)
                    self.printCode('idsData = self.load_' + name_att2 + "(self.idsName, self.occurrence)" + '\n', 2)
                    self.printCode("t3 = time.time()", 2)
                    self.printCode("print('in memory xml object creation took ' + str(t3 - t2) + ' seconds')", 2)
                    self.printCode('if self.async==True:', 2)
                    self.printCode('e = threading.Event()' + '\n', 3)
                    self.printCode('wx.PostEvent(self.view.parent, ResultEvent((self.idsName, self.occurrence, idsData, self.pathsList, e), self.view.parent.eventResultId))',3)
                    self.printCode("print ('waiting for view update...')" + '\n', 3)
                    self.printCode('e.wait()' + '\n', 3)
                    #self.printCode("print ('view update wait ended...')" + '\n', 3)
                    self.printCode('else:', 2)
                    self.printCode('self.view.parent.updateView(self.idsName, self.occurrence, idsData, self.pathsList)', 3)

                self.printCode('\n', -1)


            self.printCode('def load_' + name_att + "(self, IDSName, occurrence):" + '\n', 0)
            self.printCode("IDSName = '" + name_att + "'", 1)
            self.printCode("parents = {}", 1)
            self.printCode('parent = ET.Element(' + "'" + ids.text + "'" + ')', 1)
            self.generateCodeForIDS(None, ids, 1, {}, [], '', 0, name_att)
            self.generateParentsCode(1, ids.text)
            self.printCode("return parent", 1)
            self.printCode('',-1)
            i+=1


    def generateParentsCode(self, level, path):
        path = self.replaceIndices(path)
        code1 = "if parents.get('" + path + "') != None : "
        self.printCode(code1, level)
        code1 = "parent = parents['" + path + "']"
        self.printCode(code1, level + 1)
        self.printCode("else:", level)
        code1 = "parents['" + path + "'] = parent"
        self.printCode(code1, level + 1)

    def generateCodeForIDS(self, parent_AOS, child, level, previousLevel, parents , s, index, idsName):

        for ids_child_element in child:
            index+=1
            data_type = ids_child_element.get('data_type')

            if data_type == 'structure':

                 ids_child_element.text = child.text + '.' + ids_child_element.get('name')

                 self.generateParentsCode(level, child.text)

                 parentCode = "parent = ET.SubElement(parent, " + "'" + ids_child_element.get('name') + "'" + ")"
                 self.printCode(parentCode, level)

                 documentation = ids_child_element.get('documentation')
                 if documentation != None:
                     documentation = documentation.replace("'", "''")
                     documentation = documentation.replace("\n", "")
                     code = "parent.set(" + "'documentation', '" + documentation + "')"
                     self.printCode(code, level)

                 parentName = ids_child_element.get('name')
                 if parentName != None:
                     parentName = parentName.replace("'", "''")
                     parentName = parentName.replace("\n", "")
                     code = "parent.set(" + "'name', '" + parentName + "')"
                     self.printCode(code, level)

                 lifecycle_status = ids_child_element.get('lifecycle_status')
                 if lifecycle_status is not None:
                     code = "parent.set(" + "'lifecycle_status', '" + lifecycle_status + "')"
                     self.printCode(code, level)

                 self.generateCodeForIDS(parent_AOS, ids_child_element, level, previousLevel, parents, s, index, idsName)

            elif data_type == 'struct_array':

                if (ids_child_element.get('name') == "ggd" and child.text == "equilibrium.time_slice[i]"):
                    print("WARNING: GGD structure array from parent equilibrium.time_slice[i] has been ignored")
                    continue

                code = child.text + "." + ids_child_element.get('name') + '(:)'
                s = GlobalValues.indices[str(level)]
                m = GlobalValues.max_indices[str(level)]

                ids_child_element.text = code.replace('(:)', '[' + s + ']')

                self.generateParentsCode(level, child.text)
                self.printCode("#level=" + str(level), level)

                code_parameter = "len(self.ids." + child.text + "." + ids_child_element.get('name') + ')'

                parameter = m + ' = ' + code_parameter + '\n'
                self.printCode(parameter, level)
                self.printCode(s + '= 0', level)
                self.printCode ('while ' + s + ' < ' + m + ':' + '\n', level)

                code = "current_parent_" + str(level) + "= parent"  #keep in memory the parent of the current level
                self.printCode(code, level + 1)

                parentCode = "parent = ET.SubElement(parent, " + "'" + ids_child_element.get('name') + "'" + ")"
                self.printCode(parentCode, level + 1)


                code = "parent.set(" + "'index', str(" + s + "))"
                self.printCode(code, level + 1)
                code = "parent.set(" + "'dim', str(" + m + "))"
                self.printCode(code, level + 1)
                code = "parent.set(" + "'data_type', '" + data_type + "')"
                self.printCode(code, level + 1)

                lifecycle_status = ids_child_element.get('lifecycle_status')
                if lifecycle_status is not None:
                    code = "parent.set(" + "'lifecycle_status', '" + lifecycle_status + "')"
                    self.printCode(code, level + 1)

                documentation = ids_child_element.get('documentation')
                if documentation != None:
                    documentation = documentation.replace("'", "''")
                    documentation = documentation.replace("\n", "")
                    code = "parent.set(" + "'documentation', '" + documentation + "')"
                    self.printCode(code, level + 1)

                parentName = ids_child_element.get('name')
                if parentName != None:
                    parentName = parentName.replace("'", "''")
                    parentName = parentName.replace("\n", "")
                    code = "parent.set(" + "'name', '" + parentName + "')"
                    self.printCode(code, level + 1)

                if '(i' in ids_child_element.get('path_doc'): #this is an array of
                    parent_AOS = ids_child_element


                previousLevel[level] = s
                self.generateCodeForIDS(parent_AOS, ids_child_element, level + 1, previousLevel, parents, s, index, idsName)

                code = "parent = current_parent_" + str(level)  # keep the parent of the current level
                self.printCode(code, level + 1)

                # code = "if parent.tag == 'equilibrium':"
                # self.printCode(code, level + 1)
                # self.printCode(s + '+=' + str(self.time_step), level + 2)
                # self.printCode("else:", level + 1)
                # self.printCode(s + '+= 1', level + 2)
                self.printCode(s + '+= 1', level + 1)


            elif data_type == 'STR_0D' or data_type == 'INT_0D' or data_type == 'FLT_0D':
                #if level == 1:
                self.generateParentsCode(level, child.text)
                ids_child_element.text = "self.ids." + child.text + "." + ids_child_element.get('name')
                name_att = ids_child_element.get('name') + '_att_' + str(index)
                affect = name_att + '='
                self.printCode( affect + ids_child_element.text + '\n', level)
                parentCode = "node = ET.SubElement(parent, " + "'" + ids_child_element.get('name') + "'" + "+ '='" "+ str(" + name_att + "))"
                self.printCode(parentCode, level)

                # parentCode = "node = ET.SubElement(parent, " + "'" + ids_child_element.get(
                #     'name') + "'" + ")"
                # self.printCode(parentCode, level)
                # code = "node.add('" + ids_child_element.text + "')"
                # self.printCode(code, level)
                if (ids_child_element.get('name') == 'multiplicity'):
                    print('test')

                if (ids_child_element.get('path_doc') == 'element(i1)/multiplicity'):
                    print('test')

                code = "node.set(" + "'data_type', '" + data_type + "')"
                self.printCode(code, level)

                lifecycle_status = ids_child_element.get('lifecycle_status')
                if lifecycle_status is not None:
                    code = "node.set(" + "'lifecycle_status', '" + lifecycle_status + "')"
                    self.printCode(code, level)

                type = ids_child_element.get('type')
                code = "node.set(" + "'type', '" + type + "')"
                self.printCode(code, level)
                units = ids_child_element.get('units')
                if units != None:
                    code = "node.set(" + "'units', '" + units + "')"
                    self.printCode(code, level)
                documentation = ids_child_element.get('documentation')
                if documentation != None:
                    documentation = documentation.replace("'", "''")
                    documentation = documentation.replace("\n", "")
                    code = "node.set(" + "'documentation', '" + documentation + "')"
                    self.printCode(code, level)

                nodeName = ids_child_element.get('name')
                if nodeName != None:
                    nodeName = nodeName.replace("'", "''")
                    nodeName = nodeName.replace("\n", "")
                    code = "node.set(" + "'name', '" + nodeName + "')"
                    self.printCode(code, level)

            elif data_type == 'FLT_1D' or data_type == 'INT_1D' or data_type == 'flt_1d_type':
                #if level == 1:
                self.generateParentsCode(level, child.text)
                ids_child_element.text = "self.ids." + child.text + "." + ids_child_element.get('name')
                name = ids_child_element.get('name')
                name_att = name + '_att_' + str(index)
                affect = name_att + '='
                self.printCode(affect + ids_child_element.text + '\n', level)
                parentCode = "node = ET.SubElement(parent, '" + name + "')"
                self.printCode(parentCode, level)

                path_doc = ids_child_element.get('path_doc')


                itimeIndex = self.search_itime_index(path_doc)

                # if '(itime)' in path_doc:
                #     time_dependent = 1
                # else:
                #     time_dependent = 0

                lifecycle_status = ids_child_element.get('lifecycle_status')
                #if (ids_child_element.get('path_doc') == 'time_slice(itime)/profiles_1d/b_average_error_upper(:)'):
                #    print('test')
                if lifecycle_status is not None:
                    code = "node.set(" + "'lifecycle_status', '" + lifecycle_status + "')"
                    self.printCode(code, level)

                code = "node.set(" + "'itime_index', '" + str(itimeIndex) + "')"
                self.printCode(code, level)

                code = None
                coordinateName = None

                for c in range(1,10):
                    coordinateName = "coordinate" + str(c)
                    coordinateValue = ids_child_element.get(coordinateName)
                    if coordinateValue != None:
                        coordinate = coordinateValue.replace("(", "[")
                        coordinate = coordinate.replace(")", "]")
                        coordinate = coordinate.replace("/", ".")
                        coordinate = self.replaceIndices(coordinate)
                        code = "node.set(" + "'" + coordinateName + "'" + ", '" + coordinate + "')" #example: coordinateName='coordinate1', coordinate='flux_loop[i1].flux.time'
                        self.printCode(code, level)

                if coordinate !=  "1...N" and coordinate.endswith(".time"):
                    self.printCode("if self.ids." + idsName + ".ids_properties.homogeneous_time==1:", level)
                    coordinateName = "coordinate1"
                    coordinate = "time"
                    self.printCode("node.set(" + "'" + coordinateName + "'" + ", '" + coordinate + "')", level + 1)

                code = "node.set(" + "'data_type', '" + data_type + "')"
                self.printCode(code, level)

                units = ids_child_element.get('units')
                if units != None:
                    code = "node.set(" + "'units', '" + units + "')"
                    self.printCode(code, level)

                documentation = ids_child_element.get('documentation')
                if documentation != None:
                    documentation = documentation.replace("'","''")
                    documentation = documentation.replace("\n", "")
                    code = "node.set(" + "'documentation', '" + documentation + "')"
                    self.printCode(code, level)

                nodeName = ids_child_element.get('name')
                if nodeName != None:
                    nodeName = nodeName.replace("'", "''")
                    nodeName = nodeName.replace("\n", "")
                    code = "node.set(" + "'name', '" + nodeName + "')"
                    self.printCode(code, level)

                type = ids_child_element.get('type')
                code = "node.set(" + "'type', '" + type + "')"
                self.printCode(code, level)

                code = "nameNode = ET.SubElement(node, 'name')"
                self.printCode(code, level)
                code = "nameNode.set('data_type', 'STR_0D')"
                self.printCode(code, level)

                # code = "aos = ET.SubElement(node, 'aos')"
                # self.printCode(code, level)
                # code = "aos.text = " + "'" + ids_child_element.text + "'"
                # self.printCode(code, level)
                # code = "node.set(" + "'aos', '" + ids_child_element.text + "')"
                # self.printCode(code, level)


                for i in range(0, level - 1):
                    var_name = GlobalValues.indices[str(i+1)]
                    var_name_max = GlobalValues.max_indices[str(i + 1)]
                    code = "var_name = " + "'" + var_name + "'"
                    self.printCode(code, level)
                    code = "var_name_max = " + "'" + var_name_max + "'"
                    self.printCode(code, level)
                    code = "node.set(var_name" + ", str(" +  GlobalValues.indices[str(i+1)]  + "))"
                    self.printCode(code, level)
                    code = "node.set(var_name_max" + ", str(" + GlobalValues.max_indices[str(i + 1)] + "))"
                    self.printCode(code, level)

                code = "node.set(" + "'" + "aos_parents_count" + "'" + ", str(" + str(level - 1) + "))"
                self.printCode(code, level)

                aos = ids_child_element.text

                if itimeIndex != -1:
                    aos = aos.replace("[" + GlobalValues.indices[str(itimeIndex + 1)] + "]", "[itime]")

                code = "node.set(" + "'aos', '" + aos + "')"
                self.printCode(code, level)

                value = self.replaceIndices(ids_child_element.text)
                value = value.replace('self.', '')
                #value = value.replace('ids.', '')
                code = "nameNode.text = " + "'" + value + "'"
                self.printCode(code, level)

            elif data_type == 'FLT_2D' or data_type == 'INT_2D' or data_type == 'flt_2d_type' \
                or data_type == 'FLT_3D' or data_type == 'INT_3D' or data_type == 'flt_3d_type' \
                or data_type == 'FLT_4D' or data_type == 'INT_4D' or data_type == 'flt_4d_type' \
                or data_type == 'FLT_5D' or data_type == 'INT_5D' or data_type == 'flt_5d_type' \
                or data_type == 'FLT_6D' or data_type == 'INT_6D' or data_type == 'flt_6d_type' :

                #if level == 1:
                self.generateParentsCode(level, child.text)

                ids_child_element.text = "self.ids." + child.text + "." + ids_child_element.get('name')
                name = ids_child_element.get('name')
                name_att = name + '_att_' + str(index)
                affect = name_att + '='
                self.printCode(affect + ids_child_element.text + '\n', level)
                parentCode = "node = ET.SubElement(parent, '" + name + "')"
                self.printCode(parentCode, level)

                path_doc = ids_child_element.get('path_doc')


                itimeIndex = self.search_itime_index(path_doc)

                code = "node.set(" + "'itime_index', '" + str(itimeIndex) + "')"
                self.printCode(code, level)

                code = None
                coordinateName = None

                for c in range(1,10):
                    coordinateName = "coordinate" + str(c)
                    coordinateValue = ids_child_element.get(coordinateName)
                    if coordinateValue != None:
                        coordinate = coordinateValue.replace("(", "[")
                        coordinate = coordinate.replace(")", "]")
                        coordinate = coordinate.replace("/", ".")
                        coordinate = self.replaceIndices(coordinate)
                        code = "node.set(" + "'" + coordinateName + "'" + ", '" + coordinate + "')" #example: coordinateName='coordinate1', coordinate='flux_loop[i1].flux.time'
                        self.printCode(code, level)

                    coordinateSameAsName = "coordinate" + str(c) + "_same_as"
                    coordinateSameAsValue = ids_child_element.get(coordinateSameAsName)
                    if coordinateSameAsValue != None:
                        coordinate_same_as = coordinateSameAsValue.replace("(", "[")
                        coordinate_same_as = coordinate_same_as.replace(")", "]")
                        coordinate_same_as = coordinate_same_as.replace("/", ".")
                        coordinate_same_as = self.replaceIndices(coordinate_same_as)
                        code = "node.set(" + "'" + coordinateSameAsName + "'" + ", '" + coordinate_same_as + "')"  # example: coordinateName='coordinate1', coordinate='flux_loop[i1].flux.time'
                        self.printCode(code, level)

                # if coordinate !=  "1...N" and coordinate.endswith(".time"):
                #     self.printCode("if self.ids." + idsName + ".ids_properties.homogeneous_time==1:", level)
                #     coordinateName = "coordinate1"
                #     coordinate = "time"
                #     self.printCode("node.set(" + "'" + coordinateName + "'" + ", '" + coordinate + "')", level + 1)

                code = "node.set(" + "'data_type', '" + data_type + "')"
                self.printCode(code, level)

                lifecycle_status = ids_child_element.get('lifecycle_status')
                if lifecycle_status is not None:
                    code = "node.set(" + "'lifecycle_status', '" + lifecycle_status + "')"
                    self.printCode(code, level)

                units = ids_child_element.get('units')
                if units != None:
                    code = "node.set(" + "'units', '" + units + "')"
                    self.printCode(code, level)

                documentation = ids_child_element.get('documentation')
                if documentation != None:
                    documentation = documentation.replace("'","''")
                    documentation = documentation.replace("\n", "")
                    code = "node.set(" + "'documentation', '" + documentation + "')"
                    self.printCode(code, level)

                nodeName = ids_child_element.get('name')
                if nodeName != None:
                    nodeName = nodeName.replace("'", "''")
                    nodeName = nodeName.replace("\n", "")
                    code = "node.set(" + "'name', '" + nodeName + "')"
                    self.printCode(code, level)

                type = ids_child_element.get('type')
                code = "node.set(" + "'type', '" + type + "')"
                self.printCode(code, level)

                code = "nameNode = ET.SubElement(node, 'name')"
                self.printCode(code, level)
                code = "nameNode.set('data_type', 'STR_0D')"
                self.printCode(code, level)

                # code = "aos = ET.SubElement(node, 'aos')"
                # self.printCode(code, level)
                # code = "aos.text = " + "'" + ids_child_element.text + "'"
                # self.printCode(code, level)
                # code = "node.set(" + "'aos', '" + ids_child_element.text + "')"
                # self.printCode(code, level)


                for i in range(0, level - 1):
                    var_name = GlobalValues.indices[str(i+1)]
                    var_name_max = GlobalValues.max_indices[str(i + 1)]
                    code = "var_name = " + "'" + var_name + "'"
                    self.printCode(code, level)
                    code = "var_name_max = " + "'" + var_name_max + "'"
                    self.printCode(code, level)
                    code = "node.set(var_name" + ", str(" +  GlobalValues.indices[str(i+1)]  + "))"
                    self.printCode(code, level)
                    code = "node.set(var_name_max" + ", str(" + GlobalValues.max_indices[str(i + 1)] + "))"
                    self.printCode(code, level)

                code = "node.set(" + "'" + "aos_parents_count" + "'" + ", str(" + str(level - 1) + "))"
                self.printCode(code, level)

                aos = ids_child_element.text

                if itimeIndex != -1:
                    aos = aos.replace("[" + GlobalValues.indices[str(itimeIndex + 1)] + "]", "[itime]")

                code = "node.set(" + "'aos', '" + aos + "')"
                self.printCode(code, level)

                value = self.replaceIndices(ids_child_element.text)
                value = value.replace('self.', '')
                #value = value.replace('ids.', '')
                code = "nameNode.text = " + "'" + value + "'"
                self.printCode(code, level)




    def printCode(self, text, level):
        n = level + 1
        tabs = ''
        i = 0
        while i < n:
            tabs += '\t'
            i += 1

        #self.f.write(tabs + text.encode("utf-8") + "\n")
        self.f.write(tabs + text + "\n")
        # print tabs + text

    def replaceIndices(self, value):
        value = value.replace("[i]", "' + '[' + str(i) + ']")
        value = value.replace("[j]", "' + '[' + str(j) + ']")
        value = value.replace("[k]", "' + '[' + str(k) + ']")
        value = value.replace("[l]", "' + '[' + str(l) + ']")
        value = value.replace("[q]", "' + '[' + str(q) + ']")
        value = value.replace("[r]", "' + '[' + str(r) + ']")
        value = value.replace("[t]", "' + '[' + str(t) + ']")
        return value

#     def patchIndices(self, value):
#         value = value.replace("(i1)", "[i]")
#         value = value.replace("(i2)", "[j]")
#         value = value.replace("(i3)", "[k]")
#         value = value.replace("(i4)", "[l]")
#         value = value.replace("(i5)", "[q]")
#         value = value.replace("(i6)", "[r]")
#         value = value.replace("(i7)", "[t]")
#         #print "patched value : " + value
#         return value


    def search_itime_index(self, path_doc):

        itime_index = -1
        try:
            path_doc.index("(itime)")
        except:
            return itime_index

        itime_position = 0

        p_index = -1

        for c in range(1, 10):
            p = '(i' + str(c) + ')'
            try:
                p_index = path_doc.index(p)
            except:
                return itime_position
            if  itime_index > p_index:
                itime_position += 1



if __name__ == "__main__":

    print ("Starting code generation")
    GlobalOperations.checkEnvSettings()
    imas_versions = ["3.6.0", "3.7.0", "3.9.0", "3.9.1", "3.11.0", "3.12.0", "3.12.1", "3.15.0", "3.15.1", "3.16.0", "3.17.0", "3.17.1", "3.17.2", "3.18.0", "3.19.1", "3.20.0"]
    # imas_versions = ["3.19.1"]
    for v in imas_versions:
        dag = IMAS_DataAccessCodeGenerator(v)
    print ("End of code generation")
    print ("Do not forget to declare new code in the GeneratedClassFactory class")

