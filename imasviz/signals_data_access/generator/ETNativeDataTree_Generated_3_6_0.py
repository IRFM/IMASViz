#This class has been generated -- DO NOT MODIFY MANUALLY !!! --
import xml.etree.ElementTree as ET
import os
import wx
import imas
import threading
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
			self.ids.magnetics.get(self.occurrence)
			idsData = self.load_magnetics(self.idsName, self.occurrence)

			if self.async==True:
				e = threading.Event()

				wx.PostEvent(self.view.parent, ResultEvent((self.idsName, idsData, self.pathsList, e), self.view.parent.eventResultId))
				print 'waiting for view update...'

				e.wait()

				print 'view update wait ended...'

			else:
				self.view.parent.updateView(self.idsName, idsData, self.pathsList)


	def load_magnetics(self, IDSName, occurrence):

		IDSName = 'magnetics'
		parents = {}
		parent = ET.Element('magnetics')
		if 'magnetics' in parents and parents['magnetics'] != None : 
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		parent = ET.SubElement(parent, 'code')
		name_att_2=self.ids.magnetics.code.name

		node = ET.SubElement(parent, 'name'+ '='+ str(name_att_2))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		if 'magnetics.code' in parents and parents['magnetics.code'] != None : 
			parent = parents['magnetics.code']
		else:
			parents['magnetics.code'] = parent
		output_flag_att_3=self.ids.magnetics.code.output_flag

		node = ET.SubElement(parent, 'output_flag')
		node.set('itime_index', '-1')
		node.set('coordinate1', 'time')
		node.set('data_type', 'INT_1D')
		node.set('type', 'dynamic')
		nameNode = ET.SubElement(node, 'name')
		nameNode.set('data_type', 'STR_0D')
		node.set('aos_parents_count', str(0))
		node.set('aos', 'self.ids.magnetics.code.output_flag')
		nameNode.text = 'ids.magnetics.code.output_flag'
		if 'magnetics' in parents and parents['magnetics'] != None : 
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		time_att_2=self.ids.magnetics.time

		node = ET.SubElement(parent, 'time')
		node.set('itime_index', '-1')
		node.set('coordinate1', '1...N')
		node.set('data_type', 'flt_1d_type')
		node.set('type', 'dynamic')
		nameNode = ET.SubElement(node, 'name')
		nameNode.set('data_type', 'STR_0D')
		node.set('aos_parents_count', str(0))
		node.set('aos', 'self.ids.magnetics.time')
		nameNode.text = 'ids.magnetics.time'
		if 'magnetics' in parents and parents['magnetics'] != None : 
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		parent = ET.SubElement(parent, 'ids_properties')
		comment_att_4=self.ids.magnetics.ids_properties.comment

		node = ET.SubElement(parent, 'comment'+ '='+ str(comment_att_4))
		node.set('data_type', 'STR_0D')
		node.set('type', 'constant')
		homogeneous_time_att_5=self.ids.magnetics.ids_properties.homogeneous_time

		node = ET.SubElement(parent, 'homogeneous_time'+ '='+ str(homogeneous_time_att_5))
		node.set('data_type', 'INT_0D')
		node.set('type', 'constant')
		if 'magnetics' in parents and parents['magnetics'] != None : 
			parent = parents['magnetics']
		else:
			parents['magnetics'] = parent
		return parent

