#This class has been generated -- DO NOT MODIFY MANUALLY !!! --
import time
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication

from imasviz.VizGUI.VizTreeView.QtResultEvent import ResultEvent


class ETNativeDataTree_Generated_3_15_1_pyqt_testing(QThread):
	def __init__(self, userName, imasDbName, shotNumber, runNumber, view, occurrence=0, pathsList = None, async=True):
		super(ETNativeDataTree_Generated_3_15_1_pyqt_testing, self).__init__()
		print('*thread __init__() launched.')

		self.occurrence = occurrence
		self.view = view
		self.ids = None
		self.idsName = self.view.IDSNameSelected
		self.pathsList = pathsList
		self.async = async

	def run(self):
		print('*thread run() launched.')

	# 	self.exec()

	# def exec(self):
	# 	print('*thread exec() launched.')

		idsData = None
		if self.idsName == 'magnetics':
			self.view.log.info('Loading occurrence ' + str(self.occurrence) + ' of IDS ' + self.idsName + '...')
			t1 = time.time()
			self.ids.magnetics.get(self.occurrence)
			t2 = time.time()
			print('imas get took ' + str(t2 - t1) + ' seconds')
			idsData = self.load_magnetics(self.idsName, self.occurrence)

			t3 = time.time()
			print('in memory xml object creation took ' + str(t3 - t2) + ' seconds')
			if self.async==True:
				print('* thread check 1')
                # QCoreApplication.postEvent(self.view.parent, ResultEvent((self.idsName, self.occurrence, idsData, self.pathsList), self.view.parent.eventResultId))
				QApplication.postEvent(self.view.parent, ResultEvent((self.idsName, self.occurrence, idsData, self.pathsList, self), self.view.parent.eventResultId))
				print('* thread check 2')
				print ('waiting for view update...')

				print('self.view.parent : ', self.view.parent)
				print('self.idsName : ', self.idsName)
				print('self.occurrence: ', self.occurrence)
				print('idsData : ', idsData)
				print('self.pathsList : ', self.pathsList)
				print('self.view.parent.eventResultId : ', self.view.parent.eventResultId)
			else:
				self.view.parent.updateView(self.idsName, self.occurrence, idsData, self.pathsList)

	def load_magnetics(self, IDSName, occurrence):

		IDSName = 'magnetics'
		parents = {}
		parent = ET.Element('magnetics')
		if parents.get('magnetics') != None :
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		parent = ET.SubElement(parent, 'ids_properties')
		parent.set('documentation', 'Interface Data Structure properties. This element identifies the node above as an IDS')
		parent.set('name', 'ids_properties')
		if parents.get('magnetics.ids_properties') != None :
			parent = parents['magnetics.ids_properties']
		else:
			parents['magnetics.ids_properties'] = parent
		comment_att_2=self.ids.magnetics.ids_properties.comment

		node = ET.SubElement(parent, 'comment'+ '='+ str(comment_att_2))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'Any comment describing the content of this IDS')
		node.set('name', 'comment')
		if parents.get('magnetics.ids_properties') != None :
			parent = parents['magnetics.ids_properties']
		else:
			parents['magnetics.ids_properties'] = parent
		homogeneous_time_att_3=self.ids.magnetics.ids_properties.homogeneous_time

		node = ET.SubElement(parent, 'homogeneous_time'+ '='+ str(homogeneous_time_att_3))
		node.set('data_type', 'INT_0D')
		node.set('type', 'constant')
		node.set('documentation', '1 if the time of this IDS is homogeneous. In this case, the time values for this IDS are stored in ../time just below the root of this IDS. Otherwise, the time values are stored in the various time fields at lower levels in the tree.')
		node.set('name', 'homogeneous_time')
		if parents.get('magnetics.ids_properties') != None :
			parent = parents['magnetics.ids_properties']
		else:
			parents['magnetics.ids_properties'] = parent
		source_att_4=self.ids.magnetics.ids_properties.source

		node = ET.SubElement(parent, 'source'+ '='+ str(source_att_4))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'Source of the data (any comment describing the origin of the data : code, path to diagnostic signals, processing method, ...)')
		node.set('name', 'source')
		if parents.get('magnetics.ids_properties') != None :
			parent = parents['magnetics.ids_properties']
		else:
			parents['magnetics.ids_properties'] = parent
		provider_att_5=self.ids.magnetics.ids_properties.provider

		node = ET.SubElement(parent, 'provider'+ '='+ str(provider_att_5))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'Name of the person in charge of producing this data')
		node.set('name', 'provider')
		if parents.get('magnetics.ids_properties') != None :
			parent = parents['magnetics.ids_properties']
		else:
			parents['magnetics.ids_properties'] = parent
		creation_date_att_6=self.ids.magnetics.ids_properties.creation_date

		node = ET.SubElement(parent, 'creation_date'+ '='+ str(creation_date_att_6))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'Date at which this data has been produced')
		node.set('name', 'creation_date')
		if parents.get('magnetics') != None :
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		#level=1
		N = len(self.ids.magnetics.flux_loop)

		i= 0
		while i < N:

			current_parent_1= parent
			parent = ET.SubElement(parent, 'flux_loop')
			parent.set('index', str(i))
			parent.set('dim', str(N))
			parent.set('data_type', 'struct_array')
			parent.set('documentation', 'Flux loops; partial flux loops can be described')
			parent.set('name', 'flux_loop')
			if parents.get('magnetics.flux_loop' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.flux_loop' + '[' + str(i) + ']']
			else:
				parents['magnetics.flux_loop' + '[' + str(i) + ']'] = parent
			name_att_3=self.ids.magnetics.flux_loop[i].name

			node = ET.SubElement(parent, 'name'+ '='+ str(name_att_3))
			node.set('data_type', 'STR_0D')
			node.set('type', 'static')
			node.set('documentation', 'Name of the flux loop')
			node.set('name', 'name')
			if parents.get('magnetics.flux_loop' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.flux_loop' + '[' + str(i) + ']']
			else:
				parents['magnetics.flux_loop' + '[' + str(i) + ']'] = parent
			identifier_att_4=self.ids.magnetics.flux_loop[i].identifier

			node = ET.SubElement(parent, 'identifier'+ '='+ str(identifier_att_4))
			node.set('data_type', 'STR_0D')
			node.set('type', 'static')
			node.set('documentation', 'ID of the flux loop')
			node.set('name', 'identifier')
			if parents.get('magnetics.flux_loop' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.flux_loop' + '[' + str(i) + ']']
			else:
				parents['magnetics.flux_loop' + '[' + str(i) + ']'] = parent
			#level=2
			M = len(self.ids.magnetics.flux_loop[i].position)

			j= 0
			while j < M:

				current_parent_2= parent
				parent = ET.SubElement(parent, 'position')
				parent.set('index', str(j))
				parent.set('dim', str(M))
				parent.set('data_type', 'struct_array')
				parent.set('documentation', 'List of (R,Z,phi) points defining the position of the loop (see data structure documentation FLUXLOOPposition.pdf)')
				parent.set('name', 'position')
				if parents.get('magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']') != None :
					parent = parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']']
				else:
					parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']'] = parent
				r_att_6=self.ids.magnetics.flux_loop[i].position[j].r

				node = ET.SubElement(parent, 'r'+ '='+ str(r_att_6))
				node.set('data_type', 'FLT_0D')
				node.set('type', 'static')
				node.set('units', 'm')
				node.set('documentation', 'Major radius')
				node.set('name', 'r')
				if parents.get('magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']') != None :
					parent = parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']']
				else:
					parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']'] = parent
				r_error_upper_att_7=self.ids.magnetics.flux_loop[i].position[j].r_error_upper

				node = ET.SubElement(parent, 'r_error_upper'+ '='+ str(r_error_upper_att_7))
				node.set('data_type', 'FLT_0D')
				node.set('type', 'static')
				node.set('units', 'm')
				node.set('documentation', 'Upper error for "r"')
				node.set('name', 'r_error_upper')
				if parents.get('magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']') != None :
					parent = parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']']
				else:
					parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']'] = parent
				r_error_lower_att_8=self.ids.magnetics.flux_loop[i].position[j].r_error_lower

				node = ET.SubElement(parent, 'r_error_lower'+ '='+ str(r_error_lower_att_8))
				node.set('data_type', 'FLT_0D')
				node.set('type', 'static')
				node.set('units', 'm')
				node.set('documentation', 'Lower error for "r"')
				node.set('name', 'r_error_lower')
				if parents.get('magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']') != None :
					parent = parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']']
				else:
					parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']'] = parent
				z_att_10=self.ids.magnetics.flux_loop[i].position[j].z

				node = ET.SubElement(parent, 'z'+ '='+ str(z_att_10))
				node.set('data_type', 'FLT_0D')
				node.set('type', 'static')
				node.set('units', 'm')
				node.set('documentation', 'Height')
				node.set('name', 'z')
				if parents.get('magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']') != None :
					parent = parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']']
				else:
					parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']'] = parent
				z_error_upper_att_11=self.ids.magnetics.flux_loop[i].position[j].z_error_upper

				node = ET.SubElement(parent, 'z_error_upper'+ '='+ str(z_error_upper_att_11))
				node.set('data_type', 'FLT_0D')
				node.set('type', 'static')
				node.set('units', 'm')
				node.set('documentation', 'Upper error for "z"')
				node.set('name', 'z_error_upper')
				if parents.get('magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']') != None :
					parent = parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']']
				else:
					parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']'] = parent
				z_error_lower_att_12=self.ids.magnetics.flux_loop[i].position[j].z_error_lower

				node = ET.SubElement(parent, 'z_error_lower'+ '='+ str(z_error_lower_att_12))
				node.set('data_type', 'FLT_0D')
				node.set('type', 'static')
				node.set('units', 'm')
				node.set('documentation', 'Lower error for "z"')
				node.set('name', 'z_error_lower')
				if parents.get('magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']') != None :
					parent = parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']']
				else:
					parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']'] = parent
				phi_att_14=self.ids.magnetics.flux_loop[i].position[j].phi

				node = ET.SubElement(parent, 'phi'+ '='+ str(phi_att_14))
				node.set('data_type', 'FLT_0D')
				node.set('type', 'static')
				node.set('units', 'rad')
				node.set('documentation', 'Toroidal angle')
				node.set('name', 'phi')
				if parents.get('magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']') != None :
					parent = parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']']
				else:
					parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']'] = parent
				phi_error_upper_att_15=self.ids.magnetics.flux_loop[i].position[j].phi_error_upper

				node = ET.SubElement(parent, 'phi_error_upper'+ '='+ str(phi_error_upper_att_15))
				node.set('data_type', 'FLT_0D')
				node.set('type', 'static')
				node.set('units', 'rad')
				node.set('documentation', 'Upper error for "phi"')
				node.set('name', 'phi_error_upper')
				if parents.get('magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']') != None :
					parent = parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']']
				else:
					parents['magnetics.flux_loop' + '[' + str(i) + '].position' + '[' + str(j) + ']'] = parent
				phi_error_lower_att_16=self.ids.magnetics.flux_loop[i].position[j].phi_error_lower

				node = ET.SubElement(parent, 'phi_error_lower'+ '='+ str(phi_error_lower_att_16))
				node.set('data_type', 'FLT_0D')
				node.set('type', 'static')
				node.set('units', 'rad')
				node.set('documentation', 'Lower error for "phi"')
				node.set('name', 'phi_error_lower')
				parent = current_parent_2
				j+= 1
			if parents.get('magnetics.flux_loop' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.flux_loop' + '[' + str(i) + ']']
			else:
				parents['magnetics.flux_loop' + '[' + str(i) + ']'] = parent
			parent = ET.SubElement(parent, 'flux')
			parent.set('documentation', 'Measured flux')
			parent.set('name', 'flux')
			if parents.get('magnetics.flux_loop' + '[' + str(i) + '].flux') != None :
				parent = parents['magnetics.flux_loop' + '[' + str(i) + '].flux']
			else:
				parents['magnetics.flux_loop' + '[' + str(i) + '].flux'] = parent
			data_att_7=self.ids.magnetics.flux_loop[i].flux.data

			node = ET.SubElement(parent, 'data')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'flux_loop[i1].flux.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'Wb')
			node.set('documentation', 'Measured flux')
			node.set('name', 'data')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.flux_loop[i].flux.data')
			nameNode.text = 'ids.magnetics.flux_loop' + '[' + str(i) + '].flux.data'
			if parents.get('magnetics.flux_loop' + '[' + str(i) + '].flux') != None :
				parent = parents['magnetics.flux_loop' + '[' + str(i) + '].flux']
			else:
				parents['magnetics.flux_loop' + '[' + str(i) + '].flux'] = parent
			data_error_upper_att_8=self.ids.magnetics.flux_loop[i].flux.data_error_upper

			node = ET.SubElement(parent, 'data_error_upper')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'flux_loop[i1].flux.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'Wb')
			node.set('documentation', 'Upper error for "data"')
			node.set('name', 'data_error_upper')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.flux_loop[i].flux.data_error_upper')
			nameNode.text = 'ids.magnetics.flux_loop' + '[' + str(i) + '].flux.data_error_upper'
			if parents.get('magnetics.flux_loop' + '[' + str(i) + '].flux') != None :
				parent = parents['magnetics.flux_loop' + '[' + str(i) + '].flux']
			else:
				parents['magnetics.flux_loop' + '[' + str(i) + '].flux'] = parent
			data_error_lower_att_9=self.ids.magnetics.flux_loop[i].flux.data_error_lower

			node = ET.SubElement(parent, 'data_error_lower')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'flux_loop[i1].flux.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'Wb')
			node.set('documentation', 'Lower error for "data"')
			node.set('name', 'data_error_lower')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.flux_loop[i].flux.data_error_lower')
			nameNode.text = 'ids.magnetics.flux_loop' + '[' + str(i) + '].flux.data_error_lower'
			if parents.get('magnetics.flux_loop' + '[' + str(i) + '].flux') != None :
				parent = parents['magnetics.flux_loop' + '[' + str(i) + '].flux']
			else:
				parents['magnetics.flux_loop' + '[' + str(i) + '].flux'] = parent
			time_att_11=self.ids.magnetics.flux_loop[i].flux.time

			node = ET.SubElement(parent, 'time')
			node.set('itime_index', '-1')
			node.set('coordinate1', '1...N')
			node.set('data_type', 'flt_1d_type')
			node.set('documentation', 'Generic time [s]')
			node.set('name', 'time')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.flux_loop[i].flux.time')
			nameNode.text = 'ids.magnetics.flux_loop' + '[' + str(i) + '].flux.time'
			parent = current_parent_1
			i+= 1
		if parents.get('magnetics') != None :
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		#level=1
		N = len(self.ids.magnetics.bpol_probe)

		i= 0
		while i < N:

			current_parent_1= parent
			parent = ET.SubElement(parent, 'bpol_probe')
			parent.set('index', str(i))
			parent.set('dim', str(N))
			parent.set('data_type', 'struct_array')
			parent.set('documentation', 'Poloidal field probes')
			parent.set('name', 'bpol_probe')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			name_att_4=self.ids.magnetics.bpol_probe[i].name

			node = ET.SubElement(parent, 'name'+ '='+ str(name_att_4))
			node.set('data_type', 'STR_0D')
			node.set('type', 'static')
			node.set('documentation', 'Name of the probe')
			node.set('name', 'name')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			identifier_att_5=self.ids.magnetics.bpol_probe[i].identifier

			node = ET.SubElement(parent, 'identifier'+ '='+ str(identifier_att_5))
			node.set('data_type', 'STR_0D')
			node.set('type', 'static')
			node.set('documentation', 'ID of the probe')
			node.set('name', 'identifier')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			parent = ET.SubElement(parent, 'position')
			parent.set('documentation', 'R, Z, Phi position of the coil centre')
			parent.set('name', 'position')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].position') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].position']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].position'] = parent
			r_att_7=self.ids.magnetics.bpol_probe[i].position.r

			node = ET.SubElement(parent, 'r'+ '='+ str(r_att_7))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm')
			node.set('documentation', 'Major radius')
			node.set('name', 'r')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].position') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].position']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].position'] = parent
			r_error_upper_att_8=self.ids.magnetics.bpol_probe[i].position.r_error_upper

			node = ET.SubElement(parent, 'r_error_upper'+ '='+ str(r_error_upper_att_8))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm')
			node.set('documentation', 'Upper error for "r"')
			node.set('name', 'r_error_upper')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].position') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].position']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].position'] = parent
			r_error_lower_att_9=self.ids.magnetics.bpol_probe[i].position.r_error_lower

			node = ET.SubElement(parent, 'r_error_lower'+ '='+ str(r_error_lower_att_9))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm')
			node.set('documentation', 'Lower error for "r"')
			node.set('name', 'r_error_lower')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].position') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].position']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].position'] = parent
			z_att_11=self.ids.magnetics.bpol_probe[i].position.z

			node = ET.SubElement(parent, 'z'+ '='+ str(z_att_11))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm')
			node.set('documentation', 'Height')
			node.set('name', 'z')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].position') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].position']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].position'] = parent
			z_error_upper_att_12=self.ids.magnetics.bpol_probe[i].position.z_error_upper

			node = ET.SubElement(parent, 'z_error_upper'+ '='+ str(z_error_upper_att_12))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm')
			node.set('documentation', 'Upper error for "z"')
			node.set('name', 'z_error_upper')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].position') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].position']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].position'] = parent
			z_error_lower_att_13=self.ids.magnetics.bpol_probe[i].position.z_error_lower

			node = ET.SubElement(parent, 'z_error_lower'+ '='+ str(z_error_lower_att_13))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm')
			node.set('documentation', 'Lower error for "z"')
			node.set('name', 'z_error_lower')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].position') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].position']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].position'] = parent
			phi_att_15=self.ids.magnetics.bpol_probe[i].position.phi

			node = ET.SubElement(parent, 'phi'+ '='+ str(phi_att_15))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'rad')
			node.set('documentation', 'Toroidal angle')
			node.set('name', 'phi')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].position') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].position']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].position'] = parent
			phi_error_upper_att_16=self.ids.magnetics.bpol_probe[i].position.phi_error_upper

			node = ET.SubElement(parent, 'phi_error_upper'+ '='+ str(phi_error_upper_att_16))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'rad')
			node.set('documentation', 'Upper error for "phi"')
			node.set('name', 'phi_error_upper')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].position') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].position']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].position'] = parent
			phi_error_lower_att_17=self.ids.magnetics.bpol_probe[i].position.phi_error_lower

			node = ET.SubElement(parent, 'phi_error_lower'+ '='+ str(phi_error_lower_att_17))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'rad')
			node.set('documentation', 'Lower error for "phi"')
			node.set('name', 'phi_error_lower')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			poloidal_angle_att_7=self.ids.magnetics.bpol_probe[i].poloidal_angle

			node = ET.SubElement(parent, 'poloidal_angle'+ '='+ str(poloidal_angle_att_7))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'rad')
			node.set('documentation', 'Poloidal angle of the coil orientation')
			node.set('name', 'poloidal_angle')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			poloidal_angle_error_upper_att_8=self.ids.magnetics.bpol_probe[i].poloidal_angle_error_upper

			node = ET.SubElement(parent, 'poloidal_angle_error_upper'+ '='+ str(poloidal_angle_error_upper_att_8))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'rad')
			node.set('documentation', 'Upper error for "poloidal_angle"')
			node.set('name', 'poloidal_angle_error_upper')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			poloidal_angle_error_lower_att_9=self.ids.magnetics.bpol_probe[i].poloidal_angle_error_lower

			node = ET.SubElement(parent, 'poloidal_angle_error_lower'+ '='+ str(poloidal_angle_error_lower_att_9))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'rad')
			node.set('documentation', 'Lower error for "poloidal_angle"')
			node.set('name', 'poloidal_angle_error_lower')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			toroidal_angle_att_11=self.ids.magnetics.bpol_probe[i].toroidal_angle

			node = ET.SubElement(parent, 'toroidal_angle'+ '='+ str(toroidal_angle_att_11))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'rad')
			node.set('documentation', 'Toroidal angle of coil orientation (0 if fully in the poloidal plane) ')
			node.set('name', 'toroidal_angle')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			toroidal_angle_error_upper_att_12=self.ids.magnetics.bpol_probe[i].toroidal_angle_error_upper

			node = ET.SubElement(parent, 'toroidal_angle_error_upper'+ '='+ str(toroidal_angle_error_upper_att_12))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'rad')
			node.set('documentation', 'Upper error for "toroidal_angle"')
			node.set('name', 'toroidal_angle_error_upper')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			toroidal_angle_error_lower_att_13=self.ids.magnetics.bpol_probe[i].toroidal_angle_error_lower

			node = ET.SubElement(parent, 'toroidal_angle_error_lower'+ '='+ str(toroidal_angle_error_lower_att_13))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'rad')
			node.set('documentation', 'Lower error for "toroidal_angle"')
			node.set('name', 'toroidal_angle_error_lower')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			area_att_15=self.ids.magnetics.bpol_probe[i].area

			node = ET.SubElement(parent, 'area'+ '='+ str(area_att_15))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm^2')
			node.set('documentation', 'Area of each turn of the coil')
			node.set('name', 'area')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			area_error_upper_att_16=self.ids.magnetics.bpol_probe[i].area_error_upper

			node = ET.SubElement(parent, 'area_error_upper'+ '='+ str(area_error_upper_att_16))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm^2')
			node.set('documentation', 'Upper error for "area"')
			node.set('name', 'area_error_upper')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			area_error_lower_att_17=self.ids.magnetics.bpol_probe[i].area_error_lower

			node = ET.SubElement(parent, 'area_error_lower'+ '='+ str(area_error_lower_att_17))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm^2')
			node.set('documentation', 'Lower error for "area"')
			node.set('name', 'area_error_lower')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			length_att_19=self.ids.magnetics.bpol_probe[i].length

			node = ET.SubElement(parent, 'length'+ '='+ str(length_att_19))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm')
			node.set('documentation', 'Length of the coil')
			node.set('name', 'length')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			length_error_upper_att_20=self.ids.magnetics.bpol_probe[i].length_error_upper

			node = ET.SubElement(parent, 'length_error_upper'+ '='+ str(length_error_upper_att_20))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm')
			node.set('documentation', 'Upper error for "length"')
			node.set('name', 'length_error_upper')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			length_error_lower_att_21=self.ids.magnetics.bpol_probe[i].length_error_lower

			node = ET.SubElement(parent, 'length_error_lower'+ '='+ str(length_error_lower_att_21))
			node.set('data_type', 'FLT_0D')
			node.set('type', 'static')
			node.set('units', 'm')
			node.set('documentation', 'Lower error for "length"')
			node.set('name', 'length_error_lower')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			turns_att_23=self.ids.magnetics.bpol_probe[i].turns

			node = ET.SubElement(parent, 'turns'+ '='+ str(turns_att_23))
			node.set('data_type', 'INT_0D')
			node.set('type', 'static')
			node.set('documentation', 'Turns in the coil, including sign')
			node.set('name', 'turns')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + ']']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + ']'] = parent
			parent = ET.SubElement(parent, 'field')
			parent.set('documentation', 'Measured magnetic field')
			parent.set('name', 'field')
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].field') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].field']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].field'] = parent
			data_att_25=self.ids.magnetics.bpol_probe[i].field.data

			node = ET.SubElement(parent, 'data')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'bpol_probe[i1].field.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'T')
			node.set('documentation', 'Measured magnetic field')
			node.set('name', 'data')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.bpol_probe[i].field.data')
			nameNode.text = 'ids.magnetics.bpol_probe' + '[' + str(i) + '].field.data'
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].field') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].field']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].field'] = parent
			data_error_upper_att_26=self.ids.magnetics.bpol_probe[i].field.data_error_upper

			node = ET.SubElement(parent, 'data_error_upper')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'bpol_probe[i1].field.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'T')
			node.set('documentation', 'Upper error for "data"')
			node.set('name', 'data_error_upper')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.bpol_probe[i].field.data_error_upper')
			nameNode.text = 'ids.magnetics.bpol_probe' + '[' + str(i) + '].field.data_error_upper'
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].field') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].field']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].field'] = parent
			data_error_lower_att_27=self.ids.magnetics.bpol_probe[i].field.data_error_lower

			node = ET.SubElement(parent, 'data_error_lower')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'bpol_probe[i1].field.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'T')
			node.set('documentation', 'Lower error for "data"')
			node.set('name', 'data_error_lower')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.bpol_probe[i].field.data_error_lower')
			nameNode.text = 'ids.magnetics.bpol_probe' + '[' + str(i) + '].field.data_error_lower'
			if parents.get('magnetics.bpol_probe' + '[' + str(i) + '].field') != None :
				parent = parents['magnetics.bpol_probe' + '[' + str(i) + '].field']
			else:
				parents['magnetics.bpol_probe' + '[' + str(i) + '].field'] = parent
			time_att_29=self.ids.magnetics.bpol_probe[i].field.time

			node = ET.SubElement(parent, 'time')
			node.set('itime_index', '-1')
			node.set('coordinate1', '1...N')
			node.set('data_type', 'flt_1d_type')
			node.set('documentation', 'Generic time [s]')
			node.set('name', 'time')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.bpol_probe[i].field.time')
			nameNode.text = 'ids.magnetics.bpol_probe' + '[' + str(i) + '].field.time'
			parent = current_parent_1
			i+= 1
		if parents.get('magnetics') != None :
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		#level=1
		N = len(self.ids.magnetics.method)

		i= 0
		while i < N:

			current_parent_1= parent
			parent = ET.SubElement(parent, 'method')
			parent.set('index', str(i))
			parent.set('dim', str(N))
			parent.set('data_type', 'struct_array')
			parent.set('documentation', 'A method generating processed quantities derived from the magnetic measurements')
			parent.set('name', 'method')
			if parents.get('magnetics.method' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.method' + '[' + str(i) + ']']
			else:
				parents['magnetics.method' + '[' + str(i) + ']'] = parent
			name_att_5=self.ids.magnetics.method[i].name

			node = ET.SubElement(parent, 'name'+ '='+ str(name_att_5))
			node.set('data_type', 'STR_0D')
			node.set('type', 'static')
			node.set('documentation', 'Name of the data processing method')
			node.set('name', 'name')
			if parents.get('magnetics.method' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.method' + '[' + str(i) + ']']
			else:
				parents['magnetics.method' + '[' + str(i) + ']'] = parent
			parent = ET.SubElement(parent, 'ip')
			parent.set('documentation', 'Plasma current. Positive sign means anti-clockwise when viewed from above.')
			parent.set('name', 'ip')
			if parents.get('magnetics.method' + '[' + str(i) + '].ip') != None :
				parent = parents['magnetics.method' + '[' + str(i) + '].ip']
			else:
				parents['magnetics.method' + '[' + str(i) + '].ip'] = parent
			data_att_7=self.ids.magnetics.method[i].ip.data

			node = ET.SubElement(parent, 'data')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'method[i1].ip.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'A')
			node.set('documentation', 'Plasma current. Positive sign means anti-clockwise when viewed from above.')
			node.set('name', 'data')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.method[i].ip.data')
			nameNode.text = 'ids.magnetics.method' + '[' + str(i) + '].ip.data'
			if parents.get('magnetics.method' + '[' + str(i) + '].ip') != None :
				parent = parents['magnetics.method' + '[' + str(i) + '].ip']
			else:
				parents['magnetics.method' + '[' + str(i) + '].ip'] = parent
			data_error_upper_att_8=self.ids.magnetics.method[i].ip.data_error_upper

			node = ET.SubElement(parent, 'data_error_upper')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'method[i1].ip.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'A')
			node.set('documentation', 'Upper error for "data"')
			node.set('name', 'data_error_upper')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.method[i].ip.data_error_upper')
			nameNode.text = 'ids.magnetics.method' + '[' + str(i) + '].ip.data_error_upper'
			if parents.get('magnetics.method' + '[' + str(i) + '].ip') != None :
				parent = parents['magnetics.method' + '[' + str(i) + '].ip']
			else:
				parents['magnetics.method' + '[' + str(i) + '].ip'] = parent
			data_error_lower_att_9=self.ids.magnetics.method[i].ip.data_error_lower

			node = ET.SubElement(parent, 'data_error_lower')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'method[i1].ip.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'A')
			node.set('documentation', 'Lower error for "data"')
			node.set('name', 'data_error_lower')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.method[i].ip.data_error_lower')
			nameNode.text = 'ids.magnetics.method' + '[' + str(i) + '].ip.data_error_lower'
			if parents.get('magnetics.method' + '[' + str(i) + '].ip') != None :
				parent = parents['magnetics.method' + '[' + str(i) + '].ip']
			else:
				parents['magnetics.method' + '[' + str(i) + '].ip'] = parent
			time_att_11=self.ids.magnetics.method[i].ip.time

			node = ET.SubElement(parent, 'time')
			node.set('itime_index', '-1')
			node.set('coordinate1', '1...N')
			node.set('data_type', 'flt_1d_type')
			node.set('documentation', 'Generic time [s]')
			node.set('name', 'time')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.method[i].ip.time')
			nameNode.text = 'ids.magnetics.method' + '[' + str(i) + '].ip.time'
			if parents.get('magnetics.method' + '[' + str(i) + ']') != None :
				parent = parents['magnetics.method' + '[' + str(i) + ']']
			else:
				parents['magnetics.method' + '[' + str(i) + ']'] = parent
			parent = ET.SubElement(parent, 'diamagnetic_flux')
			parent.set('documentation', 'Diamagnetic flux')
			parent.set('name', 'diamagnetic_flux')
			if parents.get('magnetics.method' + '[' + str(i) + '].diamagnetic_flux') != None :
				parent = parents['magnetics.method' + '[' + str(i) + '].diamagnetic_flux']
			else:
				parents['magnetics.method' + '[' + str(i) + '].diamagnetic_flux'] = parent
			data_att_8=self.ids.magnetics.method[i].diamagnetic_flux.data

			node = ET.SubElement(parent, 'data')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'method[i1].diamagnetic_flux.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'Wb')
			node.set('documentation', 'Diamagnetic flux')
			node.set('name', 'data')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.method[i].diamagnetic_flux.data')
			nameNode.text = 'ids.magnetics.method' + '[' + str(i) + '].diamagnetic_flux.data'
			if parents.get('magnetics.method' + '[' + str(i) + '].diamagnetic_flux') != None :
				parent = parents['magnetics.method' + '[' + str(i) + '].diamagnetic_flux']
			else:
				parents['magnetics.method' + '[' + str(i) + '].diamagnetic_flux'] = parent
			data_error_upper_att_9=self.ids.magnetics.method[i].diamagnetic_flux.data_error_upper

			node = ET.SubElement(parent, 'data_error_upper')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'method[i1].diamagnetic_flux.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'Wb')
			node.set('documentation', 'Upper error for "data"')
			node.set('name', 'data_error_upper')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.method[i].diamagnetic_flux.data_error_upper')
			nameNode.text = 'ids.magnetics.method' + '[' + str(i) + '].diamagnetic_flux.data_error_upper'
			if parents.get('magnetics.method' + '[' + str(i) + '].diamagnetic_flux') != None :
				parent = parents['magnetics.method' + '[' + str(i) + '].diamagnetic_flux']
			else:
				parents['magnetics.method' + '[' + str(i) + '].diamagnetic_flux'] = parent
			data_error_lower_att_10=self.ids.magnetics.method[i].diamagnetic_flux.data_error_lower

			node = ET.SubElement(parent, 'data_error_lower')
			node.set('itime_index', '-1')
			node.set('coordinate1', 'method[i1].diamagnetic_flux.time')
			if self.ids.magnetics.ids_properties.homogeneous_time==1:
				node.set('coordinate1', 'time')
			node.set('data_type', 'FLT_1D')
			node.set('units', 'Wb')
			node.set('documentation', 'Lower error for "data"')
			node.set('name', 'data_error_lower')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.method[i].diamagnetic_flux.data_error_lower')
			nameNode.text = 'ids.magnetics.method' + '[' + str(i) + '].diamagnetic_flux.data_error_lower'
			if parents.get('magnetics.method' + '[' + str(i) + '].diamagnetic_flux') != None :
				parent = parents['magnetics.method' + '[' + str(i) + '].diamagnetic_flux']
			else:
				parents['magnetics.method' + '[' + str(i) + '].diamagnetic_flux'] = parent
			time_att_12=self.ids.magnetics.method[i].diamagnetic_flux.time

			node = ET.SubElement(parent, 'time')
			node.set('itime_index', '-1')
			node.set('coordinate1', '1...N')
			node.set('data_type', 'flt_1d_type')
			node.set('documentation', 'Generic time [s]')
			node.set('name', 'time')
			node.set('type', 'dynamic')
			nameNode = ET.SubElement(node, 'name')
			nameNode.set('data_type', 'STR_0D')
			var_name = 'i'
			var_name_max = 'N'
			node.set(var_name, str(i))
			node.set(var_name_max, str(N))
			node.set('aos_parents_count', str(1))
			node.set('aos', 'self.ids.magnetics.method[i].diamagnetic_flux.time')
			nameNode.text = 'ids.magnetics.method' + '[' + str(i) + '].diamagnetic_flux.time'
			parent = current_parent_1
			i+= 1
		if parents.get('magnetics') != None :
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		parent = ET.SubElement(parent, 'code')
		parent.set('documentation', 'Generic decription of the code-specific parameters for the code that has produced this IDS')
		parent.set('name', 'code')
		if parents.get('magnetics.code') != None :
			parent = parents['magnetics.code']
		else:
			parents['magnetics.code'] = parent
		name_att_6=self.ids.magnetics.code.name

		node = ET.SubElement(parent, 'name'+ '='+ str(name_att_6))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'Name of software generating IDS')
		node.set('name', 'name')
		if parents.get('magnetics.code') != None :
			parent = parents['magnetics.code']
		else:
			parents['magnetics.code'] = parent
		commit_att_7=self.ids.magnetics.code.commit

		node = ET.SubElement(parent, 'commit'+ '='+ str(commit_att_7))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'Unique commit reference of software')
		node.set('name', 'commit')
		if parents.get('magnetics.code') != None :
			parent = parents['magnetics.code']
		else:
			parents['magnetics.code'] = parent
		version_att_8=self.ids.magnetics.code.version

		node = ET.SubElement(parent, 'version'+ '='+ str(version_att_8))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'Unique version (tag) of software')
		node.set('name', 'version')
		if parents.get('magnetics.code') != None :
			parent = parents['magnetics.code']
		else:
			parents['magnetics.code'] = parent
		repository_att_9=self.ids.magnetics.code.repository

		node = ET.SubElement(parent, 'repository'+ '='+ str(repository_att_9))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'URL of software repository')
		node.set('name', 'repository')
		if parents.get('magnetics.code') != None :
			parent = parents['magnetics.code']
		else:
			parents['magnetics.code'] = parent
		parameters_att_10=self.ids.magnetics.code.parameters

		node = ET.SubElement(parent, 'parameters'+ '='+ str(parameters_att_10))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'List of the code specific parameters in XML format')
		node.set('name', 'parameters')
		if parents.get('magnetics.code') != None :
			parent = parents['magnetics.code']
		else:
			parents['magnetics.code'] = parent
		output_flag_att_11=self.ids.magnetics.code.output_flag

		node = ET.SubElement(parent, 'output_flag')
		node.set('itime_index', '-1')
		node.set('coordinate1', 'time')
		node.set('data_type', 'INT_1D')
		node.set('documentation', 'Output flag : 0 means the run is successful, other values mean some difficulty has been encountered, the exact meaning is then code specific. Negative values mean the result shall not be used.')
		node.set('name', 'output_flag')
		node.set('type', 'dynamic')
		nameNode = ET.SubElement(node, 'name')
		nameNode.set('data_type', 'STR_0D')
		node.set('aos_parents_count', str(0))
		node.set('aos', 'self.ids.magnetics.code.output_flag')
		nameNode.text = 'ids.magnetics.code.output_flag'
		if parents.get('magnetics') != None :
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		time_att_6=self.ids.magnetics.time

		node = ET.SubElement(parent, 'time')
		node.set('itime_index', '-1')
		node.set('coordinate1', '1...N')
		node.set('data_type', 'flt_1d_type')
		node.set('documentation', 'Generic time [s]')
		node.set('name', 'time')
		node.set('type', 'dynamic')
		nameNode = ET.SubElement(node, 'name')
		nameNode.set('data_type', 'STR_0D')
		node.set('aos_parents_count', str(0))
		node.set('aos', 'self.ids.magnetics.time')
		nameNode.text = 'ids.magnetics.time'
		if parents.get('magnetics') != None :
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		return parent
