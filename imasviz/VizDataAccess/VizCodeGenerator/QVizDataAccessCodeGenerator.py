import xml.etree.ElementTree as elt_tree
import os
import sys
from imasviz.VizUtils import QVizGlobalOperations
from imasviz.VizUtils import QVizGlobalValues, QVizPreferences

sys.path.append((os.environ['VIZ_HOME']))


class QVizDataAccessCodeGenerator:
    patched_versions = ["3.7.0", "3.9.0", "3.9.1", "3.11.0", "3.12.0",
                        "3.12.1", "3.15.0", "3.15.1", "3.16.0", "3.17.0",
                        "3.17.1", "3.17.2", "3.18.0", "3.19.0", "3.19.1",
                        "3.20.0", "3.21.0", "3.21.1", "3.22.0", "3.23.1",
                        "3.23.2", "3.23.3", "3.24.0"]

    def __init__(self, dd_version):
        self.dd_version = dd_version
        self.time_step = 10
        path_generated_code = None

        className = QVizGlobalOperations.replaceDashesByUnderScores(dd_version)
        className = QVizGlobalOperations.replaceDotsByUnderScores(className)

        if QVizPreferences.Ignore_GGD == 1:

            className = "IDSDef_XMLParser_Partial_Generated_" + className
        else:
            className = "IDSDef_XMLParser_Full_Generated_" + className

        self.IDSDefFile = QVizGlobalOperations.getIDSDefFile(dd_version)

        if self.IDSDefFile is None:
            print("WARNING: no suitable IDSDef.xml file found for given IMAS version.")
        elif "/IDSDef.xml" in self.IDSDefFile:
            path_generated_code = os.environ['HOME'] + "/.imasviz/VizGeneratedCode"
            if not os.path.exists(path_generated_code):
                os.mkdir(path_generated_code)
                print("Directory ", path_generated_code, " created ")
            else:
                print("Directory ", path_generated_code, " already exists")

        print(f"The set generated code path: {path_generated_code}")

        XMLtreeIDSDef = elt_tree.parse(self.IDSDefFile)
        fileName = className + ".py"
        if os.environ['VIZ_HOME'] == '' or os.environ['VIZ_HOME'] is None:
            print("VIZ_HOME not defined! Exiting procedure.")
            sys.exit()

        if path_generated_code is not None:
            # Change current working directory
            os.chdir(path_generated_code)
            self.f = open(fileName, 'w')
            self.generateCode(XMLtreeIDSDef, className)
            self.f.close()

    def generateCode(self, XMLtreeIDSDef, className):

        root = XMLtreeIDSDef.getroot()
        i = 0
        for ids in root:
            name_att = ids.get('name')
            if name_att is None:
                continue
            # if name_att != 'equilibrium':
            #     continue
            print("Generating code for: " + name_att + " from: " +
                  self.IDSDefFile)

            ids.text = name_att
            if i == 0:
                self.printCode('#This class has been generated -- DO NOT MODIFY MANUALLY !!! --', -1)
                self.printCode('import xml.etree.ElementTree as ET', -1)
                self.printCode('import os, logging', -1)
                self.printCode('from PySide6.QtCore import QThread', -1)
                self.printCode('from PySide6.QtWidgets import QApplication, QInputDialog', -1)
                self.printCode('import imas', -1)
                self.printCode('import time', -1)
                self.printCode('from imasviz.VizGUI.VizTreeView.QVizResultEvent import QVizResultEvent', -1)
                self.printCode('\n', -1)

                self.printCode("class " + className + "(QThread):", -1)
                self.printCode(
                    "def __init__(self, uri, view, IDSName, occurrence=0, "
                    "viewLoadingStrategy=None, asynch=True):",
                    0)
                self.printCode("super(" + className + ", self).__init__()", 1)
                self.printCode("self.occurrence = occurrence", 1)
                self.printCode("self.view = view", 1)
                self.printCode("self.dataSource = None", 1)
                self.printCode("self.idsName = IDSName", 1)
                self.printCode("self.view.IDSNameSelected[occurrence] = IDSName", 1)
                self.printCode("self.loadData = True", 1)
                self.printCode("self.viewLoadingStrategy = viewLoadingStrategy", 1)
                self.printCode("self.asynch = asynch", 1)
                self.printCode("self.progressBar = None", 1)
                self.printCode("self.parameters = None", 1)
                self.printCode("self.ggd_warning_done = 0", 1)
                self.printCode('', -1)

                self.printCode('def setProgressBar(self, progressBar):', 0)
                self.printCode("self.progressBar = progressBar", 1)

                self.printCode('def run(self):', 0)

                self.printCode('try:', 1)

                self.printCode("idsData = None", 2)
                # print('-------->name_att')
                # print (name_att)
                for ids2 in root:
                    name_att2 = ids2.get('name')
                    if name_att2 is None:
                        continue
                    self.printCode("if self.idsName == '" + name_att2 + "':", 2)
                    self.printCode("message = 'Loading occurrence ' + str(int(self.occurrence)) + ' of ' +" +
                                   "'" + name_att2 + "' +  ' IDS'", 3)
                    self.printCode("logging.getLogger(self.dataSource.uri).info(message)", 3)
                    self.printCode('idsData, ids_instance = self.load_' + name_att2 + "(self.idsName, self.occurrence)" + '\n', 3)
                    self.printCode('if self.asynch:', 3)

                    self.printCode(
                        'QApplication.postEvent(self.view.parent, QVizResultEvent((self.idsName,ids_instance, self.occurrence, ' +
                        'idsData, self.progressBar, self.viewLoadingStrategy, self), self.view.parent.eventResultId), ' +
                        '1)', 4)
                    self.printCode("print ('waiting for view update...')" + '\n', 4)
                    self.printCode('else:', 3)
                    self.printCode(
                        'self.view.updateView(self.idsName, ids_instance, self.occurrence, idsData, self.viewLoadingStrategy)', 4)
                    self.printCode("self.progressBar.hide()", 4)

                self.printCode('except AttributeError as att_error:', 1)
                self.printCode('logging.getLogger(self.dataSource.uri).error(att_error, exc_info=True)', 2)
                self.printCode(
                    'logging.getLogger(self.dataSource.uri).error("An attribute error has occurred. This means that IMASViz is using a wrong data '
                    'parser ' +
                    'for the current IMAS data entry. This error can occur for IMAS data entries created with an old '
                    'version of the Access Layer.' +
                    ' Update the DD version (field ids_properties.version_put.data_dictionary) of ' +
                    'at least one IDS found in the current data entry, IMASViz will then pick the right parser.' +
                    ' ")', 2)
                self.printCode("self.progressBar.hide()", 2)
                self.printCode('except Exception as exception:', 1)
                self.printCode('logging.getLogger(self.dataSource.uri).error(exception, exc_info=True)', 2)
                self.printCode("self.progressBar.hide()", 2)
                self.printCode('\n', -1)

            self.printCode('def load_' + name_att + "(self, IDSName, occurrence):" + '\n', 0)
            self.printCode("self.dataSource.open()", 1)
            self.printCode(name_att + " = self.dataSource.get('" + name_att + "', occurrence)" , 1)
            #self.printCode(name_att + " = self.ids.get('"  + name_att + "', occurrence);", 1)  # get ids data from the database
            self.printCode("IDSName = '" + name_att + "'", 1)
            self.printCode("parents = []", 1)
            self.printCode('parent = ET.Element(' + "'" + ids.text + "'" + ')', 1)
            self.printCode('root = parent', 1)
            self.printCode('parents.append(parent)', 1)
            self.generateCodeForIDS(ids, 1, [], '', 0)
            self.printCode("return (root, " + name_att + ")", 1)
            self.printCode('', -1)
            i += 1

    def generateCodeForIDS(self, child, level, parents, s, index):

        for ids_child_element in child:
            index += 1
            data_type = ids_child_element.get('data_type')

            if data_type == 'structure':
                ids_child_element.text = child.text + '.' + ids_child_element.get('name')

                parentCode = "parent = ET.SubElement(parent, " + "'" + ids_child_element.get('name') + "'" + ")"
                self.printCode(parentCode, level)
                self.printCode('parents.append(parent)', level)

                units = ids_child_element.get('units')
                if units is not None:
                    code = "parent.set(" + "'units', '" + units + "')"
                    self.printCode(code, level)
                if units == "as_parent":
                    parent_units = child.get('units')
                    if parent_units is not None:
                        code = "parent.set(" + "'units', '" + parent_units + "')"
                        self.printCode(code, level)

                documentation = ids_child_element.get('documentation')
                if documentation is not None:
                    documentation = documentation.replace("&#34;", "'")
                    documentation = documentation.replace('"', "'")
                    documentation = documentation.replace("'", "''")
                    documentation = documentation.replace("\n", "")
                    if self.dd_version in QVizDataAccessCodeGenerator.patched_versions:
                        code = "parent.set(" + "'documentation', '" + documentation + "')"
                    else:
                        code = "parent.set(" + '"documentation", "' + documentation + '")'
                    self.printCode(code, level)

                parentName = ids_child_element.get('name')
                if parentName is not None:
                    parentName = parentName.replace("'", "''")
                    parentName = parentName.replace("\n", "")
                    code = "parent.set(" + "'name', '" + parentName + "')"
                    self.printCode(code, level)
                    code = "parent.set(" + "'data_type', '" + data_type + "')"
                    self.printCode(code, level)

                lifecycle_status = ids_child_element.get('lifecycle_status')
                if lifecycle_status is not None:
                    code = "parent.set(" + "'lifecycle_status', '" + lifecycle_status + "')"
                    self.printCode(code, level)

                self.generateCodeForIDS(ids_child_element, level, parents, s, index)

                code = "parents.pop() #remove the parent from the stack"
                self.printCode(code, level)
                self.printCode('parent = parents[-1]', level)

            elif data_type == 'struct_array':

                if QVizPreferences.Ignore_GGD == 1:
                    if ids_child_element.get('name') == "ggd" \
                            or ids_child_element.get('name').startswith("ggd_") \
                            or ids_child_element.get('name').endswith("_ggd"):
                        self.printCode("if self.ggd_warning_done == 0:", level)
                        self.printCode("self.ggd_warning_done = 1", level + 1)
                        self.printCode("logging.getLogger(self.dataSource.uri).warning('GGD structures have been ignored')", level + 1)
                        self.printCode("logging.getLogger(self.dataSource.uri).warning('Enable GGD structures parsing using a user preferences file. "
                                       "See Viz documentation for details, 2.9. "
                                       "Setting user preferences.')", level + 1)
                        continue

                code = child.text + "." + ids_child_element.get('name') + '(:)'
                s = QVizGlobalValues.indices[str(level)]
                m = QVizGlobalValues.max_indices[str(level)]

                ids_child_element.text = code.replace('(:)', '[' + s + ']')
                code_parameter = "len(" + child.text + "." + \
                                 ids_child_element.get('name') + ')'

                parameter = m + ' = ' + code_parameter + '\n'
                self.printCode(parameter, level)
                maxLimit = m + '_sup'
                parameter = maxLimit + ' = ' + m + '\n'
                self.printCode(parameter, level)
                self.printCode(s + '= 0', level)

                step = m + '_step'
                parameter = step + ' = 1' + '\n'
                self.printCode(parameter, level)

                self.printCode("minLimit = 0", level)

                dim = m

                time_slices = "-1"
                if ids_child_element.get('type') is not None and ids_child_element.get('type') == 'dynamic':
                    time_slices = "1"
                    self.printCode("if " + m + " > 0:", level)
                    self.printCode(
                        "if self.viewLoadingStrategy is None or self.viewLoadingStrategy.getIdentifier() == 1:",
                        level + 1)
                    parameter = maxLimit + ' = 1 #only first time slice is kept for the tree' + '\n'
                    self.printCode(parameter, level + 2)
                    self.printCode("elif self.viewLoadingStrategy.getIdentifier() == 2:", level + 1)
                    parameter = step + ' = 10 #only one time slice over 10 is displayed in the view' + '\n'
                    self.printCode(parameter, level + 2)
                    self.printCode("elif self.viewLoadingStrategy.getIdentifier() == 4:", level + 1)
                    self.printCode("minLimit = self.viewLoadingStrategy.getTimeIndex()", level + 2)
                    self.printCode("if minLimit >= " + maxLimit + ":", level + 2)
                    self.printCode("logging.getLogger(self.dataSource.uri).error('Bad input from user: time index too large.')", level + 3)
                    self.printCode("return", level + 3)
                    self.printCode(maxLimit + " = minLimit + 1", level + 2)
                    self.printCode("if self.viewLoadingStrategy is not None:", level + 1)
                    self.printCode("self.viewLoadingStrategy.setIDSIsDynamic(True)", level + 2)

                self.printCode('for ' + s + ' in range(minLimit,' + maxLimit + ',' + step + '):' + '\n', level)
                self.loop_content_for_struct_array(ids_child_element, s, level, dim, time_slices,
                                                   data_type, parents, index)

            elif data_type == 'STR_0D' or data_type == 'str_type' or data_type == 'INT_0D' or \
            data_type == 'int_type' or data_type == 'FLT_0D' or data_type == 'flt_type' or \
            data_type == 'CPX_0D' or data_type == 'cpx_type':

                
                ids_child_element.text = child.text + "." \
                                         + ids_child_element.get('name')


                name_att = ids_child_element.get('name') + '_att_' + str(index)
                affect = name_att + '='
                self.printCode(affect + ids_child_element.text + '\n', level)
                parentCode = "node = ET.SubElement(parent, " + "'" \
                             + ids_child_element.get('name') + "'" + "+ '='" "+ str(" \
                             + name_att + "))"
                self.printCode(parentCode, level)

                code = "node.set('content', " + ids_child_element.text + ")"
                self.printCode(code, level)

                code = "node.set(" + "'data_type', '" + data_type + "')"
                self.printCode(code, level)

                lifecycle_status = ids_child_element.get('lifecycle_status')
                if lifecycle_status is not None:
                    code = "node.set(" + "'lifecycle_status', '" \
                           + lifecycle_status + "')"
                    self.printCode(code, level)

                type = ids_child_element.get('type')
                code = "node.set(" + "'type', '" + type + "')"
                self.printCode(code, level)
                units = ids_child_element.get('units')
                if units is not None:
                    code = "node.set(" + "'units', '" + units + "')"
                    self.printCode(code, level)
                if units == "as_parent":
                    parent_units = child.get('units')
                    if parent_units is not None:
                        code = "node.set(" + "'units', '" + parent_units + "')"
                        self.printCode(code, level)

                documentation = ids_child_element.get('documentation')
                if documentation is not None:
                    documentation = documentation.replace("&#34;", "'")
                    documentation = documentation.replace('"', "'")
                    documentation = documentation.replace("'", "''")
                    documentation = documentation.replace("\n", "")
                    if self.dd_version in QVizDataAccessCodeGenerator.patched_versions:
                        code = "node.set(" + "'documentation', '" \
                               + documentation + "')"
                    else:
                        code = "node.set(" + '"documentation", "' \
                               + documentation + '")'
                    self.printCode(code, level)

                nodeName = ids_child_element.get('name')
                if nodeName is not None:
                    nodeName = nodeName.replace("'", "''")
                    nodeName = nodeName.replace("\n", "")
                    code = "node.set(" + "'name', '" + nodeName + "')"
                    self.printCode(code, level)

                code = "nameNode = ET.SubElement(node, 'name')"
                self.printCode(code, level)
                code = "nameNode.set('data_type', 'STR_0D')"
                self.printCode(code, level)
                value = self.replaceIndices(ids_child_element.text)
                value = value.replace('self.', '')
                value = value.replace('ids.', '')
                code = "nameNode.text = " + "'" + value + "'"
                self.printCode(code, level)

                path_doc = ids_child_element.get('path_doc')
                itimeIndex = self.search_itime_index(path_doc)
                code = "node.set(" + "'itime_index', '" + str(itimeIndex) + "')"
                self.printCode(code, level)
                parametrizedPath = child.text
                if itimeIndex != -1:
                    parametrizedPath = parametrizedPath.replace(
                        "[" + QVizGlobalValues.indices[str(itimeIndex + 1)] + "]", "[itime]")
                code = "node.set(" + "'parametrizedPath', '" + parametrizedPath + "')"
                self.printCode(code, level)

                for i in range(0, level - 1):
                    var_name = QVizGlobalValues.indices[str(i + 1)]
                    var_name_max = QVizGlobalValues.max_indices[str(i + 1)]
                    code = "var_name = " + "'" + var_name + "'"
                    self.printCode(code, level)
                    code = "var_name_max = " + "'" + var_name_max + "'"
                    self.printCode(code, level)
                    code = "node.set(var_name" + ", str(" \
                           + QVizGlobalValues.indices[str(i + 1)] + "))"
                    self.printCode(code, level)
                    code = "node.set(var_name_max" + ", str(" \
                           + QVizGlobalValues.max_indices[str(i + 1)] + "))"
                    self.printCode(code, level)

                code = "node.set(" + "'" + "aos_parents_count" + "'" \
                       + ", str(" + str(level - 1) + "))"
                self.printCode(code, level)

            elif data_type == 'FLT_1D' or data_type == 'INT_1D' or data_type == 'int_1d_type' or \
            data_type == 'flt_1d_type' or data_type == 'STR_1D' or \
            data_type == 'CPX_1D' or data_type == 'cplx_1d_type': 

                ids_child_element.text = child.text + "." \
                                         + ids_child_element.get('name')
                name = ids_child_element.get('name')
                name_att = name + '_att_' + str(index)
                affect = name_att + '='
                self.printCode(affect + ids_child_element.text + '\n', level)
                parentCode = "node = ET.SubElement(parent, '" + name + "')"
                self.printCode(parentCode, level)

                path_doc = ids_child_element.get('path_doc')
                itimeIndex = self.search_itime_index(path_doc)
                lifecycle_status = ids_child_element.get('lifecycle_status')

                if lifecycle_status is not None:
                    code = "node.set(" + "'lifecycle_status', '" \
                           + lifecycle_status + "')"
                    self.printCode(code, level)

                code = "node.set(" + "'itime_index', '" + str(itimeIndex) + "')"
                self.printCode(code, level)

                for c in range(1, 10):
                    coordinateName = "coordinate" + str(c)
                    coordinateValue = ids_child_element.get(coordinateName)
                    if coordinateValue is not None:
                        coordinate = QVizGlobalOperations.makeIMASPath(coordinateValue)
                        coordinate = self.replaceIndices(coordinate)
                        code = "node.set(" + "'" + coordinateName + "'" \
                               + ", '" + coordinate + "')"  # example: coordinateName='coordinate1',
                        # coordinate='flux_loop[i1].flux.time'
                        self.printCode(code, level)

                code = "node.set(" + "'data_type', '" + data_type + "')"
                self.printCode(code, level)

                units = ids_child_element.get('units')

                if units is not None:
                    code = "node.set(" + "'units', '" + units + "')"
                    self.printCode(code, level)
                if units == "as_parent":
                    parent_units = child.get('units')
                    if parent_units is not None:
                        code = "node.set(" + "'units', '" + parent_units + "')"
                        self.printCode(code, level)

                nodeName = ids_child_element.get('name')
                if nodeName is not None:
                    nodeName = nodeName.replace("'", "''")
                    nodeName = nodeName.replace("\n", "")

                    code = "node.set(" + "'name', '" + nodeName + "')"
                    self.printCode(code, level)

                documentation = ids_child_element.get('documentation')
                if documentation is not None:
                    documentation = documentation.replace("&#34;", "'")
                    documentation = documentation.replace('"', "'")
                    documentation = documentation.replace("'", "''")
                    documentation = documentation.replace("\n", "")
                    if self.dd_version in QVizDataAccessCodeGenerator.patched_versions:
                        code = "node.set(" + "'documentation', '" \
                               + documentation + "')"
                    else:
                        code = "node.set(" + '"documentation", "' \
                               + documentation + '")'
                    self.printCode(code, level)

                type = ids_child_element.get('type')
                code = "node.set(" + "'type', '" + type + "')"
                self.printCode(code, level)

                code = "nameNode = ET.SubElement(node, 'name')"
                self.printCode(code, level)
                code = "nameNode.set('data_type', 'STR_0D')"
                self.printCode(code, level)

                for i in range(0, level - 1):
                    var_name = QVizGlobalValues.indices[str(i + 1)]
                    var_name_max = QVizGlobalValues.max_indices[str(i + 1)]
                    code = "var_name = " + "'" + var_name + "'"
                    self.printCode(code, level)
                    code = "var_name_max = " + "'" + var_name_max + "'"
                    self.printCode(code, level)
                    code = "node.set(var_name" + ", str(" \
                           + QVizGlobalValues.indices[str(i + 1)] + "))"
                    self.printCode(code, level)
                    code = "node.set(var_name_max" + ", str(" \
                           + QVizGlobalValues.max_indices[str(i + 1)] + "))"
                    self.printCode(code, level)

                code = "node.set(" + "'" + "aos_parents_count" + "'" + ", str(" + str(level - 1) + "))"
                self.printCode(code, level)

                parametrizedPath = child.text

                if itimeIndex != -1:
                    parametrizedPath = parametrizedPath.replace(
                        "[" + QVizGlobalValues.indices[str(itimeIndex + 1)] + "]", "[itime]")

                code = "node.set(" + "'parametrizedPath', '" + parametrizedPath + "')"
                self.printCode(code, level)

                value = self.replaceIndices(ids_child_element.text)
                value = value.replace('self.', '')
                value = value.replace('ids.', '')
                code = "nameNode.text = " + "'" + value + "'"
                self.printCode(code, level)


            elif data_type == 'FLT_2D' or data_type == 'INT_2D' \
                    or data_type == 'flt_2d_type' or data_type == 'FLT_3D' \
                    or data_type == 'INT_3D' or data_type == 'flt_3d_type' \
                    or data_type == 'FLT_4D' or data_type == 'INT_4D' \
                    or data_type == 'flt_4d_type' or data_type == 'FLT_5D' \
                    or data_type == 'INT_5D' or data_type == 'flt_5d_type' \
                    or data_type == 'FLT_6D' or data_type == 'INT_6D' \
                    or data_type == 'flt_6d_type' \
                    or  data_type == 'CPX_2D' or data_type == 'CPX_3D' \
                    or  data_type == 'CPX_4D' or data_type == 'CPX_5D' \
                    or  data_type == 'CPX_6D':

                # self.generateParentsCode(level, child.text)

                ids_child_element.text = child.text + "." \
                                         + ids_child_element.get('name')
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

                for c in range(1, 10):
                    coordinateName = "coordinate" + str(c)
                    coordinateValue = ids_child_element.get(coordinateName)
                    if coordinateValue is not None:
                        coordinate = QVizGlobalOperations.makeIMASPath(coordinateValue)
                        coordinate = self.replaceIndices(coordinate)
                        code = "node.set(" + "'" + coordinateName + "'" \
                               + ", '" + coordinate + "')"  # example: coordinateName='coordinate1',
                        # coordinate='flux_loop[i1].flux.time'
                        self.printCode(code, level)

                    coordinateSameAsName = "coordinate" + str(c) + "_same_as"
                    coordinateSameAsValue = ids_child_element.get(coordinateSameAsName)
                    if coordinateSameAsValue is not None:
                        coordinate_same_as = QVizGlobalOperations.makeIMASPath(coordinateSameAsValue)
                        coordinate_same_as = self.replaceIndices(coordinate_same_as)
                        code = "node.set(" + "'" + coordinateSameAsName + "'" \
                               + ", '" + coordinate_same_as + "')"  # example: coordinateName='coordinate1',
                        # coordinate='flux_loop[i1].flux.time'
                        self.printCode(code, level)

                code = "node.set(" + "'data_type', '" + data_type + "')"
                self.printCode(code, level)

                lifecycle_status = ids_child_element.get('lifecycle_status')
                if lifecycle_status is not None:
                    code = "node.set(" + "'lifecycle_status', '" + \
                           lifecycle_status + "')"
                    self.printCode(code, level)

                nodeName = ids_child_element.get('name')
                if nodeName is not None:
                    nodeName = nodeName.replace("'", "''")
                    nodeName = nodeName.replace("\n", "")
                    code = "node.set(" + "'name', '" + nodeName + "')"
                    self.printCode(code, level)

                units = ids_child_element.get('units')
                if units is not None:
                    code = "node.set(" + "'units', '" + units + "')"
                    self.printCode(code, level)
                if units == "as_parent":
                    parent_units = child.get('units')
                    if parent_units is not None:
                        code = "node.set(" + "'units', '" + parent_units + "')"
                        self.printCode(code, level)

                documentation = ids_child_element.get('documentation')
                if documentation is not None:
                    documentation = documentation.replace("&#34;", "'")
                    documentation = documentation.replace('"', "'")
                    documentation = documentation.replace("'", "''")
                    documentation = documentation.replace("\n", "")
                    if self.dd_version in QVizDataAccessCodeGenerator.patched_versions:
                        code = "node.set(" + "'documentation', '" \
                               + documentation + "')"
                    else:
                        code = "node.set(" + '"documentation", "' \
                               + documentation + '")'
                    self.printCode(code, level)

                type = ids_child_element.get('type')
                code = "node.set(" + "'type', '" + type + "')"
                self.printCode(code, level)

                code = "nameNode = ET.SubElement(node, 'name')"
                self.printCode(code, level)
                code = "nameNode.set('data_type', 'STR_0D')"
                self.printCode(code, level)

                for i in range(0, level - 1):
                    var_name = QVizGlobalValues.indices[str(i + 1)]
                    var_name_max = QVizGlobalValues.max_indices[str(i + 1)]
                    code = "var_name = " + "'" + var_name + "'"
                    self.printCode(code, level)
                    code = "var_name_max = " + "'" + var_name_max + "'"
                    self.printCode(code, level)
                    code = "node.set(var_name" + ", str(" \
                           + QVizGlobalValues.indices[str(i + 1)] + "))"
                    self.printCode(code, level)
                    code = "node.set(var_name_max" + ", str(" \
                           + QVizGlobalValues.max_indices[str(i + 1)] + "))"
                    self.printCode(code, level)

                code = "node.set(" + "'" + "aos_parents_count" + "'" \
                       + ", str(" + str(level - 1) + "))"
                self.printCode(code, level)

                parametrizedPath = child.text

                if itimeIndex != -1:
                    parametrizedPath = parametrizedPath.replace(
                        "[" + QVizGlobalValues.indices[str(itimeIndex + 1)] + "]", "[itime]")

                code = "node.set(" + "'parametrizedPath', '" \
                       + parametrizedPath + "')"
                self.printCode(code, level)

                value = self.replaceIndices(ids_child_element.text)
                value = value.replace('self.', '')
                value = value.replace('ids.', '')
                code = "nameNode.text = " + "'" + value + "'"
                self.printCode(code, level)

            else:
                print("datatype=", ids_child_element.get('data_type'))
                print('unrecognized node...', ids_child_element.attrib['name'])


    def loop_content_for_struct_array(self, ids_child_element, s, level, dim, time_slices, data_type,
                                      parents, index):
        parentCode = "parent = ET.SubElement(parent, " + "'" \
                     + ids_child_element.get('name') + "'" + ")"
        self.printCode(parentCode, level + 1)

        code = "parents.append(parent)"  # keep in memory the parent of the current level
        self.printCode(code, level + 1)

        code = "parent.set(" + "'index', str(" + s + "))"
        self.printCode(code, level + 1)
        code = "parent.set(" + "'dim', str(" + dim + "))"
        self.printCode(code, level + 1)
        code = "parent.set(" + "'limited_nodes', str(" + time_slices + "))"
        self.printCode(code, level + 1)
        code = "parent.set(" + "'data_type', '" + data_type + "')"
        self.printCode(code, level + 1)

        lifecycle_status = ids_child_element.get('lifecycle_status')
        if lifecycle_status is not None:
            code = "parent.set(" + "'lifecycle_status', '" \
                   + lifecycle_status + "')"
            self.printCode(code, level + 1)

        documentation = ids_child_element.get('documentation')
        if documentation is not None:
            documentation = documentation.replace("&#34;", "'")
            documentation = documentation.replace('"', "'")
            documentation = documentation.replace("'", "''")
            documentation = documentation.replace("\n", "")
            if self.dd_version in QVizDataAccessCodeGenerator.patched_versions:
                code = "parent.set(" + "'documentation', '" \
                       + documentation + "')"
            else:
                code = "parent.set(" + '"documentation", "' \
                       + documentation + '")'
            self.printCode(code, level + 1)

        parentName = ids_child_element.get('name')
        if parentName is not None:
            parentName = parentName.replace("'", "''")
            parentName = parentName.replace("\n", "")
            code = "parent.set(" + "'name', '" + parentName + "')"
            self.printCode(code, level + 1)

        self.generateCodeForIDS(ids_child_element,
                                level + 1, parents, s,
                                index)

        code = "parents.pop() #remove the parent from the stack"
        self.printCode(code, level + 1)
        self.printCode("parent = parents[-1]", level + 1)
        self.printCode(s + '+= 1', level + 1)

    def printCode(self, text, level):
        n = level + 1
        tabs = ''
        i = 0
        while i < n:
            tabs += '\t'
            i += 1

        # self.f.write(tabs + text.encode("utf-8") + "\n")
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

    def search_itime_index(self, path_doc):

        itime_index = -1
        try:
            itime_index = path_doc.index("(itime)")
        except:
            return itime_index  # 'itime' not found

        s = path_doc[0:itime_index]
        itime_position = 0
        p_index = -1

        for c in range(1, 10):
            p = '(i' + str(c) + ')'
            try:
                p_index = s.index(p)
                itime_position += 1
            except:
                return itime_position


if __name__ == "__main__":

    # print("Starting code generation")
    # QVizGlobalOperations.checkEnvSettings_generator()
    # imas_versions = ["3.23.3", "3.24.0", "3.25.0", "3.26.0", "3.27.0"]

    # print("Generating full parsers...")
    # for v in imas_versions:
    #     QVizPreferences.Ignore_GGD = 0
    #     dag = QVizDataAccessCodeGenerator(v)

    # print("Generating parsers ignoring GGD structures...")
    # for v in imas_versions:
    #     QVizPreferences.Ignore_GGD = 1
    #     dag = QVizDataAccessCodeGenerator(v)
    QVizGlobalOperations.checkEnvSettings_generator()
    QVizPreferences.Ignore_GGD = 1
    dag = QVizDataAccessCodeGenerator('3.39.0')

    print("End of code generation")
    # Note: Do not forget to declare new code in the QVizGeneratedClassFactory
    #       class
