import lxml.sax
from xml.sax.handler import ContentHandler
from imasviz.data_source.DataSourceFactory import DataSourceFactory
import os
import xml.etree.ElementTree as ET

class MyContentHandler(ContentHandler):
     def __init__(self):
         self.a_amount = 0
         self.b_amount = 0
         self.text = None

     def startElementNS(self, name, qname, attributes):
         uri, localname = name
         # print 'test'
         if localname == 'flux':
             print (attributes)
             self.a_amount += 1
         if localname == 'field':
             print ('field')
             self.b_amount += 1

     def characters(self, data):
         self.text = data


# def test():
#     handler = MyContentHandler()
#     context = Context(GlobalVaues.TORE_SUPRA, os.environ['TS_MAPPINGS_DIR'])
#     IDSName = 'magnetics'
#     tree = ET.parse(context.mappingFilesDirectory + '/' + IDSName + '_v1.xml')
#     lxml.sax.saxify(tree, handler)
#     # root = tree.getroot()
#     # idsObject = root.find(IDSName)
#     # print idsObject
#
# test()
