#This class has been generated -- DO NOT MODIFY MANUALLY !!! --
import xml.etree.ElementTree as ET
import os
import wx
import imas
import threading
import time
from imasviz.view.ResultEvent import ResultEvent
from threading import Thread


class ETNativeDataTree_Generated_3_6_0(Thread):
	def __init__(self, userName, imasDbName, shotNumber, runNumber, view, occurrence=0, pathsList = None, async=True):
		Thread.__init__(self)
		self.occurrence = occurrence
		self.view = view
		self.ids = None
		self.idsName = self.view.IDSNameSelected
		self.pathsList = pathsList
		self.async = async

	def run(self):
		self.execute()

	def execute(self):
		idsData = None
		if self.idsName == 'magnetics':
			self.view.log.info('Loading occurrence ' + str(self.occurrence) + ' of IDS ' + self.idsName + '...')
			t1 = time.time()
			self.ids.magnetics.get(self.occurrence)
			t2 = time.time()
			print('imas get took ' + str(t2 - t1) + ' seconds')
			print ('Get operation ended')
			idsData = self.load_magnetics(self.idsName, self.occurrence)

			t3 = time.time()
			print('in memory xml object creation took ' + str(t3 - t2) + ' seconds')
			if self.async==True:
				e = threading.Event()

				wx.PostEvent(self.view.parent, ResultEvent((self.idsName, self.occurrence, idsData, self.pathsList, e), self.view.parent.eventResultId))
				print ('waiting for view update...')

				e.wait()

				print ('view update wait ended...')

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
		parent = ET.SubElement(parent, 'code')
		parent.set('documentation', 'Generic decription of the code-specific parameters for the code that has produced this IDS')
		name_att_2=self.ids.magnetics.code.name

		node = ET.SubElement(parent, 'name'+ '='+ str(name_att_2))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'Name of software generating IDS')
		if parents.get('magnetics.code') != None : 
			parent = parents['magnetics.code']
		else:
			parents['magnetics.code'] = parent
		output_flag_att_3=self.ids.magnetics.code.output_flag

		node = ET.SubElement(parent, 'output_flag')
		node.set('itime_index', '-1')
		node.set('coordinate1', 'time')
		node.set('data_type', 'INT_1D')
		node.set('documentation', 'Output flag : 0 means the run is successful, other values mean some difficulty has been encountered, the exact meaning is then code specific. Negative values mean the result shall not be used.')
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
		time_att_2=self.ids.magnetics.time

		node = ET.SubElement(parent, 'time')
		node.set('itime_index', '-1')
		node.set('coordinate1', '1...N')
		node.set('data_type', 'flt_1d_type')
		node.set('documentation', 'Generic time [s]')
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
		parent = ET.SubElement(parent, 'ids_properties')
		parent.set('documentation', 'Interface Data Structure properties. This element identifies the node above as an IDS')
		comment_att_4=self.ids.magnetics.ids_properties.comment

		node = ET.SubElement(parent, 'comment'+ '='+ str(comment_att_4))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		node.set('documentation', 'Any comment describing the content of this IDS')
		homogeneous_time_att_5=self.ids.magnetics.ids_properties.homogeneous_time

		node = ET.SubElement(parent, 'homogeneous_time'+ '='+ str(homogeneous_time_att_5))
		node.set('data_type', 'INT_0D')
		node.set('type', 'constant')
		node.set('documentation', '1 if the time of this IDS is homogeneous. In this case, the time values for this IDS are stored in ../time just below the root of this IDS. Otherwise, the time values are stored in the various time fields at lower levels in the tree.')
		if parents.get('magnetics') != None : 
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		return parent

